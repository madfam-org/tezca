import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import {
  CACHE_TTL_MS,
  LAW_PAGE_SIZE,
  SITEMAP_URL_LIMIT,
  SitemapInventoryError,
  assertSitemapSize,
  fetchAllLawIds,
  getLawIds,
  resetLawIdCache,
} from '@/lib/sitemap-laws';

const API = 'http://api.test/api/v1';
const noSleep = () => Promise.resolve();

/** A fake `/laws/` endpoint holding `total` laws, ids law-0 … law-(total-1). */
function lawApi(total: number, failures: Record<number, number> = {}) {
  const remaining = { ...failures };
  const calls: string[] = [];
  const fetchImpl = vi.fn(async (input: RequestInfo | URL) => {
    const url = new URL(String(input));
    calls.push(url.toString());
    const page = Number(url.searchParams.get('page'));
    const size = Number(url.searchParams.get('page_size'));
    if (remaining[page]) {
      remaining[page]--;
      return new Response('upstream error', { status: 502 });
    }
    const start = (page - 1) * size;
    const results = Array.from({ length: Math.max(0, Math.min(size, total - start)) }, (_, i) => ({
      id: `law-${start + i}`,
    }));
    return Response.json({ count: total, results });
  }) as unknown as typeof fetch;
  return { fetchImpl, calls };
}

describe('fetchAllLawIds', () => {
  it('reads every page of the inventory', async () => {
    const total = LAW_PAGE_SIZE * 3 + 7;
    const { fetchImpl, calls } = lawApi(total);
    const ids = await fetchAllLawIds(API, { fetchImpl, sleep: noSleep });
    expect(ids).toHaveLength(total);
    expect(new Set(ids).size).toBe(total);
    expect(calls).toHaveLength(4);
  });

  it('retries a failing page and still returns the full inventory', async () => {
    const total = LAW_PAGE_SIZE * 2;
    const { fetchImpl } = lawApi(total, { 2: 2 });
    const ids = await fetchAllLawIds(API, { fetchImpl, sleep: noSleep });
    expect(ids).toHaveLength(total);
  });

  it('throws instead of returning a partial inventory when a page keeps failing', async () => {
    const { fetchImpl } = lawApi(LAW_PAGE_SIZE * 2, { 2: 99 });
    await expect(fetchAllLawIds(API, { fetchImpl, sleep: noSleep })).rejects.toThrow(
      SitemapInventoryError,
    );
  });

  it('throws when the first read is unreachable', async () => {
    const fetchImpl = vi.fn(async () => {
      throw new TypeError('fetch failed');
    }) as unknown as typeof fetch;
    await expect(fetchAllLawIds(API, { fetchImpl, sleep: noSleep })).rejects.toThrow(/fetch failed/);
    expect(fetchImpl).toHaveBeenCalledTimes(3);
  });

  it('throws on an empty inventory', async () => {
    const { fetchImpl } = lawApi(0);
    await expect(fetchAllLawIds(API, { fetchImpl, sleep: noSleep })).rejects.toThrow(/no laws/);
  });
});

describe('getLawIds', () => {
  beforeEach(() => {
    resetLawIdCache();
    vi.spyOn(console, 'error').mockImplementation(() => {});
  });
  afterEach(() => vi.restoreAllMocks());

  it('serves a fresh copy from memory', async () => {
    const { fetchImpl, calls } = lawApi(3);
    await getLawIds(API, { fetchImpl, sleep: noSleep });
    await getLawIds(API, { fetchImpl, sleep: noSleep });
    expect(calls).toHaveLength(1);
  });

  it('keeps the last complete copy when a refresh fails', async () => {
    let clock = 0;
    const now = () => clock;
    const good = lawApi(3);
    expect(await getLawIds(API, { fetchImpl: good.fetchImpl, sleep: noSleep, now })).toHaveLength(3);

    clock = CACHE_TTL_MS + 1;
    const down = lawApi(3, { 1: 99 });
    expect(await getLawIds(API, { fetchImpl: down.fetchImpl, sleep: noSleep, now })).toHaveLength(3);
    expect(console.error).toHaveBeenCalled();
  });

  it('throws when there is no complete copy to fall back on', async () => {
    const down = lawApi(3, { 1: 99 });
    await expect(getLawIds(API, { fetchImpl: down.fetchImpl, sleep: noSleep })).rejects.toThrow(
      SitemapInventoryError,
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
