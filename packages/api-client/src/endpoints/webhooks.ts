/**
 * Webhook management endpoint methods.
 */

import type { WebhookCreateParams, WebhookSubscription } from "../types";

export class WebhooksEndpoint {
  constructor(
    private request: <T>(path: string, params?: Record<string, string>) => Promise<T>,
    private requestBody: <T>(method: string, path: string, body?: unknown) => Promise<T>,
  ) {}

  /** Create a new webhook subscription. */
  async create(params: WebhookCreateParams): Promise<WebhookSubscription> {
    return this.requestBody("POST", "/webhooks/", {
      url: params.url,
      events: params.events,
      domain_filter: params.domainFilter ?? [],
    });
  }

  /** List all webhook subscriptions. */
  async list(): Promise<{ count: number; webhooks: WebhookSubscription[] }> {
    return this.request("/webhooks/list/");
  }

  /** Delete a webhook subscription. */
  async delete(id: number): Promise<{ status: string; id: number }> {
    return this.requestBody("DELETE", `/webhooks/${id}/`);
  }

  /** Send a test event to a webhook. */
  async test(id: number): Promise<{ status: string; id: number }> {
    return this.requestBody("POST", `/webhooks/${id}/test/`);
  }
}
