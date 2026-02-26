/**
 * Search endpoint methods.
 */

import type { SearchParams } from "../types";

export interface SearchResultItem {
  id: string;
  law_id: string;
  law_name: string;
  article: string;
  snippet: string;
  score: number;
  tier: string | null;
  law_type: string | null;
  state: string | null;
  hierarchy: string[];
}

export interface SearchResponse {
  results: SearchResultItem[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  facets: Record<string, { key: string; count: number }[]>;
}

export class SearchEndpoint {
  constructor(private request: <T>(path: string, params?: Record<string, string>) => Promise<T>) {}

  /** Full-text search across all articles. */
  async search(q: string, params?: SearchParams): Promise<SearchResponse> {
    const query: Record<string, string> = { q };
    if (params) {
      for (const [k, v] of Object.entries(params)) {
        if (v !== undefined && v !== null) query[k] = String(v);
      }
    }
    return this.request("/search/", query);
  }

  /** Autocomplete suggestions. */
  async suggest(q: string): Promise<{
    suggestions: { id: string; name: string; tier: string }[];
  }> {
    return this.request("/suggest/", { q });
  }
}
