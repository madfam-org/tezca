import { IngestionStatus } from "@leyesmx/lib";

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
     * Get current ingestion status
     */
    getIngestionStatus: async (): Promise<IngestionStatus> => {
        return fetcher<IngestionStatus>('/ingest/');
    },

    /**
     * Start ingestion process
     */
    startIngestion: async (params: { mode: string; laws?: string; skip_download?: boolean }): Promise<IngestionStatus> => {
        return fetcher<IngestionStatus>('/ingest/', {
            method: 'POST',
            body: JSON.stringify(params),
        });
    },
};

export { APIError };
