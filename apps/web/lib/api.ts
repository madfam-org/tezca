import type { Law, LawListItem, SearchResponse } from './types';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

class APIError extends Error {
    constructor(public status: number, message: string) {
        super(message);
        this.name = 'APIError';
    }
}

async function fetcher<T>(endpoint: string, options?: RequestInit): Promise<T> {
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

        return response.json();
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
        return fetcher<LawListItem[]>('/laws/');
    },

    /**
     * Get a single law by ID
     */
    getLaw: async (lawId: string): Promise<Law> => {
        return fetcher<Law>(`/laws/${lawId}/`);
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
    getStats: async (): Promise<import('./types').DashboardStats> => {
        return fetcher<import('./types').DashboardStats>('/stats/');
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
            status?: string;
            sort?: string;
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
        if (options?.status && options.status !== 'all') {
            params.append('status', options.status);
        }
        if (options?.sort && options.sort !== 'relevance') {
            params.append('sort', options.sort);
        }
        if (options?.page) {
            params.append('page', options.page.toString());
        }
        if (options?.page_size) {
            params.append('page_size', options.page_size.toString());
        }

        return fetcher<SearchResponse>(`/search/?${params}`);
    },
};

export { APIError };
