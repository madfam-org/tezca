import { describe, it, expect } from "vitest";
import { APIKeyAuth, JWTAuth } from "../src/auth";

describe("APIKeyAuth", () => {
  it("returns X-API-Key header", () => {
    const auth = new APIKeyAuth("tzk_test123");
    expect(auth.getHeaders()).toEqual({ "X-API-Key": "tzk_test123" });
  });
});

describe("JWTAuth", () => {
  it("returns Bearer Authorization header", () => {
    const auth = new JWTAuth("my.jwt.token");
    expect(auth.getHeaders()).toEqual({
      Authorization: "Bearer my.jwt.token",
    });
  });
});
