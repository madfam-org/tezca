/**
 * TezcaClient — Main SDK client for the Tezca API.
 *
 * Usage:
 *   const tezca = new TezcaClient({ apiKey: "tzk_..." });
 *   const laws = await tezca.laws.list({ domain: "finance" });
 *
 *   // JWT auth for user-specific endpoints:
 *   const tezca = new TezcaClient({ token: "eyJ..." });
 *   const prefs = await tezca.user.preferences();
 */

import type { TezcaClientConfig, ChangelogParams, ChangelogResponse } from "./types";
import { APIKeyAuth, JWTAuth, type AuthStrategy } from "./auth";
import { TezcaAPIError, RateLimitError, AuthError, ForbiddenError } from "./errors";
import { LawsEndpoint } from "./endpoints/laws";
import { SearchEndpoint } from "./endpoints/search";
import { BulkEndpoint } from "./endpoints/bulk";
import { ExportEndpoint } from "./endpoints/export";
import { WebhooksEndpoint } from "./endpoints/webhooks";
import { CategoriesEndpoint } from "./endpoints/categories";
import { CoverageEndpoint } from "./endpoints/coverage";
import { GraphEndpoint } from "./endpoints/graph";
import { JudicialEndpoint } from "./endpoints/judicial";
import { ReferencesEndpoint } from "./endpoints/references";
import { UserEndpoint } from "./endpoints/user";

const DEFAULT_BASE_URL = "https://tezca.mx/api/v1";
const DEFAULT_TIMEOUT = 30_000;

export class TezcaClient {
  readonly laws: LawsEndpoint;
  readonly search: SearchEndpoint["search"];
  readonly suggest: SearchEndpoint["suggest"];
  readonly bulk: BulkEndpoint;
  readonly export: ExportEndpoint;
  readonly webhooks: WebhooksEndpoint;
  readonly categories: CategoriesEndpoint;
  readonly coverage: CoverageEndpoint;
  readonly graph: GraphEndpoint;
  readonly judicial: JudicialEndpoint;
  readonly references: ReferencesEndpoint;
  readonly user?: UserEndpoint;

  private auth: AuthStrategy;
  private baseUrl: string;
  private timeout: number;

  constructor(config: TezcaClientConfig) {
    if (!config.apiKey && !config.token) {
      throw new Error("TezcaClient requires at least one of apiKey or token");
    }

    this.auth = config.token
      ? new JWTAuth(config.token)
      : new APIKeyAuth(config.apiKey!);
    this.baseUrl = (config.baseUrl ?? DEFAULT_BASE_URL).replace(/\/$/, "");
    this.timeout = config.timeout ?? DEFAULT_TIMEOUT;

    // Initialize endpoints
    const req = this.request.bind(this);
    const reqRaw = this.requestRaw.bind(this);
    const reqBody = this.requestBody.bind(this);

    this.laws = new LawsEndpoint(req);

    const searchEndpoint = new SearchEndpoint(req);
    this.search = searchEndpoint.search.bind(searchEndpoint);
    this.suggest = searchEndpoint.suggest.bind(searchEndpoint);

    this.bulk = new BulkEndpoint(req);
    this.export = new ExportEndpoint(req, reqRaw);
    this.webhooks = new WebhooksEndpoint(req, reqBody);
    this.categories = new CategoriesEndpoint(req);
    this.coverage = new CoverageEndpoint(req);
    this.graph = new GraphEndpoint(req);
    this.judicial = new JudicialEndpoint(req);
    this.references = new ReferencesEndpoint(req, reqBody);

    // User endpoint only available with JWT auth
    if (config.token) {
      this.user = new UserEndpoint(req, reqBody);
    }
  }

  /** Get changelog of laws updated since a date. */
  async changelog(params: ChangelogParams): Promise<ChangelogResponse> {
    const query: Record<string, string> = { since: params.since };
    if (params.domain) query.domain = params.domain;
    if (params.category) query.category = params.category;
    if (params.tier) query.tier = params.tier;
    return this.request("/changelog/", query);
  }

  /** Get dashboard statistics. */
  async stats(): Promise<Record<string, unknown>> {
    return this.request("/stats/");
  }

  // ── Internal request methods ─────────────────────────────────────────

  private async request<T>(
    path: string,
    params?: Record<string, string>,
  ): Promise<T> {
    const response = await this.requestRaw(path, params);
    return response.json() as Promise<T>;
  }

  private async requestRaw(
    path: string,
    params?: Record<string, string>,
  ): Promise<Response> {
    let url = `${this.baseUrl}${path}`;
    if (params && Object.keys(params).length > 0) {
      const sep = url.includes("?") ? "&" : "?";
      url += sep + new URLSearchParams(params).toString();
    }

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), this.timeout);

    try {
      const response = await fetch(url, {
        headers: {
          ...this.auth.getHeaders(),
          Accept: "application/json",
        },
        signal: controller.signal,
      });

      if (!response.ok) {
        await this.handleError(response);
      }

      return response;
    } finally {
      clearTimeout(timeoutId);
    }
  }

  private async requestBody<T>(
    method: string,
    path: string,
    body?: unknown,
  ): Promise<T> {
    const url = `${this.baseUrl}${path}`;
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), this.timeout);

    try {
      const response = await fetch(url, {
        method,
        headers: {
          ...this.auth.getHeaders(),
          "Content-Type": "application/json",
          Accept: "application/json",
        },
        body: body ? JSON.stringify(body) : undefined,
        signal: controller.signal,
      });

      if (!response.ok) {
        await this.handleError(response);
      }

      return response.json() as Promise<T>;
    } finally {
      clearTimeout(timeoutId);
    }
  }

  private async handleError(response: Response): Promise<never> {
    let body: unknown;
    try {
      body = await response.json();
    } catch {
      body = await response.text().catch(() => null);
    }

    switch (response.status) {
      case 401:
        throw new AuthError(
          (body as { error?: string })?.error ?? "Authentication failed",
        );
      case 403:
        throw new ForbiddenError(
          (body as { error?: string })?.error ?? "Insufficient permissions",
        );
      case 429: {
        const retryAfter = parseInt(
          response.headers.get("Retry-After") ?? "60",
          10,
        );
        throw new RateLimitError(retryAfter, body);
      }
      default:
        throw new TezcaAPIError(
          response.status,
          (body as { error?: string })?.error ??
            `HTTP ${response.status}: ${response.statusText}`,
          body,
        );
    }
  }
}
