/**
 * Law inventory for the public sitemap.
 *
 * The sitemap used to swallow a failed API read and publish only its static
 * routes, so search engines were told the site had no law pages and nothing
 * failed. This module makes that failure visible instead:
 *
 * - every page read is retried with backoff and a per-request timeout;
 * - a page that still fails, or an inventory that comes back empty, throws,
 *   so the sitemap request answers 5xx rather than a truncated list;
 * - the last complete inventory is kept in memory for `CACHE_TTL_MS`, and a
 *   failed refresh keeps serving it (logged loudly) instead of shrinking it.
 *
 * A single sitemap file may hold at most 50,000 URLs (sitemaps.org). Above
 * that the build of the list throws: split it with `generateSitemaps` and a
 * sitemap index rather than publish an invalid or cut file.
 */

export const LAW_PAGE_SIZE = 200; // LawListPagination.max_page_size in apps/api/law_views.py
export const SITEMAP_URL_LIMIT = 50_000;
export const SITEMAP_URL_WARN_AT = 45_000;
export const CACHE_TTL_MS = 24 * 60 * 60 * 1000;

const RETRY_DELAYS_MS = [1_000, 3_000];
const REQUEST_TIMEOUT_MS = 15_000;
const PAGE_CONCURRENCY = 4;

interface LawListPage {
  count?: number;
  results?: Array<{ id: string }>;
}

export class SitemapInventoryError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'SitemapInventoryError';
  }
}

type Sleep = (ms: number) => Promise<void>;

export interface FetchLawIdsOptions {
  fetchImpl?: typeof fetch;
  sleep?: Sleep;
}

const defaultSleep: Sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

async function fetchPage(
  url: string,
  fetchImpl: typeof fetch,
  sleep: Sleep,
): Promise<LawListPage> {
  let lastError = 'unknown error';
  for (let attempt = 0; attempt <= RETRY_DELAYS_MS.length; attempt++) {
    if (attempt > 0) await sleep(RETRY_DELAYS_MS[attempt - 1]);
    try {
      const res = await fetchImpl(url, {
        cache: 'no-store',
        signal: AbortSignal.timeout(REQUEST_TIMEOUT_MS),
        headers: { Accept: 'application/json' },
      });
      if (res.ok) {
        return (await res.json()) as LawListPage;
      }
      lastError = `HTTP ${res.status}`;
    } catch (err) {
      lastError = err instanceof Error ? err.message : String(err);
    }
  }
  throw new SitemapInventoryError(
    `law list read failed after ${RETRY_DELAYS_MS.length + 1} attempts (${url}): ${lastError}`,
  );
}

/**
 * Read every law id from the paginated `/laws/` endpoint. Throws on any page
 * that keeps failing, and on an empty inventory.
 */
export async function fetchAllLawIds(
  apiUrl: string,
  { fetchImpl = fetch, sleep = defaultSleep }: FetchLawIdsOptions = {},
): Promise<string[]> {
  const pageUrl = (page: number) => `${apiUrl}/laws/?page_size=${LAW_PAGE_SIZE}&page=${page}`;

  const first = await fetchPage(pageUrl(1), fetchImpl, sleep);
  const count = first.count ?? 0;
  if (!Number.isFinite(count) || count <= 0 || !first.results?.length) {
    throw new SitemapInventoryError(`law list returned no laws (count=${first.count})`);
  }

  const pageCount = Math.ceil(count / LAW_PAGE_SIZE);
  const pages: LawListPage[] = new Array(pageCount);
  pages[0] = first;

  let nextPage = 2;
  const worker = async () => {
    while (nextPage <= pageCount) {
      const page = nextPage++;
      pages[page - 1] = await fetchPage(pageUrl(page), fetchImpl, sleep);
    }
  };
  await Promise.all(Array.from({ length: Math.min(PAGE_CONCURRENCY, pageCount - 1) }, worker));

  const ids = new Set<string>();
  for (const page of pages) {
    for (const law of page?.results ?? []) ids.add(law.id);
  }
  if (ids.size !== count) {
    // The inventory can move while it is paginated; log, do not fail.
    console.warn(`[sitemap] law list reported count=${count} but returned ${ids.size} unique ids`);
  }
  return [...ids];
}

let cached: { ids: string[]; at: number } | null = null;
let inflight: Promise<string[]> | null = null;

/** Test hook: forget the in-memory inventory. */
export function resetLawIdCache(): void {
  cached = null;
  inflight = null;
}

/**
 * Cached law inventory. A fresh copy is served from memory; a stale or missing
 * copy is refreshed (one refresh at a time). When a refresh fails, the last
 * complete copy is served and the error is logged; with no copy, it throws.
 */
export async function getLawIds(
  apiUrl: string,
  options: FetchLawIdsOptions & { now?: () => number } = {},
): Promise<string[]> {
  const now = options.now ?? Date.now;
  if (cached && now() - cached.at < CACHE_TTL_MS) return cached.ids;

  inflight ??= fetchAllLawIds(apiUrl, options)
    .then((ids) => {
      cached = { ids, at: now() };
      return ids;
    })
    .finally(() => {
      inflight = null;
    });

  try {
    return await inflight;
  } catch (err) {
    console.error('[sitemap] law inventory refresh failed', err);
    if (cached) return cached.ids;
    throw err;
  }
}

/** Throw above the per-file URL limit; warn as it approaches it. */
export function assertSitemapSize(urlCount: number): void {
  if (urlCount > SITEMAP_URL_LIMIT) {
    throw new SitemapInventoryError(
      `sitemap would list ${urlCount} URLs, above the ${SITEMAP_URL_LIMIT} per-file limit; ` +
        'split it with generateSitemaps and a sitemap index',
    );
  }
  if (urlCount > SITEMAP_URL_WARN_AT) {
    console.warn(
      `[sitemap] ${urlCount} URLs, close to the ${SITEMAP_URL_LIMIT} per-file limit; plan a sitemap index`,
    );
  }
}
