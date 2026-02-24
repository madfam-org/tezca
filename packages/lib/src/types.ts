// TypeScript types for API responses

export interface LawVersion {
    publication_date: string;
    valid_from: string | null;
    valid_to?: string | null;
    dof_url: string | null;
    change_summary?: string | null;
    xml_file: string | null;
}

export interface Law {
    id: string;
    name: string;
    short_name?: string;
    fullName?: string;
    category?: string;
    tier?: string;
    law_type?: 'legislative' | 'non_legislative';
    state?: string;
    status?: string;
    last_verified?: string;
    source_url?: string;
    versions?: LawVersion[];
    articles?: number;
    transitorios?: number;
    grade?: 'A' | 'B' | 'C' | 'D' | 'F';
    score?: number;
    priority?: number;
    file?: string;
    degraded?: boolean;
}

export type Article = LawArticle;

export interface LawListItem {
    id: string;
    name: string;
    tier?: string;
    law_type?: 'legislative' | 'non_legislative';
    category?: string;
    status?: string;
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
    tier?: string | null;
    law_type?: string | null;
    state?: string;
    municipality?: string;
    hierarchy?: string[];
    book?: string;
    title?: string;
    chapter?: string;
}

export interface FacetBucket {
    key: string;
    count: number;
}

export interface SearchResponse {
    results: SearchResult[];
    total?: number;
    page?: number;
    page_size?: number;
    total_pages?: number;
    warning?: string;
    facets?: Record<string, FacetBucket[]>;
}

export interface APIError {
    error: string;
    details?: string;
}

export interface CoverageItem {
    label?: string;
    count: number;
    universe: number | null;
    percentage: number | null;
    description?: string;
    source?: string;
    last_verified?: string;
    permanent_gaps?: number;
    cities_covered?: number;
    total_municipalities?: number;
}

export interface CoverageBreakdown {
    leyes_vigentes: CoverageItem;
    federal: CoverageItem;
    state: CoverageItem;
    state_all_powers: CoverageItem;
    municipal: CoverageItem;
}

export interface DashboardStats {
    total_laws: number;
    federal_count: number;
    state_count: number;
    municipal_count: number;
    legislative_count: number;
    non_legislative_count: number;
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
    coverage?: CoverageBreakdown;
    degraded?: boolean;
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

// Related Laws
export interface RelatedLaw {
    law_id: string;
    name: string;
    tier: string;
    category?: string;
    state?: string;
    score: number;
}

// Categories
export interface CategoryItem {
    category: string;
    count: number;
    label?: string;
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
