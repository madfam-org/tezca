import type { IngestionStatus } from "@tezca/lib";
import type { DashboardData, RoadmapData } from "@/components/dataops/types";

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

export interface SystemMetrics {
    total_laws: number;
    counts: { federal: number; state: number; municipal: number };
    top_categories: { category: string; count: number }[];
    quality_distribution: Record<string, number> | null;
    last_updated: string;
}

export interface SystemConfig {
    environment: {
        debug: boolean;
        allowed_hosts: string[];
        language: string;
        timezone: string;
    };
    database: {
        engine: string;
        status: string;
        name: string;
    };
    elasticsearch: {
        host: string;
        status: string;
    };
    data: {
        total_laws: number;
        total_versions: number;
        latest_publication: string | null;
    };
}

export interface HealthCheck {
    status: string;
    database: string;
    timestamp: string;
}

export const api = {
    getIngestionStatus: async (): Promise<IngestionStatus> => {
        return fetcher<IngestionStatus>('/ingest/');
    },

    startIngestion: async (params: { mode: string; laws?: string; skip_download?: boolean }): Promise<IngestionStatus> => {
        return fetcher<IngestionStatus>('/ingest/', {
            method: 'POST',
            body: JSON.stringify(params),
        });
    },

    getMetrics: async (): Promise<SystemMetrics> => {
        return fetcher<SystemMetrics>('/admin/metrics/');
    },

    getConfig: async (): Promise<SystemConfig> => {
        return fetcher<SystemConfig>('/admin/config/');
    },

    getHealth: async (): Promise<HealthCheck> => {
        return fetcher<HealthCheck>('/admin/health/');
    },

    getCoverage: async () => {
        return fetcher<Record<string, unknown>>('/admin/coverage/');
    },

    getHealthSources: async () => {
        return fetcher<Record<string, unknown>>('/admin/health-sources/');
    },

    getGaps: async () => {
        return fetcher<Record<string, unknown>>('/admin/gaps/');
    },

    getCoverageDashboard: async (): Promise<DashboardData> => {
        return fetcher<DashboardData>('/admin/coverage/dashboard/');
    },

    getRoadmap: async (): Promise<RoadmapData> => {
        return fetcher<RoadmapData>('/admin/roadmap/');
    },

    updateRoadmapItem: async (data: { id: number; status?: string; progress_pct?: number; notes?: string }) => {
        return fetcher<{ ok: boolean; id: number; status: string; progress_pct: number }>('/admin/roadmap/', {
            method: 'PATCH',
            body: JSON.stringify(data),
        });
    },
};

export { APIError };
