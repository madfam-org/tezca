import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import {
  CACHE_TTL_MS,
  DEFAULT_RETRY_AFTER_MS,
  LAW_PAGE_SIZE,
  REFRESH_DEADLINE_MS,
  REQUEST_BUDGET_MS,
  RETRY_AFTER_CAP_MS,
  SITEMAP_URL_LIMIT,
  assertSitemapSize,
  getLawInventory,
  parseRetryAfter,
  resetLawInventory,
} from '@/lib/sitemap-laws';

const API = 'http://api.test/api/v1';

/** What a page answers before it answers 200: a status, or 429 with a Retry-After. */
type Hiccup = number | { status: 429; retryAfter?: string };

function fakeResponse(status: number, body: unknown, headers: Record<string, string> = {}) {
  return {
    ok: status >= 200 && status < 300,
    status,
    headers: new Headers(headers),
    json: async () => body,
  } as unknown as Response;
}

/**
 * A fake `/laws/` endpoint holding `total` laws, ids law-0 … law-(total-1).
 * `hiccups[page]` lists the answers that page gives, in order, before a 200.
 * Records every requested page and the most requests ever in flight at once.
 */
function lawApi(total: number, hiccups: Record<number, Hiccup[]> = {}) {
  const queue = Object.fromEntries(Object.entries(hiccups).map(([k, v]) => [k, [...v]]));
  const pages: number[] = [];
  let inFlight = 0;
  let maxInFlight = 0;
  const fetchImpl = vi.fn(async (input: RequestInfo | URL) => {
    inFlight++;
    maxInFlight = Math.max(maxInFlight, inFlight);
    try {
      await Promise.resolve();
      const url = new URL(String(input));
      const page = Number(url.searchParams.get('page'));
      const size = Number(url.searchParams.get('page_size'));
      pages.push(page);
      const next = queue[page]?.shift();
      if (typeof next === 'number') return fakeResponse(next, { detail: 'upstream error' });
      if (next) {
        const headers: Record<string, string> = {};
        if (next.retryAfter !== undefined) headers['retry-after'] = next.retryAfter;
        return fakeResponse(429, { detail: 'throttled' }, headers);
      }
      const start = (page - 1) * size;
      const results = Array.from(
        { length: Math.max(0, Math.min(size, total - start)) },
        (_, i) => ({ id: `law-${start + i}` }),
      );
      return fakeResponse(200, { count: total, results });
    } finally {
      inFlight--;
    }
  }) as unknown as typeof fetch;
  return {
    fetchImpl,
    pages,
    get maxInFlight() {
      return maxInFlight;
    },
  };
}

beforeEach(() => {
  vi.useFakeTimers({ toFake: ['setTimeout', 'clearTimeout', 'Date'] });
  resetLawInventory();
  vi.spyOn(console, 'error').mockImplementation(() => {});
  vi.spyOn(console, 'warn').mockImplementation(() => {});
  vi.spyOn(console, 'info').mockImplementation(() => {});
});

afterEach(() => {
  resetLawInventory();
  vi.useRealTimers();
  vi.restoreAllMocks();
});

describe('parseRetryAfter', () => {
  it('reads delta-seconds', () => {
    expect(parseRetryAfter('2')).toBe(2_000);
    expect(parseRetryAfter('60')).toBe(60_000);
  });

  it('caps a long wait', () => {
    expect(parseRetryAfter('3000')).toBe(RETRY_AFTER_CAP_MS);
  });

  it('reads an HTTP date', () => {
    const now = Date.parse('2026-11-27T10:00:00Z');
    expect(parseRetryAfter('Fri, 27 Nov 2026 10:00:30 GMT', now)).toBe(30_000);
  });

  it('falls back to a default, and never waits under a second', () => {
    expect(parseRetryAfter(null)).toBe(DEFAULT_RETRY_AFTER_MS);
    expect(parseRetryAfter('soon')).toBe(DEFAULT_RETRY_AFTER_MS);
    expect(parseRetryAfter('0')).toBe(1_000);
  });
});

