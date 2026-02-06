import type { Law, LawArticleResponse } from "@leyesmx/lib";

export interface LawStructureNode {
    label: string;
    children: LawStructureNode[];
}

export interface ComparisonLawData {
    meta: Law;
    details: LawArticleResponse;
    structure: LawStructureNode[];
}
