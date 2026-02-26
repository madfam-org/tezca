/**
 * Bulk data access endpoint methods.
 */

import type {
  BulkArticlesParams,
  BulkArticlesResponse,
  BulkArticle,
  ChangelogParams,
  ChangelogResponse,
} from "../types";
import { autoPaginate } from "../pagination";

export class BulkEndpoint {
  constructor(private request: <T>(path: string, params?: Record<string, string>) => Promise<T>) {}

  /** Fetch a single page of bulk articles. */
  async articlePage(params?: BulkArticlesParams): Promise<BulkArticlesResponse> {
    const query: Record<string, string> = {};
    if (params) {
      for (const [k, v] of Object.entries(params)) {
        if (v !== undefined && v !== null) query[k] = String(v);
      }
    }
    return this.request("/bulk/articles/", query);
  }

  /**
   * Auto-paginating async iterator over bulk articles.
   *
   * Usage:
   *   for await (const batch of client.bulk.articles({ domain: "finance" })) {
   *     await processBatch(batch);
   *   }
   */
  articles(params?: BulkArticlesParams): AsyncGenerator<BulkArticle[], void, unknown> {
    return autoPaginate(
      (p) => this.articlePage(p),
      params ?? {},
    );
  }
}
