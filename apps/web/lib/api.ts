import type { Law, LawListItem, SearchResponse, DashboardStats, LawArticleResponse, IngestionStatus, RelatedLaw, CategoryItem } from "@tezca/lib";
import {
    LawSchema,
    SearchResponseSchema,
    DashboardStatsSchema,
    LawArticleResponseSchema,
    IngestionStatusSchema,
    safeParseResponse,
} from "@tezca/lib";
import { z } from "zod";

interface LawStructureNode {
    label: string;
    children: LawStructureNode[];
}

interface PaginatedResponse<T> {
    count: number;
    next: string | null;
    previous: string | null;
    results: T[];
}

interface AdminMetricsResponse {
    total_laws: number;
    counts: { federal: number; state: number };
    top_categories: { category: string; count: number }[];
    quality_distribution: Record<string, number> | null;
    last_updated: string;
}

import { API_BASE_URL } from './config';

class APIError extends Error {
    constructor(public status: number, message: string) {
        super(message);
        this.name = 'APIError';
    }
}

/**
 * Fetch data from the API and optionally validate against a Zod schema.
 * In development, validation errors are logged as warnings.
 * The raw data is always returned to avoid breaking the UI.
 */
async function fetcher<T>(endpoint: string, options?: RequestInit, schema?: z.ZodType<T>): Promise<T> {
    const url = `${API_BASE_URL}${endpoint}`;

    try {
        const response = await fetch(url, {
            ...options,
            headers: {
                'Content-Type': 'application/json',
                ...options?.headers,
            },
        });

        if (!response.ok) {
            throw new APIError(
                response.status,
                `API request failed: ${response.statusText}`
            );
        }

        const data = await response.json();

        if (schema && process.env.NODE_ENV === 'development') {
            const result = safeParseResponse(schema, data);
            if (!result.success) {
                console.warn(
                    `[API] Validation warning for ${endpoint}:`,
                    result.error.issues,
                );
            }
        }

        return data as T;
    } catch (error) {
        if (error instanceof APIError) {
            throw error;
        }
        throw new APIError(500, `Network error: ${(error as Error).message}`);
    }
}

