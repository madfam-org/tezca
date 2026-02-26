/**
 * Auto-paginator helper for cursor-based endpoints.
 */

import type { BulkArticle, BulkArticlesResponse, BulkArticlesParams } from "./types";

/**
 * Creates an async iterator that auto-paginates through bulk article results.
 *
 * Usage:
 *   for await (const batch of autoPaginate(fetcher, params)) {
 *     await processBatch(batch);
 *   }
 */
export async function* autoPaginate(
  fetcher: (params: BulkArticlesParams) => Promise<BulkArticlesResponse>,
  params: BulkArticlesParams,
): AsyncGenerator<BulkArticle[], void, unknown> {
  let cursor = params.cursor;

  while (true) {
    const response = await fetcher({ ...params, cursor });
    if (response.results.length === 0) break;

    yield response.results;

    if (!response.next_cursor) break;
    cursor = response.next_cursor;
  }
}
