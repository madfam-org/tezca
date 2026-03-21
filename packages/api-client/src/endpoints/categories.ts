/**
 * Categories endpoint methods.
 */

import type { CategoryItem } from "../types";

export class CategoriesEndpoint {
  constructor(
    private request: <T>(path: string, params?: Record<string, string>) => Promise<T>,
  ) {}

  /** List all law categories with counts. */
  async list(): Promise<CategoryItem[]> {
    return this.request("/categories/");
  }

  /** List all states that have laws. */
  async states(): Promise<string[]> {
    return this.request("/states/");
  }

  /** List municipalities, optionally filtered by state. */
  async municipalities(state?: string): Promise<string[]> {
    const params = state ? { state } : undefined;
    return this.request("/municipalities/", params);
  }
}
