import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { TezcaClient } from "../src/client";

describe("ReferencesEndpoint", () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    globalThis.fetch = vi.fn();
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  function mockFetch(status: number, body: unknown) {
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: status >= 200 && status < 300,
      status,
      statusText: status === 200 ? "OK" : "Error",
      json: () => Promise.resolve(body),
      text: () => Promise.resolve(JSON.stringify(body)),
      headers: new Headers(),
    });
  }

  it("fetches references for a law", async () => {
    const refs = [
      {
        id: 1,
        source_law_slug: "cpeum",
        source_article_id: "art-1",
        target_law_slug: "amparo",
        reference_text: "Ley de Amparo",
        confidence: 0.95,
      },
    ];
    mockFetch(200, refs);

    const client = new TezcaClient({ apiKey: "tzk_test" });
    const result = await client.references.forLaw("cpeum");

    expect(result).toEqual(refs);
    expect(globalThis.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/laws/cpeum/references/"),
      expect.anything(),
    );
  });

  it("batch fetches references for articles (small batch)", async () => {
    const batchResponse = {
      law_id: "cpeum",
      article_refs: {
        "art-1": [{ id: 1, reference_text: "ref1", confidence: 0.9 }],
        "art-2": [],
      },
    };
    mockFetch(200, batchResponse);

    const client = new TezcaClient({ apiKey: "tzk_test" });
    const result = await client.references.batch("cpeum", ["art-1", "art-2"]);

    expect(result.law_id).toBe("cpeum");
    expect(result.article_refs["art-1"]).toHaveLength(1);

    // Verify it was a POST request
    const [, options] = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    expect(options.method).toBe("POST");
    expect(JSON.parse(options.body)).toEqual({ article_ids: ["art-1", "art-2"] });
  });

  it("batch chunks large requests at 200 IDs", async () => {
    // Create 250 article IDs
    const articleIds = Array.from({ length: 250 }, (_, i) => `art-${i}`);

    // Mock two sequential responses
    let callCount = 0;
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockImplementation(() => {
      callCount++;
      const refs: Record<string, unknown[]> = {};
      if (callCount === 1) {
        // First chunk: art-0 to art-199
        for (let i = 0; i < 200; i++) refs[`art-${i}`] = [];
      } else {
        // Second chunk: art-200 to art-249
        for (let i = 200; i < 250; i++) refs[`art-${i}`] = [];
      }
      return Promise.resolve({
        ok: true,
        status: 200,
        statusText: "OK",
        json: () => Promise.resolve({ law_id: "cpeum", article_refs: refs }),
        text: () => Promise.resolve("{}"),
        headers: new Headers(),
      });
    });

    const client = new TezcaClient({ apiKey: "tzk_test" });
    const result = await client.references.batch("cpeum", articleIds);

    expect(callCount).toBe(2);
    expect(Object.keys(result.article_refs)).toHaveLength(250);
  });

  it("laws endpoint has references method", async () => {
    const refs = [{ id: 1, reference_text: "ref1", confidence: 0.9 }];
    mockFetch(200, refs);

    const client = new TezcaClient({ apiKey: "tzk_test" });
    const result = await client.laws.references("cpeum");

    expect(result).toEqual(refs);
  });
});
