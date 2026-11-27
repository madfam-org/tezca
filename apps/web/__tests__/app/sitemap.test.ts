import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import sitemap, { dynamic } from '@/app/sitemap';
import { REQUEST_BUDGET_MS, resetLawInventory } from '@/lib/sitemap-laws';

describe('app/sitemap', () => {
  beforeEach(() => {
    resetLawInventory();
    vi.spyOn(console, 'error').mockImplementation(() => {});
    vi.spyOn(console, 'info').mockImplementation(() => {});
  });
  afterEach(() => {
    resetLawInventory();
    vi.useRealTimers();
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it('is rendered per request, never baked into the image at build', () => {
    expect(dynamic).toBe('force-dynamic');
  });

  it('lists every law page next to the static routes', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () =>
        Response.json({ count: 2, results: [{ id: 'cpeum' }, { id: 'ley federal/del trabajo' }] }),
      ),
    );
    const urls = (await sitemap()).map((entry) => entry.url);
    expect(urls).toContain('https://tezca.mx/leyes');
    expect(urls).toContain('https://tezca.mx/leyes/cpeum');
    expect(urls).toContain(`https://tezca.mx/leyes/${encodeURIComponent('ley federal/del trabajo')}`);
  });

  // fetch is stubbed, no host is called.
  it('still publishes the static routes, and logs the missing laws, when the API is down', async () => {
    vi.useFakeTimers({ toFake: ['setTimeout', 'clearTimeout', 'Date'] });
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => new Response('unavailable', { status: 503 })),
    );
    const pending = sitemap();
    await vi.advanceTimersByTimeAsync(REQUEST_BUDGET_MS);
    const urls = (await pending).map((entry) => entry.url);
    expect(urls).toContain('https://tezca.mx/leyes');
    expect(urls.some((url) => url.startsWith('https://tezca.mx/leyes/'))).toBe(false);
    expect(console.error).toHaveBeenCalledWith(
      expect.stringContaining('no complete law inventory yet'),
    );
  });
});
