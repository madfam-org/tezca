/**
 * Cross-references endpoint methods.
 */

import type { CrossReferenceData, BatchRefsResponse } from "../types";

export class ReferencesEndpoint {
  constructor(
    private request: <T>(path: string, params?: Record<string, string>) => Promise<T>,
    private requestBody: <T>(method: string, path: string, body?: unknown) => Promise<T>,
  ) {}

  /** Get all cross-references for a law. */
  async forLaw(lawId: string): Promise<CrossReferenceData[]> {
    return this.request(`/laws/${encodeURIComponent(lawId)}/references/`);
  }

  /**
   * Batch fetch cross-references for specific articles.
   * Chunks at 200 IDs per request to match backend limits.
   */
  async batch(lawId: string, articleIds: string[]): Promise<BatchRefsResponse> {
    const CHUNK_SIZE = 200;
    const encodedLawId = encodeURIComponent(lawId);

    if (articleIds.length <= CHUNK_SIZE) {
      return this.requestBody("POST", `/laws/${encodedLawId}/articles/references/batch/`, {
        article_ids: articleIds,
      });
    }

    // Chunk large requests and merge results
    const merged: BatchRefsResponse = {
      law_id: lawId,
      article_refs: {},
    };

    for (let i = 0; i < articleIds.length; i += CHUNK_SIZE) {
      const chunk = articleIds.slice(i, i + CHUNK_SIZE);
      const result = await this.requestBody<BatchRefsResponse>(
        "POST",
        `/laws/${encodedLawId}/articles/references/batch/`,
        { article_ids: chunk },
      );
      Object.assign(merged.article_refs, result.article_refs);
    }

    return merged;
  }
}
