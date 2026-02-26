/**
 * SDK-specific types for the Tezca API client.
 * Re-exports shared types from @tezca/lib and adds SDK types.
 */

// Re-export shared types
export type {
  Law,
  LawListItem,
  LawVersion,
  SearchResult,
  SearchResponse,
  DashboardStats,
} from "@tezca/lib";

// SDK-specific types

export interface TezcaClientConfig {
  apiKey: string;
  baseUrl?: string;
  timeout?: number;
}

export interface PaginationOptions {
  page?: number;
  page_size?: number;
}

export interface CursorPaginationOptions {
  cursor?: string;
  page_size?: number;
}

export type DomainFilter =
  | "finance"
  | "criminal"
  | "labor"
  | "civil"
  | "administrative"
  | "constitutional";

export interface LawListParams extends PaginationOptions {
  domain?: DomainFilter;
  category?: string;
  tier?: string;
  state?: string;
  status?: string;
  law_type?: string;
  q?: string;
  sort?: string;
}

export interface SearchParams extends PaginationOptions {
  domain?: DomainFilter;
  category?: string;
  jurisdiction?: string;
  status?: string;
  state?: string;
  sort?: string;
  law_type?: string;
}

export interface BulkArticlesParams extends CursorPaginationOptions {
  domain?: DomainFilter;
  category?: string;
  tier?: string;
  state?: string;
  status?: string;
  updated_since?: string;
}

export interface ChangelogParams {
  since: string;
  domain?: DomainFilter;
  category?: string;
  tier?: string;
}

export interface BulkArticle {
  law_id: string;
  law_name: string;
  category: string | null;
  tier: string | null;
  status: string | null;
  law_type: string | null;
  state: string | null;
  article_id: string;
  text: string;
  last_updated: string | null;
}

export interface BulkArticlesResponse {
  count: number;
  next_cursor: string | null;
  page_size: number;
  results: BulkArticle[];
}

export interface ChangelogEntry {
  law_id: string;
  law_name: string;
  category: string | null;
  tier: string | null;
  status: string | null;
  change_type: string;
  publication_date: string | null;
  change_summary: string | null;
  previous_version_date: string | null;
  updated_at: string;
}

export interface ChangelogResponse {
  since: string;
  total: number;
  changes: ChangelogEntry[];
}

export interface WebhookCreateParams {
  url: string;
  events: string[];
  domainFilter?: string[];
}

export interface WebhookSubscription {
  id: number;
  url: string;
  events: string[];
  domain_filter: string[];
  secret?: string;
  is_active: boolean;
  failure_count: number;
  created_at: string;
  last_triggered_at: string | null;
}

export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}
