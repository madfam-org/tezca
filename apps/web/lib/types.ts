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
    category?: string;
    tier?: number;
    versions: LawVersion[];
    articles?: number;
    grade?: 'A' | 'B' | 'C' | 'D' | 'F';
    score?: number;
}

export interface LawListItem {
    id: string;
    name: string;
    versions: number;
}

export interface SearchResult {
    id: string;
    law: string;
    article: string;
    snippet: string;
    score: number;
    date?: string;
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
