import { describe, it, expect } from "vitest";
import {
  TezcaAPIError,
  RateLimitError,
  AuthError,
  ForbiddenError,
} from "../src/errors";

describe("TezcaAPIError", () => {
  it("stores status and message", () => {
    const err = new TezcaAPIError(500, "Server error");
    expect(err.status).toBe(500);
    expect(err.message).toBe("Server error");
    expect(err.name).toBe("TezcaAPIError");
    expect(err).toBeInstanceOf(Error);
  });

  it("stores response body", () => {
    const body = { error: "details" };
    const err = new TezcaAPIError(400, "Bad request", body);
    expect(err.body).toEqual(body);
  });
});

describe("RateLimitError", () => {
  it("stores retryAfter and has status 429", () => {
    const err = new RateLimitError(60);
    expect(err.status).toBe(429);
    expect(err.retryAfter).toBe(60);
    expect(err.name).toBe("RateLimitError");
    expect(err).toBeInstanceOf(TezcaAPIError);
  });
});

describe("AuthError", () => {
  it("has status 401 and default message", () => {
    const err = new AuthError();
    expect(err.status).toBe(401);
    expect(err.message).toBe("Authentication failed");
    expect(err.name).toBe("AuthError");
  });

  it("accepts custom message", () => {
    const err = new AuthError("Invalid key");
    expect(err.message).toBe("Invalid key");
  });
});

describe("ForbiddenError", () => {
  it("has status 403 and default message", () => {
    const err = new ForbiddenError();
    expect(err.status).toBe(403);
    expect(err.message).toBe("Insufficient permissions");
    expect(err.name).toBe("ForbiddenError");
  });
});
