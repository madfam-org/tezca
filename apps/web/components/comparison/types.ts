import type { Law, LawArticleResponse } from "@tezca/lib";

export interface LawStructureNode {
    label: string;
    children: LawStructureNode[];
}

export interface ComparisonLawData {
    meta: Law;
    details: LawArticleResponse;
    structure: LawStructureNode[];
}