describe('getLawInventory', () => {
  it('reads every page, one request at a time', async () => {
    const total = LAW_PAGE_SIZE * 3 + 7;
    const api = lawApi(total);
    const inventory = await getLawInventory(API, { fetchImpl: api.fetchImpl });
    expect(inventory.complete).toBe(true);
    expect(inventory.ids).toHaveLength(total);
    expect(new Set(inventory.ids).size).toBe(total);
    expect(api.pages).toEqual([1, 2, 3, 4]);
    expect(api.maxInFlight).toBe(1);
  });

  it('serves a fresh copy from memory', async () => {
    const api = lawApi(3);
    await getLawInventory(API, { fetchImpl: api.fetchImpl });
    await getLawInventory(API, { fetchImpl: api.fetchImpl });
    expect(api.pages).toEqual([1]);
  });

  it('shares one refresh between concurrent requests', async () => {
    const api = lawApi(LAW_PAGE_SIZE * 2);
    const [a, b] = await Promise.all([
      getLawInventory(API, { fetchImpl: api.fetchImpl }),
      getLawInventory(API, { fetchImpl: api.fetchImpl }),
    ]);
    expect(a.ids).toHaveLength(LAW_PAGE_SIZE * 2);
    expect(b.ids).toEqual(a.ids);
    expect(api.pages).toEqual([1, 2]);
  });

  it('waits for Retry-After on a 429 and asks for the same page again', async () => {
    const api = lawApi(LAW_PAGE_SIZE * 2, { 2: [{ status: 429, retryAfter: '2' }] });
    const pending = getLawInventory(API, { fetchImpl: api.fetchImpl });

    await vi.advanceTimersByTimeAsync(1_999);
    expect(api.pages).toEqual([1, 2]);

    await vi.advanceTimersByTimeAsync(1);
    const inventory = await pending;
    expect(inventory.complete).toBe(true);
    expect(inventory.ids).toHaveLength(LAW_PAGE_SIZE * 2);
    expect(api.pages).toEqual([1, 2, 2]);
    expect(console.warn).toHaveBeenCalledWith(expect.stringContaining('retrying in 2000 ms'));
  });

  it('caps the Retry-After wait', async () => {
    const api = lawApi(LAW_PAGE_SIZE * 2, { 2: [{ status: 429, retryAfter: '3000' }] });
    void getLawInventory(API, { fetchImpl: api.fetchImpl });
    await vi.advanceTimersByTimeAsync(RETRY_AFTER_CAP_MS - 1);
    expect(api.pages).toEqual([1, 2]);
    await vi.advanceTimersByTimeAsync(1);
    expect(api.pages).toEqual([1, 2, 2]);
  });

  it('on a cold start past the request budget, serves the laws read so far and keeps reading', async () => {
    const throttled = { status: 429 as const, retryAfter: '60' };
    const api = lawApi(LAW_PAGE_SIZE * 3, { 2: [throttled, throttled] });

    const pending = getLawInventory(API, { fetchImpl: api.fetchImpl });
    await vi.advanceTimersByTimeAsync(REQUEST_BUDGET_MS);
    const cold = await pending;
    expect(cold.complete).toBe(false);
    expect(cold.ids).toHaveLength(LAW_PAGE_SIZE);
    expect(console.error).toHaveBeenCalledWith(
      expect.stringContaining(`serving ${LAW_PAGE_SIZE} of ${LAW_PAGE_SIZE * 3} laws`),
    );

    // The refresh outlives the request and finishes in the background.
    await vi.advanceTimersByTimeAsync(2 * 60_000);
    expect(api.pages).toEqual([1, 2, 2, 2, 3]);
    const warm = await getLawInventory(API, { fetchImpl: api.fetchImpl });
    expect(warm).toMatchObject({ complete: true, stale: false });
    expect(warm.ids).toHaveLength(LAW_PAGE_SIZE * 3);
    expect(api.pages).toHaveLength(5);
  });

  it('on a cold start with the API down, serves no laws instead of failing', async () => {
    const api = lawApi(3, { 1: [503, 503, 503, 503, 503, 503] });
    const pending = getLawInventory(API, { fetchImpl: api.fetchImpl });
    await vi.advanceTimersByTimeAsync(4_000); // backoff 1 s + 3 s, then the refresh gives up
    const inventory = await pending;
    expect(inventory).toEqual({ ids: [], complete: false, stale: false });
    expect(console.error).toHaveBeenCalledWith(
      expect.stringContaining('law inventory refresh failed'),
      expect.anything(),
    );

    // The next request starts a new refresh.
    const retry = getLawInventory(API, { fetchImpl: api.fetchImpl });
    await vi.advanceTimersByTimeAsync(4_000);
    await retry;
    expect(api.pages).toHaveLength(6);
  });

  it('keeps the pages already read when a refresh fails, and resumes from the missing one', async () => {
    const api = lawApi(LAW_PAGE_SIZE * 3, { 3: [502, 502, 502] });
    const pending = getLawInventory(API, { fetchImpl: api.fetchImpl });
    await vi.advanceTimersByTimeAsync(4_000);
    const failed = await pending;
    expect(failed.complete).toBe(false);
    expect(failed.ids).toHaveLength(LAW_PAGE_SIZE * 2);

    const resumed = await getLawInventory(API, { fetchImpl: api.fetchImpl });
    expect(resumed.complete).toBe(true);
    expect(resumed.ids).toHaveLength(LAW_PAGE_SIZE * 3);
    expect(api.pages).toEqual([1, 2, 3, 3, 3, 3]);
  });

  it('serves a stale complete copy at once while it refreshes in the background', async () => {
    const first = lawApi(3);
    await getLawInventory(API, { fetchImpl: first.fetchImpl });

    vi.setSystemTime(Date.now() + CACHE_TTL_MS + 1);
    const throttled = { status: 429 as const, retryAfter: '60' };
    const second = lawApi(4, { 1: [throttled] });
    const stale = await getLawInventory(API, { fetchImpl: second.fetchImpl });
    expect(stale).toMatchObject({ complete: true, stale: true });
    expect(stale.ids).toHaveLength(3);

    await vi.advanceTimersByTimeAsync(60_000);
    const fresh = await getLawInventory(API, { fetchImpl: second.fetchImpl });
    expect(fresh).toMatchObject({ complete: true, stale: false });
    expect(fresh.ids).toHaveLength(4);
  });

  it('gives up a refresh that stays rate limited past its deadline', async () => {
    const forever = Array.from({ length: 1_000 }, () => ({ status: 429 as const, retryAfter: '65' }));
    const api = lawApi(LAW_PAGE_SIZE * 2, { 2: forever });
    void getLawInventory(API, { fetchImpl: api.fetchImpl });
    await vi.advanceTimersByTimeAsync(REFRESH_DEADLINE_MS + RETRY_AFTER_CAP_MS);
    const requestsAtDeadline = api.pages.length;
    expect(console.error).toHaveBeenCalledWith(
      expect.stringContaining(`law inventory refresh failed (${LAW_PAGE_SIZE} of`),
      expect.objectContaining({ message: expect.stringMatching(/ran out of time/) }),
    );
    // ~one request per capped wait, not a hot loop.
    expect(requestsAtDeadline).toBeLessThanOrEqual(REFRESH_DEADLINE_MS / RETRY_AFTER_CAP_MS + 3);
  });

  it('treats an empty inventory as a failed refresh', async () => {
    const api = lawApi(0);
    const inventory = await getLawInventory(API, { fetchImpl: api.fetchImpl });
    expect(inventory).toEqual({ ids: [], complete: false, stale: false });
    expect(console.error).toHaveBeenCalledWith(
      expect.stringContaining('law inventory refresh failed'),
      expect.objectContaining({ message: expect.stringMatching(/no laws/) }),
    );
  });
});

describe('assertSitemapSize', () => {
  it('accepts a file within the per-file limit', () => {
    expect(() => assertSitemapSize(SITEMAP_URL_LIMIT)).not.toThrow();
  });

  it('refuses a file above the per-file limit', () => {
    expect(() => assertSitemapSize(SITEMAP_URL_LIMIT + 1)).toThrow(/sitemap index/);
  });
});
