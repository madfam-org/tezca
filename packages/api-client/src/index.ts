/**
 * @tezca/api-client — TypeScript SDK for the Tezca API
 *
 * Usage:
 *   import { TezcaClient } from "@tezca/api-client";
 *
 *   const tezca = new TezcaClient({ apiKey: "tzk_..." });
 *   const laws = await tezca.laws.list({ domain: "finance" });
 */

export { TezcaClient } from "./client";

// Types
export type {
  TezcaClientConfig,
  DomainFilter,
  LawListParams,
  SearchParams,
  BulkArticlesParams,
  BulkArticle,
  BulkArticlesResponse,
  ChangelogParams,
  ChangelogEntry,
  ChangelogResponse,
  WebhookCreateParams,
  WebhookSubscription,
  PaginatedResponse,
  PaginationOptions,
  CursorPaginationOptions,
  // New types
  CategoryItem,
  CoverageTier,
  CoverageResponse,
  GraphNode,
  GraphEdge,
  GraphResponse,
  GraphParams,
  GraphOverviewParams,
  JudicialRecord,
  JudicialSearchParams,
  JudicialSearchResponse,
  JudicialStatsResponse,
  CrossReferenceData,
  IncomingCrossReference,
  BatchRefsResponse,
  AnnotationData,
  CreateAnnotationParams,
  NotificationData,
  AlertData,
  CreateAlertParams,
  UserPreferences,
} from "./types";

// Re-export shared types from @tezca/lib
export type {
  Law,
  LawListItem,
  LawVersion,
  SearchResult,
  DashboardStats,
} from "./types";

// Errors
export {
  TezcaAPIError,
  RateLimitError,
  AuthError,
  ForbiddenError,
} from "./errors";

// Auth strategies (for advanced use)
export { APIKeyAuth, JWTAuth } from "./auth";
export type { AuthStrategy } from "./auth";

// Pagination utilities
export { autoPaginate } from "./pagination";
