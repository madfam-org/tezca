/**
 * SDK-specific types for the Tezca API client.
 * Types are inlined from @tezca/lib so consumers don't need it installed.
 */

// --- Inlined from @tezca/lib ---

export interface LawVersion {
  publication_date: string;
  valid_from: string | null;
  valid_to?: string | null;
  dof_url: string | null;
  change_summary?: string | null;
  xml_file: string | null;
}

export interface Law {
  id: string;
  name: string;
  short_name?: string;
  fullName?: string;
  category?: string;
  tier?: string;
  law_type?: "legislative" | "non_legislative";
  state?: string;
  status?: string;
  last_verified?: string;
  source_url?: string;
  versions?: LawVersion[];
  articles?: number;
  transitorios?: number;
  grade?: "A" | "B" | "C" | "D" | "F";
  score?: number;
  priority?: number;
  file?: string;
  degraded?: boolean;
}

export interface LawListItem {
  id: string;
  name: string;
  tier?: string;
  law_type?: "legislative" | "non_legislative";
  category?: string;
  status?: string;
  versions: number;
}

export interface SearchResult {
  id: string;
  law_id: string;
  law_name: string;
  article: string;
  snippet: string;
  score: number;
  date?: string;
  tier?: string | null;
  law_type?: string | null;
  state?: string;
  municipality?: string;
  hierarchy?: string[];
  book?: string;
  title?: string;
  chapter?: string;
}

export interface FacetBucket {
  key: string;
  count: number;
}

export interface SearchResponse {
  results: SearchResult[];
  total?: number;
  page?: number;
  page_size?: number;
  total_pages?: number;
  warning?: string;
  facets?: Record<string, FacetBucket[]>;
}

export interface DashboardStats {
  total_laws: number;
  federal_count: number;
  state_count: number;
  municipal_count: number;
  legislative_count: number;
  non_legislative_count: number;
  total_articles: number;
  federal_coverage: number;
  state_coverage: number;
  municipal_coverage: number;
  total_coverage: number;
  last_update: string | null;
  recent_laws: {
    id: string;
    name: string;
    date: string;
    tier: string;
    category: string;
  }[];
  coverage?: CoverageBreakdown;
  degraded?: boolean;
}

export interface CoverageItem {
  label?: string;
  count: number;
  universe: number | null;
  percentage: number | null;
  description?: string;
  source?: string;
  last_verified?: string;
  permanent_gaps?: number;
  cities_covered?: number;
  total_municipalities?: number;
}

export interface CoverageBreakdown {
  leyes_vigentes: CoverageItem;
  federal: CoverageItem;
  state: CoverageItem;
  state_all_powers: CoverageItem;
  municipal: CoverageItem;
}

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
