/**
 * Coverage endpoint methods.
 */

import type { CoverageResponse } from "../types";

export class CoverageEndpoint {
  constructor(
    private request: <T>(path: string, params?: Record<string, string>) => Promise<T>,
  ) {}

  /** Get platform coverage statistics. */
  async get(): Promise<CoverageResponse> {
    return this.request("/coverage/");
  }
}
