// TypeScript types for API responses

export interface LawVersion {
    publication_date: string;
    valid_from: string;
    dof_url: string;
    xml_file: string | null;
}

export interface Law {
    id: string;
    name: string;
    short_name?: string;
    fullName?: string;
    category?: string;
    tier?: number | string;
    versions?: LawVersion[];
    articles?: number;
    transitorios?: number;
    grade?: 'A' | 'B' | 'C' | 'D' | 'F';
    score?: number;
    priority?: number;
    file?: string;
}

export type Article = LawArticle;

export interface LawListItem {
    id: string;
    name: string;
    versions: number;
}

export interface SearchResult {
    id: string;
    law_id: string;
    law_name: string;
    article: string;
    snippet: string;
    score: number;
    date?: string;
    municipality?: string;
}

export interface SearchResponse {
    results: SearchResult[];
    total?: number;
    page?: number;
    page_size?: number;
    total_pages?: number;
    warning?: string;
}

export interface APIError {
    error: string;
    details?: string;
}

export interface DashboardStats {
    total_laws: number;
    federal_count: number;
    state_count: number;
    municipal_count: number;
    total_articles: number;
    federal_coverage: number;
    state_coverage: number;
    municipal_coverage: number;
    total_coverage: number;
    last_update: string | null;
    recent_laws: {
        id: string;
        name: string;
        date: string;
        tier: string;
        category: string;
    }[];
}

export interface LawArticle {
    article_id: string;
    text: string;
}

export interface LawArticleResponse {
    law_id: string;
    law_name: string;
    total: number;
    articles: LawArticle[];
}

// Admin / Ingestion Types
export interface IngestionResults {
    success_count: number;
    total_laws: number;
    duration_seconds?: number;
}

export interface IngestionStatus {
    status: 'idle' | 'running' | 'completed' | 'failed' | 'error';
    message: string;
    timestamp: string;
    progress?: number;
    params?: Record<string, unknown>;
    results?: IngestionResults;
    warning?: string;
}