export const api = {
    /**
     * Get paginated laws with optional filters
     */
    getLaws: async (options?: {
        page?: number;
        page_size?: number;
        tier?: string;
        state?: string;
        category?: string;
        status?: string;
        law_type?: string;
        sort?: string;
        q?: string;
    }): Promise<PaginatedResponse<LawListItem>> => {
        const params = new URLSearchParams();
        if (options?.page) params.set('page', options.page.toString());
        if (options?.page_size) params.set('page_size', options.page_size.toString());
        if (options?.tier) params.set('tier', options.tier);
        if (options?.state) params.set('state', options.state);
        if (options?.category) params.set('category', options.category);
        if (options?.status) params.set('status', options.status);
        if (options?.law_type) params.set('law_type', options.law_type);
        if (options?.sort) params.set('sort', options.sort);
        if (options?.q) params.set('q', options.q);
        const qs = params.toString();
        return fetcher<PaginatedResponse<LawListItem>>(`/laws/${qs ? `?${qs}` : ''}`);
    },

    /**
     * Get a single law by ID (flat Law object)
     */
    getLaw: async (lawId: string): Promise<Law> => {
        return fetcher<Law>(`/laws/${lawId}/`, undefined, LawSchema);
    },

    /**
     * Get full law detail including versions (raw API response shape)
     */
    getLawDetail: async (lawId: string): Promise<{ law: Record<string, string>; version: Record<string, string>; versions: Record<string, string>[] }> => {
        return fetcher(`/laws/${lawId}/`);
    },

    /**
     * Get list of states
     */
    getStates: async (): Promise<{ states: string[] }> => {
        return fetcher<{ states: string[] }>('/states/');
    },

    /**
     * Get global dashboard statistics
     */
    getStats: async (): Promise<DashboardStats> => {
        return fetcher<DashboardStats>('/stats/', undefined, DashboardStatsSchema);
    },

    /**
     * Search laws and articles
     */
    search: async (
        query: string,
        options?: {
            jurisdiction?: string[];
            category?: string | null;
            state?: string | null;
            municipality?: string | null;
            status?: string;
            law_type?: string;
            sort?: string;
            date_range?: string;
            title?: string;
            chapter?: string;
            page?: number;
            page_size?: number;
        }
    ): Promise<SearchResponse> => {
        const params = new URLSearchParams({ q: query });

        // Add optional filters
        if (options?.jurisdiction && options.jurisdiction.length > 0) {
            params.append('jurisdiction', options.jurisdiction.join(','));
        }
        if (options?.category && options.category !== 'all') {
            params.append('category', options.category);
        }
        if (options?.state && options.state !== 'all') {
            params.append('state', options.state);
        }
        if (options?.municipality && options.municipality !== 'all') {
            params.append('municipality', options.municipality);
        }
        if (options?.status && options.status !== 'all') {
            params.append('status', options.status);
        }
        if (options?.law_type && options.law_type !== 'all') {
            params.append('law_type', options.law_type);
        }
        if (options?.sort && options.sort !== 'relevance') {
            params.append('sort', options.sort);
        }
        if (options?.date_range && options.date_range !== 'all') {
            params.append('date_range', options.date_range);
        }
        if (options?.page) {
            params.append('page', options.page.toString());
        }
        if (options?.page_size) {
            params.append('page_size', options.page_size.toString());
        }

        // Structural filters
        if (options?.title) {
            params.append('title', options.title);
        }
        if (options?.chapter) {
            params.append('chapter', options.chapter);
        }

        return fetcher<SearchResponse>(`/search/?${params}`, undefined, SearchResponseSchema);
    },
    /**
     * Get full text (articles) of a law
     */
    getLawArticles: async (lawId: string): Promise<LawArticleResponse> => {
        return fetcher<LawArticleResponse>(`/laws/${lawId}/articles/`, undefined, LawArticleResponseSchema);
    },

    /**
     * Get structure (books, titles, chapters) for a law
     */
    getLawStructure: async (lawId: string): Promise<{ law_id: string; structure: LawStructureNode[] }> => {
        return fetcher<{ law_id: string; structure: LawStructureNode[] }>(`/laws/${lawId}/structure/`);
    },

    /**
     * Get municipalities with law counts
     */
    getMunicipalities: async (state?: string): Promise<{ municipality: string; state: string; count: number }[]> => {
        const params = state ? `?state=${encodeURIComponent(state)}` : '';
        const res = await fetch(`${API_BASE_URL}/municipalities/${params}`);
        if (!res.ok) return [];
        return res.json();
    },

    /**
     * Full-text search within a specific law's articles (ES-powered)
     */
    searchWithinLaw: async (lawId: string, q: string): Promise<{ total: number; results: { article_id: string; snippet: string; score: number }[] }> => {
        if (!q.trim()) return { total: 0, results: [] };
        return fetcher(`/laws/${lawId}/search/?q=${encodeURIComponent(q)}`);
    },

    /**
     * Law-name autocomplete suggestions
     */
    suggest: async (q: string): Promise<{ id: string; name: string; tier: string }[]> => {
        if (q.length < 2) return [];
        const res = await fetch(`${API_BASE_URL}/suggest/?q=${encodeURIComponent(q)}`);
        if (!res.ok) return [];
        const data = await res.json();
        return data.suggestions ?? data;
    },

    /**
     * Get related laws for a given law
     */
    getRelatedLaws: async (lawId: string): Promise<{ law_id: string; related: RelatedLaw[] }> => {
        return fetcher<{ law_id: string; related: RelatedLaw[] }>(`/laws/${lawId}/related/`);
    },

    /**
     * Get all categories with law counts
     */
    getCategories: async (): Promise<CategoryItem[]> => {
        return fetcher<CategoryItem[]>('/categories/');
    },

    /**
     * Get cross-reference statistics for a law
     */
    getLawReferences: async (lawId: string): Promise<{
        statistics: {
            total_outgoing: number;
            total_incoming: number;
            most_referenced_laws: { slug: string; count: number }[];
            most_citing_laws: { slug: string; count: number }[];
        };
    }> => {
        return fetcher(`/laws/${lawId}/references/`);
    },

    /**
     * Admin Dashboard endpoints
     */
    getAdminMetrics: async () => {
        return fetcher<AdminMetricsResponse>('/admin/metrics/');
    },

    getJobStatus: async () => {
        return fetcher<IngestionStatus>('/admin/jobs/status/', undefined, IngestionStatusSchema);
    },

    listJobs: async () => {
        return fetcher<{ jobs: IngestionStatus[] }>('/admin/jobs/');
    },

};

export { APIError };
