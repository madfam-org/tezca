import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { TezcaClient } from "../src/client";
import { AuthError, RateLimitError, ForbiddenError, TezcaAPIError } from "../src/errors";

describe("TezcaClient", () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    globalThis.fetch = vi.fn();
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  function mockFetch(status: number, body: unknown, headers?: Record<string, string>) {
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: status >= 200 && status < 300,
      status,
      statusText: status === 200 ? "OK" : "Error",
      json: () => Promise.resolve(body),
      text: () => Promise.resolve(JSON.stringify(body)),
      headers: new Headers(headers),
    });
  }

  it("sends X-API-Key header on requests", async () => {
    mockFetch(200, { count: 0, next: null, previous: null, results: [] });

    const client = new TezcaClient({ apiKey: "tzk_test" });
    await client.laws.list();

    expect(globalThis.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/laws/"),
      expect.objectContaining({
        headers: expect.objectContaining({ "X-API-Key": "tzk_test" }),
      }),
    );
  });

  it("uses custom baseUrl", async () => {
    mockFetch(200, { count: 0, next: null, previous: null, results: [] });

    const client = new TezcaClient({
      apiKey: "tzk_test",
      baseUrl: "https://custom.api.com/v1",
    });
    await client.laws.list();

    expect(globalThis.fetch).toHaveBeenCalledWith(
      expect.stringContaining("https://custom.api.com/v1/laws/"),
      expect.anything(),
    );
  });

  it("strips trailing slash from baseUrl", async () => {
    mockFetch(200, { count: 0, next: null, previous: null, results: [] });

    const client = new TezcaClient({
      apiKey: "tzk_test",
      baseUrl: "https://api.example.com/v1/",
    });
    await client.laws.list();

    expect(globalThis.fetch).toHaveBeenCalledWith(
      expect.stringMatching(/^https:\/\/api\.example\.com\/v1\/laws\//),
      expect.anything(),
    );
  });

  it("throws AuthError on 401", async () => {
    mockFetch(401, { error: "Invalid API key" });

    const client = new TezcaClient({ apiKey: "tzk_bad" });
    await expect(client.stats()).rejects.toThrow(AuthError);
  });

  it("throws ForbiddenError on 403", async () => {
    mockFetch(403, { error: "Insufficient scope" });

    const client = new TezcaClient({ apiKey: "tzk_limited" });
    await expect(client.stats()).rejects.toThrow(ForbiddenError);
  });

  it("throws RateLimitError on 429 with retryAfter", async () => {
    mockFetch(429, { error: "Too many requests" }, { "Retry-After": "30" });

    const client = new TezcaClient({ apiKey: "tzk_test" });
    try {
      await client.stats();
      expect.fail("Should have thrown");
    } catch (err) {
      expect(err).toBeInstanceOf(RateLimitError);
      expect((err as RateLimitError).retryAfter).toBe(30);
    }
  });

  it("throws TezcaAPIError on other HTTP errors", async () => {
    mockFetch(500, { error: "Internal server error" });

    const client = new TezcaClient({ apiKey: "tzk_test" });
    try {
      await client.stats();
      expect.fail("Should have thrown");
    } catch (err) {
      expect(err).toBeInstanceOf(TezcaAPIError);
      expect((err as TezcaAPIError).status).toBe(500);
    }
  });

  it("search passes query params correctly", async () => {
    mockFetch(200, { results: [], total: 0, page: 1, page_size: 20, total_pages: 0, facets: {} });

    const client = new TezcaClient({ apiKey: "tzk_test" });
    await client.search("constitución", { domain: "constitutional" });

    const calledUrl = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[0][0] as string;
    expect(calledUrl).toContain("/search/");
    expect(calledUrl).toContain("q=constituci");
    expect(calledUrl).toContain("domain=constitutional");
  });

  it("changelog passes params correctly", async () => {
    mockFetch(200, { since: "2026-01-01", total: 0, changes: [] });

    const client = new TezcaClient({ apiKey: "tzk_test" });
    await client.changelog({ since: "2026-01-01", domain: "finance" });

    const calledUrl = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[0][0] as string;
    expect(calledUrl).toContain("/changelog/");
    expect(calledUrl).toContain("since=2026-01-01");
    expect(calledUrl).toContain("domain=finance");
  });
});
