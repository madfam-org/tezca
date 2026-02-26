/**
 * Laws endpoint methods.
 */

import type { Law, LawListItem, PaginatedResponse, LawListParams, PaginationOptions } from "../types";

export class LawsEndpoint {
  constructor(private request: <T>(path: string, params?: Record<string, string>) => Promise<T>) {}

  /** List laws with optional filters. */
  async list(params?: LawListParams): Promise<PaginatedResponse<LawListItem>> {
    const query = this.buildQuery(params as Record<string, unknown>);
    return this.request(`/laws/${query}`);
  }

  /** Get full law detail by ID. */
  async get(lawId: string): Promise<Law> {
    return this.request(`/laws/${encodeURIComponent(lawId)}/`);
  }

  /** Get articles for a law. */
  async articles(lawId: string, params?: PaginationOptions): Promise<{
    law_id: string;
    law_name: string;
    total: number;
    page: number;
    page_size: number;
    articles: { article_id: string; text: string }[];
  }> {
    const query = this.buildQuery(params as Record<string, unknown> | undefined);
    return this.request(`/laws/${encodeURIComponent(lawId)}/articles/${query}`);
  }

  /** Search within a specific law. */
  async search(lawId: string, q: string): Promise<{
    law_id: string;
    query: string;
    total: number;
    results: { article_id: string; snippet: string; score: number }[];
  }> {
    return this.request(`/laws/${encodeURIComponent(lawId)}/search/`, { q });
  }

  /** Get related laws. */
  async related(lawId: string): Promise<{
    law_id: string;
    related: { law_id: string; name: string; tier: string; category: string; score: number }[];
  }> {
    return this.request(`/laws/${encodeURIComponent(lawId)}/related/`);
  }

  /** Get hierarchical structure. */
  async structure(lawId: string): Promise<{
    law_id: string;
    structure: { label: string; children: unknown[] }[];
  }> {
    return this.request(`/laws/${encodeURIComponent(lawId)}/structure/`);
  }

  private buildQuery(params?: Record<string, unknown>): string {
    if (!params) return "";
    const entries = Object.entries(params).filter(
      ([, v]) => v !== undefined && v !== null && v !== "",
    );
    if (entries.length === 0) return "";
    const qs = new URLSearchParams(
      entries.map(([k, v]) => [k, String(v)]),
    ).toString();
    return `?${qs}`;
  }
}
