/**
 * Judicial records endpoint methods.
 */

import type {
  JudicialRecord,
  JudicialSearchParams,
  JudicialSearchResponse,
  JudicialStatsResponse,
  PaginatedResponse,
} from "../types";

export class JudicialEndpoint {
  constructor(
    private request: <T>(path: string, params?: Record<string, string>) => Promise<T>,
  ) {}

  /** Search judicial records (jurisprudencia and tesis aisladas). */
  async search(params: JudicialSearchParams): Promise<JudicialSearchResponse> {
    const query: Record<string, string> = {};
    if (params.q) query.q = params.q;
    if (params.materia) query.materia = params.materia;
    if (params.tipo) query.tipo = params.tipo;
    if (params.epoca) query.epoca = params.epoca;
    if (params.instancia) query.instancia = params.instancia;
    if (params.sort) query.sort = params.sort;
    if (params.page !== undefined) query.page = String(params.page);
    if (params.page_size !== undefined) query.page_size = String(params.page_size);
    return this.request("/judicial/search/", query);
  }

  /** Get judicial statistics (counts by tipo, materia, epoca). */
  async stats(): Promise<JudicialStatsResponse> {
    return this.request("/judicial/stats/");
  }
}
