import type { Law, LawListItem, SearchResponse, DashboardStats, LawArticleResponse, IngestionStatus } from "@leyesmx/lib";
import {
    LawSchema,
    LawListItemSchema,
    SearchResponseSchema,
    DashboardStatsSchema,
    LawArticleResponseSchema,
    IngestionStatusSchema,
    safeParseResponse,
} from "@leyesmx/lib";
import { z } from "zod";

interface LawStructureNode {
    label: string;
    children: LawStructureNode[];
}

interface AdminMetricsResponse {
    total_laws: number;
    counts: { federal: number; state: number };
    top_categories: { category: string; count: number }[];
    quality_distribution: Record<string, number> | null;
    last_updated: string;
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

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
     * Get all laws
     */
    getLaws: async (): Promise<LawListItem[]> => {
        return fetcher<LawListItem[]>('/laws/', undefined, z.array(LawListItemSchema));
    },

    /**
     * Get a single law by ID
     */
    getLaw: async (lawId: string): Promise<Law> => {
        return fetcher<Law>(`/laws/${lawId}/`, undefined, LawSchema);
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
