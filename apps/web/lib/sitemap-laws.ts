/**
 * Law inventory for the public sitemap.
 *
 * The law list comes from the paginated `/laws/` endpoint (30,000+ laws,
 * 200 per page). That endpoint is rate limited for anonymous callers by the
 * API itself (`TieredRateThrottle`, `RATE_LIMITS["anon"]` in
 * `apps/api/tier_permissions.py`: 10 requests a minute and 100 an hour per
 * client), so one complete read takes more than an hour and can never fit in
 * one HTTP request. The inventory is therefore read in the background and
 * kept in memory:
 *
 * - pages are read one at a time (never more than one request in flight);
 * - a `429` is not an error: the reader waits for `Retry-After` (capped at
 *   `RETRY_AFTER_CAP_MS`) and asks for the same page again;
 * - any other failure is retried with backoff; a page that keeps failing ends
 *   that refresh, and the pages already read are kept so the next refresh
 *   resumes where it stopped instead of spending the quota again;
 * - a refresh gives up after `REFRESH_DEADLINE_MS`, keeping its progress;
 * - the last complete inventory is served for `CACHE_TTL_MS`; after that it is
 *   still served (stale) while a new refresh runs in the background.
 *
 * A sitemap request never waits for the network longer than
 * `REQUEST_BUDGET_MS`. With no complete inventory yet (cold start: a new pod,
 * or the API unreachable since it started) the request serves the laws read
 * so far, possibly none, and logs an error saying how many are missing; it
 * does not answer 5xx, and the refresh keeps running behind it. The
 * incompleteness is visible in the logs, never silent.
 *
 * A single sitemap file may hold at most 50,000 URLs (sitemaps.org). Above
 * that `assertSitemapSize` throws: split it with `generateSitemaps` and a
 * sitemap index rather than publish an invalid or cut file.
 */

export const LAW_PAGE_SIZE = 200; // LawListPagination.max_page_size in apps/api/law_views.py
export const SITEMAP_URL_LIMIT = 50_000;
export const SITEMAP_URL_WARN_AT = 45_000;
export const CACHE_TTL_MS = 24 * 60 * 60 * 1000;
/** Longest a sitemap request waits for a running refresh before answering. */
export const REQUEST_BUDGET_MS = 15_000;
/** Longest single wait for a `429`, whatever `Retry-After` asks for. */
export const RETRY_AFTER_CAP_MS = 65_000;
/** `Retry-After` missing or unreadable. */
export const DEFAULT_RETRY_AFTER_MS = 60_000;
/** A refresh still running after this long stops; its progress is kept. */
export const REFRESH_DEADLINE_MS = 3 * 60 * 60 * 1000;

const ERROR_RETRY_DELAYS_MS = [1_000, 3_000];
const REQUEST_TIMEOUT_MS = 15_000;
const MIN_RETRY_AFTER_MS = 1_000;

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

export interface InventoryOptions {
  fetchImpl?: typeof fetch;
  sleep?: Sleep;
  now?: () => number;
}

interface Deps {
  fetchImpl: typeof fetch;
  sleep: Sleep;
  now: () => number;
}

export interface LawInventory {
  ids: string[];
  /** False on a cold start: `ids` holds only the laws read so far. */
  complete: boolean;
  /** True when a complete copy older than `CACHE_TTL_MS` is being served. */
  stale: boolean;
}

const defaultSleep: Sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

function resolveDeps(options: InventoryOptions): Deps {
  return {
    fetchImpl: options.fetchImpl ?? fetch,
    sleep: options.sleep ?? defaultSleep,
    now: options.now ?? Date.now,
  };
}

/**
 * Milliseconds to wait for a `Retry-After` header (delta-seconds or an HTTP
 * date), clamped to [1 s, `RETRY_AFTER_CAP_MS`].
 */
export function parseRetryAfter(value: string | null, nowMs: number = Date.now()): number {
  let ms = DEFAULT_RETRY_AFTER_MS;
  const raw = value?.trim();
  if (raw) {
    if (/^\d+$/.test(raw)) {
      ms = Number(raw) * 1000;
    } else {
      const at = Date.parse(raw);
      if (Number.isFinite(at)) ms = at - nowMs;
    }
  }
  return Math.min(RETRY_AFTER_CAP_MS, Math.max(MIN_RETRY_AFTER_MS, ms));
}

async function fetchPage(url: string, deadline: number, deps: Deps): Promise<LawListPage> {
  let errors = 0;
  let lastError = 'unknown error';
  for (;;) {
    let wait: number;
    try {
      const res = await deps.fetchImpl(url, {
        cache: 'no-store',
        signal: AbortSignal.timeout(REQUEST_TIMEOUT_MS),
        headers: { Accept: 'application/json' },
      });
      if (res.ok) return (await res.json()) as LawListPage;
      if (res.status === 429) {
        wait = parseRetryAfter(res.headers.get('retry-after'), deps.now());
        if (deps.now() + wait > deadline) {
          throw new SitemapInventoryError(
            `law list refresh ran out of time while rate limited (${url})`,
          );
        }
        console.warn(`[sitemap] law list rate limited (HTTP 429) at ${url}; retrying in ${wait} ms`);
        await deps.sleep(wait);
        continue;
      }
      lastError = `HTTP ${res.status}`;
    } catch (err) {
      if (err instanceof SitemapInventoryError) throw err;
      lastError = err instanceof Error ? err.message : String(err);
    }
    if (errors >= ERROR_RETRY_DELAYS_MS.length) {
      throw new SitemapInventoryError(
        `law list read failed after ${errors + 1} attempts (${url}): ${lastError}`,
      );
    }
    wait = ERROR_RETRY_DELAYS_MS[errors++];
    await deps.sleep(wait);
  }
}

