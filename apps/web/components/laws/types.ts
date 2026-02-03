export interface Law {
    official_id: string;
    name: string;
    category: string;
    tier: string;
    state: string | null;
}

export interface LawVersion {
    publication_date: string | null;
    dof_url: string | null;
    xml_file?: string | null;
}

export interface Article {
    article_id: string;
    text: string;
    has_structure?: boolean;
}

export interface LawDetailData {
    law: Law;
    version: LawVersion;
    articles: Article[];
    total: number;
}
