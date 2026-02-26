/**
 * Export endpoint methods.
 */

export type ExportFormat = "txt" | "pdf" | "latex" | "docx" | "epub" | "json";

export interface ExportQuota {
  tier: string;
  used: number;
  limit: number;
  remaining: number;
  formats_available: ExportFormat[];
}

export class ExportEndpoint {
  constructor(
    private request: <T>(path: string, params?: Record<string, string>) => Promise<T>,
    private requestRaw: (path: string, params?: Record<string, string>) => Promise<Response>,
  ) {}

  /** Download a law in the specified format. Returns a Response for streaming. */
  async download(lawId: string, format: ExportFormat): Promise<Response> {
    return this.requestRaw(
      `/laws/${encodeURIComponent(lawId)}/export/${format}/`,
    );
  }

  /** Get export quota information. */
  async quota(lawId: string): Promise<ExportQuota> {
    return this.request(`/laws/${encodeURIComponent(lawId)}/export/quota/`);
  }
}
