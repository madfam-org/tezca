import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import sitemap, { dynamic } from '@/app/sitemap';
import { resetLawIdCache } from '@/lib/sitemap-laws';

describe('app/sitemap', () => {
  beforeEach(() => {
    resetLawIdCache();
    vi.spyOn(console, 'error').mockImplementation(() => {});
  });
  afterEach(() => {
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

  // Real retry backoff (1 s + 3 s) runs here; fetch is stubbed, no host is called.
  it('fails instead of publishing a sitemap without the law pages', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => new Response('unavailable', { status: 503 })),
    );
    await expect(sitemap()).rejects.toThrow(/law list read failed/);
  }, 10_000);
});
