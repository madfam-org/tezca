/**
 * Graph endpoint methods.
 */

import type { GraphResponse, GraphParams, GraphOverviewParams } from "../types";

export class GraphEndpoint {
  constructor(
    private request: <T>(path: string, params?: Record<string, string>) => Promise<T>,
  ) {}

  /** Get ego graph for a specific law. */
  async ego(lawId: string, params?: GraphParams): Promise<GraphResponse> {
    const query: Record<string, string> = {};
    if (params?.depth !== undefined) query.depth = String(params.depth);
    if (params?.min_weight !== undefined) query.min_weight = String(params.min_weight);
    return this.request(`/laws/${encodeURIComponent(lawId)}/graph/`, query);
  }

  /** Get global graph overview. */
  async overview(params?: GraphOverviewParams): Promise<GraphResponse> {
    const query: Record<string, string> = {};
    if (params?.min_weight !== undefined) query.min_weight = String(params.min_weight);
    if (params?.max_nodes !== undefined) query.max_nodes = String(params.max_nodes);
    return this.request("/graph/overview/", query);
  }

  /** Get public showcase graph (unauthenticated, top 50 nodes). */
  async showcase(): Promise<GraphResponse> {
    return this.request("/graph/showcase/");
  }
}
