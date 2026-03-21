import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { TezcaClient } from "../src/client";

describe("CategoriesEndpoint", () => {
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

  it("lists categories", async () => {
    const categories = [
      { category: "ley", count: 500 },
      { category: "reglamento", count: 300 },
    ];
    mockFetch(200, categories);

    const client = new TezcaClient({ apiKey: "tzk_test" });
    const result = await client.categories.list();

    expect(result).toEqual(categories);
    expect(globalThis.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/categories/"),
      expect.anything(),
    );
  });

  it("lists states", async () => {
    const states = ["Jalisco", "Ciudad de México", "Nuevo León"];
    mockFetch(200, states);

    const client = new TezcaClient({ apiKey: "tzk_test" });
    const result = await client.categories.states();

    expect(result).toEqual(states);
    expect(globalThis.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/states/"),
      expect.anything(),
    );
  });

  it("lists municipalities filtered by state", async () => {
    const municipalities = ["Guadalajara", "Zapopan", "Tlaquepaque"];
    mockFetch(200, municipalities);

    const client = new TezcaClient({ apiKey: "tzk_test" });
    const result = await client.categories.municipalities("Jalisco");

    expect(result).toEqual(municipalities);
    const calledUrl = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[0][0] as string;
    expect(calledUrl).toContain("/municipalities/");
    expect(calledUrl).toContain("state=Jalisco");
  });
});
