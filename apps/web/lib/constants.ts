/**
 * UI timing and limits.
 *
 * Centralizes magic numbers that previously appeared as inline literals in
 * components. Naming convention: `<DOMAIN>_<UNIT>_MS` for time spans, plain
 * descriptive names for counts.
 *
 * Add new constants here when you find yourself reaching for `setTimeout(_,
 * 2000)` or `setInterval(_, 30000)` in a component.
 */

// How long "Copied!" / "Saved!" success affordances stay visible.
export const COPY_FEEDBACK_DURATION_MS = 2000;

// Search input → API debounce window. Used by autocomplete + article search.
export const SEARCH_DEBOUNCE_MS = 300;

// Polling intervals — keep generous; the admin dashboards trigger backend
// queries on every tick.
export const NOTIFICATION_POLL_INTERVAL_MS = 60_000;
export const ADMIN_JOB_QUEUE_POLL_MS = 5_000;
export const ADMIN_METRICS_POLL_MS = 30_000;

// How long client-side stat caches survive (DashboardStats).
export const DASHBOARD_STATS_TTL_MS = 5 * 60 * 1000;

// AbortController timeout for fetches that must not hang (e.g. coverage
// stats called during page render).
export const DEFAULT_FETCH_TIMEOUT_MS = 10_000;

// Smooth-scroll-into-view debounce: window during which programmatic scrolls
// are absorbed before they're allowed to retrigger.
export const SCROLL_INTO_VIEW_DEBOUNCE_MS = 1_000;