interface Progress {
  count: number;
  pageCount: number;
  nextPage: number;
  ids: Set<string>;
  startedAt: number;
}

let complete: { ids: string[]; at: number } | null = null;
let progress: Progress | null = null;
let refreshing: Promise<void> | null = null;
let generation = 0;

function completeCopy(): { ids: string[]; at: number } | null {
  return complete;
}

/** Test hook: forget the inventory and detach any refresh still running. */
export function resetLawInventory(): void {
  complete = null;
  progress = null;
  refreshing = null;
  generation++;
}

async function refreshInventory(apiUrl: string, deps: Deps): Promise<void> {
  const gen = generation;
  const deadline = deps.now() + REFRESH_DEADLINE_MS;
  const pageUrl = (page: number) => `${apiUrl}/laws/?page_size=${LAW_PAGE_SIZE}&page=${page}`;

  // Resume a recent interrupted read; restart one older than the cache TTL.
  if (!progress || deps.now() - progress.startedAt >= CACHE_TTL_MS) {
    const first = await fetchPage(pageUrl(1), deadline, deps);
    if (gen !== generation) return;
    const count = first.count ?? 0;
    if (!Number.isFinite(count) || count <= 0 || !first.results?.length) {
      throw new SitemapInventoryError(`law list returned no laws (count=${first.count})`);
    }
    progress = {
      count,
      pageCount: Math.ceil(count / LAW_PAGE_SIZE),
      nextPage: 2,
      ids: new Set(first.results.map((law) => law.id)),
      startedAt: deps.now(),
    };
  }

  const run = progress;
  while (run.nextPage <= run.pageCount) {
    const page = await fetchPage(pageUrl(run.nextPage), deadline, deps);
    if (gen !== generation) return;
    for (const law of page.results ?? []) run.ids.add(law.id);
    run.nextPage++;
  }

  if (run.ids.size !== run.count) {
    // The inventory can move while it is paginated; log, do not fail.
    console.warn(
      `[sitemap] law list reported count=${run.count} but returned ${run.ids.size} unique ids`,
    );
  }
  complete = { ids: [...run.ids], at: deps.now() };
  progress = null;
  console.info(`[sitemap] law inventory complete: ${complete.ids.length} laws`);
}

/** Start a background refresh unless one is running; never rejects. */
function startRefresh(apiUrl: string, deps: Deps): Promise<void> {
  if (refreshing) return refreshing;
  const run = refreshInventory(apiUrl, deps).catch((err) => {
    const kept = progress ? ` (${progress.ids.size} of ${progress.count} laws read, kept)` : '';
    console.error(`[sitemap] law inventory refresh failed${kept}`, err);
  });
  refreshing = run;
  void run.finally(() => {
    if (refreshing === run) refreshing = null;
  });
  return run;
}

/** Resolve true when `run` settles first, false after `ms`. */
function settlesWithin(run: Promise<void>, ms: number): Promise<boolean> {
  let timer: ReturnType<typeof setTimeout> | undefined;
  const budget = new Promise<boolean>((resolve) => {
    timer = setTimeout(() => resolve(false), ms);
  });
  return Promise.race([run.then(() => true), budget]).finally(() => clearTimeout(timer));
}

/**
 * The law inventory for one sitemap request. Never throws and never waits
 * longer than `REQUEST_BUDGET_MS`:
 *
 * - a complete copy younger than `CACHE_TTL_MS` is served from memory;
 * - an older complete copy is served at once while a refresh runs behind it;
 * - with no complete copy, the request waits for the refresh up to the
 *   budget, then serves the laws read so far (`complete: false`, logged as an
 *   error) and leaves the refresh running.
 */
export async function getLawInventory(
  apiUrl: string,
  options: InventoryOptions = {},
): Promise<LawInventory> {
  const deps = resolveDeps(options);
  if (complete && deps.now() - complete.at < CACHE_TTL_MS) {
    return { ids: complete.ids, complete: true, stale: false };
  }

  const run = startRefresh(apiUrl, deps);
  if (complete) {
    console.warn('[sitemap] serving a law inventory older than 24 h while it refreshes');
    return { ids: complete.ids, complete: true, stale: true };
  }

  const settled = await settlesWithin(run, REQUEST_BUDGET_MS);
  // Re-read the module state: the refresh may have completed while we waited.
  const done = completeCopy();
  if (done) return { ids: done.ids, complete: true, stale: false };

  const partial = progress ? [...progress.ids] : [];
  console.error(
    `[sitemap] no complete law inventory yet: serving ${partial.length} of ` +
      `${progress?.count ?? 'an unknown number of'} laws; ` +
      (settled ? 'the refresh failed and restarts on the next request' : 'the refresh continues in the background'),
  );
  return { ids: partial, complete: false, stale: false };
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
