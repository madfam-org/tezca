import { describe, it, expect, vi } from "vitest";
import { autoPaginate } from "../src/pagination";
import type { BulkArticlesResponse, BulkArticle } from "../src/types";

function makeArticle(id: string): BulkArticle {
  return {
    law_id: "law-1",
    law_name: "Test Law",
    category: "fiscal",
    tier: "federal",
    status: "vigente",
    law_type: "legislative",
    state: null,
    article_id: id,
    text: `Article ${id} text`,
    last_updated: "2026-01-01",
  };
}

describe("autoPaginate", () => {
  it("yields all pages until next_cursor is null", async () => {
    const fetcher = vi.fn<(params: any) => Promise<BulkArticlesResponse>>();
    fetcher
      .mockResolvedValueOnce({
        count: 3,
        next_cursor: "cursor2",
        page_size: 2,
        results: [makeArticle("1"), makeArticle("2")],
      })
      .mockResolvedValueOnce({
        count: 3,
        next_cursor: null,
        page_size: 2,
        results: [makeArticle("3")],
      });

    const batches: BulkArticle[][] = [];
    for await (const batch of autoPaginate(fetcher, {})) {
      batches.push(batch);
    }

    expect(batches).toHaveLength(2);
    expect(batches[0]).toHaveLength(2);
    expect(batches[1]).toHaveLength(1);
    expect(fetcher).toHaveBeenCalledTimes(2);
    expect(fetcher).toHaveBeenNthCalledWith(2, { cursor: "cursor2" });
  });

  it("stops on empty results", async () => {
    const fetcher = vi.fn<(params: any) => Promise<BulkArticlesResponse>>();
    fetcher.mockResolvedValueOnce({
      count: 0,
      next_cursor: null,
      page_size: 100,
      results: [],
    });

    const batches: BulkArticle[][] = [];
    for await (const batch of autoPaginate(fetcher, {})) {
      batches.push(batch);
    }

    expect(batches).toHaveLength(0);
  });
});
