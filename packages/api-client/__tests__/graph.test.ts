import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { TezcaClient } from "../src/client";

describe("GraphEndpoint", () => {
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

  const graphResponse = {
    nodes: [{ id: "cpeum", label: "CPEUM", size: 100 }],
    edges: [{ source: "cpeum", target: "amparo", weight: 5 }],
    stats: { total_nodes: 1, total_edges: 1 },
  };

  it("fetches ego graph for a law", async () => {
    mockFetch(200, graphResponse);

    const client = new TezcaClient({ apiKey: "tzk_test" });
    const result = await client.graph.ego("cpeum");

    expect(result.nodes).toHaveLength(1);
    const calledUrl = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[0][0] as string;
    expect(calledUrl).toContain("/laws/cpeum/graph/");
  });

  it("passes ego graph params", async () => {
    mockFetch(200, graphResponse);

    const client = new TezcaClient({ apiKey: "tzk_test" });
    await client.graph.ego("cpeum", { depth: 2, min_weight: 3 });

    const calledUrl = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[0][0] as string;
    expect(calledUrl).toContain("depth=2");
    expect(calledUrl).toContain("min_weight=3");
  });

  it("fetches graph overview", async () => {
    mockFetch(200, graphResponse);

    const client = new TezcaClient({ apiKey: "tzk_test" });
    await client.graph.overview({ max_nodes: 100 });

    const calledUrl = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[0][0] as string;
    expect(calledUrl).toContain("/graph/overview/");
    expect(calledUrl).toContain("max_nodes=100");
  });

  it("fetches public showcase", async () => {
    mockFetch(200, graphResponse);

    const client = new TezcaClient({ apiKey: "tzk_test" });
    await client.graph.showcase();

    expect(globalThis.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/graph/showcase/"),
      expect.anything(),
    );
  });

  it("encodes special characters in law ID", async () => {
    mockFetch(200, graphResponse);

    const client = new TezcaClient({ apiKey: "tzk_test" });
    await client.graph.ego("ley/especial");

    const calledUrl = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[0][0] as string;
    expect(calledUrl).toContain("ley%2Fespecial");
  });
});
