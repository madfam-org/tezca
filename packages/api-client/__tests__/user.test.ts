import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { TezcaClient } from "../src/client";

describe("UserEndpoint", () => {
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

  it("sends Bearer token header when using JWT auth", async () => {
    mockFetch(200, { bookmarks: [], recently_viewed: [], preferences: {} });

    const client = new TezcaClient({ token: "eyJtest" });
    await client.user!.preferences();

    expect(globalThis.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/user/preferences/"),
      expect.objectContaining({
        headers: expect.objectContaining({ Authorization: "Bearer eyJtest" }),
      }),
    );
  });

  it("user endpoint is undefined when using API key auth", () => {
    const client = new TezcaClient({ apiKey: "tzk_test" });
    expect(client.user).toBeUndefined();
  });

  it("throws when neither apiKey nor token provided", () => {
    expect(() => new TezcaClient({} as never)).toThrow(
      "requires at least one of apiKey or token",
    );
  });

  it("fetches user preferences", async () => {
    const prefs = { bookmarks: ["cpeum"], recently_viewed: [], preferences: { theme: "dark" } };
    mockFetch(200, prefs);

    const client = new TezcaClient({ token: "eyJtest" });
    const result = await client.user!.preferences();

    expect(result.bookmarks).toEqual(["cpeum"]);
  });

  it("adds a bookmark", async () => {
    mockFetch(200, { bookmarks: ["cpeum", "amparo"] });

    const client = new TezcaClient({ token: "eyJtest" });
    const result = await client.user!.addBookmark("amparo");

    expect(result.bookmarks).toContain("amparo");
    const [, options] = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    expect(options.method).toBe("POST");
    expect(JSON.parse(options.body)).toEqual({ law_id: "amparo" });
  });

  it("removes a bookmark", async () => {
    mockFetch(200, { bookmarks: ["cpeum"] });

    const client = new TezcaClient({ token: "eyJtest" });
    await client.user!.removeBookmark("amparo");

    const [, options] = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    expect(options.method).toBe("DELETE");
  });

  // Annotations CRUD
  it("lists annotations", async () => {
    const annotations = [{ id: 1, law_id: "cpeum", article_id: "art-1", text: "Note", color: "yellow" }];
    mockFetch(200, annotations);

    const client = new TezcaClient({ token: "eyJtest" });
    const result = await client.user!.annotations.list("cpeum");

    expect(result).toEqual(annotations);
    const calledUrl = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[0][0] as string;
    expect(calledUrl).toContain("law_id=cpeum");
  });

  it("creates an annotation", async () => {
    mockFetch(200, { id: 2, law_id: "cpeum", article_id: "art-1", text: "New note", color: "blue" });

    const client = new TezcaClient({ token: "eyJtest" });
    const result = await client.user!.annotations.create({
      law_id: "cpeum",
      article_id: "art-1",
      text: "New note",
      color: "blue",
    });

    expect(result.id).toBe(2);
    const [, options] = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    expect(options.method).toBe("POST");
  });

  it("deletes an annotation", async () => {
    mockFetch(200, {});

    const client = new TezcaClient({ token: "eyJtest" });
    await client.user!.annotations.delete(5);

    const [url, options] = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    expect(url).toContain("/user/annotations/5/");
    expect(options.method).toBe("DELETE");
  });

  // Alerts CRUD
  it("creates an alert", async () => {
    mockFetch(200, { id: 1, law_id: "cpeum", alert_type: "law_updated", delivery: "in_app", is_active: true });

    const client = new TezcaClient({ token: "eyJtest" });
    const result = await client.user!.alerts.create({
      law_id: "cpeum",
      alert_type: "law_updated",
    });

    expect(result.id).toBe(1);
    expect(result.alert_type).toBe("law_updated");
  });

  it("deletes an alert", async () => {
    mockFetch(200, {});

    const client = new TezcaClient({ token: "eyJtest" });
    await client.user!.alerts.delete(3);

    const [url, options] = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    expect(url).toContain("/user/alerts/3/");
    expect(options.method).toBe("DELETE");
  });

  // Notifications
  it("lists notifications", async () => {
    const notifications = [{ id: 1, title: "Update", body: "Law updated", is_read: false }];
    mockFetch(200, notifications);

    const client = new TezcaClient({ token: "eyJtest" });
    const result = await client.user!.notifications.list();

    expect(result).toEqual(notifications);
  });

  it("marks notifications as read", async () => {
    mockFetch(200, { updated: 2 });

    const client = new TezcaClient({ token: "eyJtest" });
    const result = await client.user!.notifications.markRead([1, 2]);

    expect(result.updated).toBe(2);
    const [, options] = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    expect(options.method).toBe("POST");
    expect(JSON.parse(options.body)).toEqual({ notification_ids: [1, 2] });
  });
});
