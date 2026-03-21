import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { TezcaClient } from "../src/client";

describe("JudicialEndpoint", () => {
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

  it("searches judicial records with query", async () => {
    mockFetch(200, { results: [], total: 0, page: 1, page_size: 20 });

    const client = new TezcaClient({ apiKey: "tzk_test" });
    await client.judicial.search({ q: "amparo", materia: "constitucional" });

    const calledUrl = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[0][0] as string;
    expect(calledUrl).toContain("/judicial/search/");
    expect(calledUrl).toContain("q=amparo");
    expect(calledUrl).toContain("materia=constitucional");
  });

  it("searches with pagination params", async () => {
    mockFetch(200, { results: [], total: 0, page: 2, page_size: 10 });

    const client = new TezcaClient({ apiKey: "tzk_test" });
    await client.judicial.search({ page: 2, page_size: 10 });

    const calledUrl = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[0][0] as string;
    expect(calledUrl).toContain("page=2");
    expect(calledUrl).toContain("page_size=10");
  });

  it("fetches judicial stats", async () => {
    const stats = {
      total: 500,
      by_tipo: { jurisprudencia: 300, tesis_aislada: 200 },
      by_materia: { civil: 100, penal: 100 },
      by_epoca: { "11a": 400 },
    };
    mockFetch(200, stats);

    const client = new TezcaClient({ apiKey: "tzk_test" });
    const result = await client.judicial.stats();

    expect(result.total).toBe(500);
    expect(globalThis.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/judicial/stats/"),
      expect.anything(),
    );
  });

  it("filters by tipo", async () => {
    mockFetch(200, { results: [], total: 0, page: 1, page_size: 20 });

    const client = new TezcaClient({ apiKey: "tzk_test" });
    await client.judicial.search({ tipo: "jurisprudencia" });

    const calledUrl = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[0][0] as string;
    expect(calledUrl).toContain("tipo=jurisprudencia");
  });
});
