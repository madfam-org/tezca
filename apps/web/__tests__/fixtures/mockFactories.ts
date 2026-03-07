/**
 * Shared mock data factories for UI data fidelity tests.
 * Generates realistic data matching actual API response shapes.
 */

// --- Constants ---

/** 200 realistic article IDs including roman numerals, Bis/Ter, Transitorios */
export const REALISTIC_ARTICLE_IDS: string[] = [
    ...Array.from({ length: 136 }, (_, i) => String(i + 1)),
    '1 Bis', '1 Bis 2', '2 Bis', '14 Bis',
    'I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII', 'IX', 'X',
    'XI', 'XII', 'XIII', 'XIV', 'XIV Bis', 'XV', 'XVI', 'XVII', 'XVIII', 'XIX', 'XX',
    'Primero Transitorio', 'Segundo Transitorio', 'Tercero Transitorio',
    'Cuarto Transitorio', 'Quinto Transitorio',
    'texto_completo',
    '1o', '2o', '3o',
    'A', 'B', 'C',
    'UNICO',
    '100-A', '100-B',
    ...Array.from({ length: 14 }, (_, i) => String(137 + i)),
];

export const LONG_LAW_NAME =
    'Ley General de los Derechos de Ni\u00f1as, Ni\u00f1os y Adolescentes en Materia de Protecci\u00f3n Integral de los Derechos Humanos de las Personas en Situaci\u00f3n de Vulnerabilidad, Discriminaci\u00f3n y Violencia Familiar, Comunitaria e Institucional en el \u00c1mbito Federal, Estatal y Municipal de los Estados Unidos Mexicanos y sus Instituciones P\u00fablicas Descentralizadas, \u00d3rganos Aut\u00f3nomos y Entidades Paraestatales, con Especial \u00c9nfasis en la Promoci\u00f3n de la Igualdad Sustantiva';

export const SPECIAL_CHARS_TEXT =
    'Art\u00edculo d\u00e9cimo \u2014 seg\u00fan \u00a72.1 \u00abproteger\u00bb las garant\u00edas \u2018individuales\u2019 del \u201cEstado\u201d';

export const MULTILINE_ARTICLE =
    'I. Los tribunales de la Federaci\u00f3n resolver\u00e1n toda controversia que se suscite:\n\na) Por normas generales, actos u omisiones de la autoridad que violen los derechos humanos reconocidos y las garant\u00edas otorgadas para su protecci\u00f3n por esta Constituci\u00f3n;\n\nb) Por normas generales o actos de la autoridad federal que vulneren o restrinjan la soberan\u00eda de los Estados o la autonom\u00eda de la Ciudad de M\u00e9xico;\n\nc) Por normas generales o actos de las autoridades de las entidades federativas que invadan la esfera de competencia de la autoridad federal.';

// --- Factories ---

export interface MockLawApiResponse {
    official_id: string;
    id: string;
    name: string;
    category: string;
    tier: string;
    state: string | null;
    status: string;
    last_verified: string | null;
    law?: Record<string, unknown>;
    versions: MockVersionItem[];
    version?: MockVersionItem;
}

export interface MockVersionItem {
    publication_date: string | null;
    valid_from?: string;
    valid_to?: string | null;
    dof_url?: string | null;
    change_summary?: string | null;
}

export interface MockArticle {
    article_id: string;
    text: string;
    has_structure?: boolean;
}

export interface MockArticlesApiResponse {
    law_id: string;
    law_name: string;
    total: number;
    articles: MockArticle[];
}

export interface MockSearchResult {
    id: string;
    law_id: string;
    law_name: string;
    article: string;
    snippet: string;
    score: number;
    tier: string;
    date: string | null;
    hierarchy: string[];
    municipality: string | null;
    law_type: string;
}

export interface MockRefLaw {
    slug: string;
    count: number;
}

export interface MockRefStats {
    total_outgoing: number;
    total_incoming: number;
    most_referenced_laws: MockRefLaw[];
    most_citing_laws: MockRefLaw[];
}

export function makeLawApiResponse(overrides: Partial<MockLawApiResponse> = {}): MockLawApiResponse {
    const defaults: MockLawApiResponse = {
        official_id: 'cpeum',
        id: 'cpeum',
        name: 'Constituci\u00f3n Pol\u00edtica de los Estados Unidos Mexicanos',
        category: 'Constitucional',
        tier: 'federal',
        state: null,
        status: 'vigente',
        last_verified: '2026-01-15',
        versions: [
            {
                publication_date: '2024-06-06',
                valid_from: '2024-06-07',
                valid_to: null,
                dof_url: 'https://www.dof.gob.mx/nota_detalle.php?codigo=1234',
                change_summary: 'Reforma en materia de bienestar',
            },
        ],
    };
    return { ...defaults, ...overrides };
}

export function makeArticlesApiResponse(
    count = 200,
    overrides: Partial<MockArticlesApiResponse> = {},
): MockArticlesApiResponse {
    const ids = REALISTIC_ARTICLE_IDS.slice(0, count);
    const articles: MockArticle[] = ids.map((id) => ({
        article_id: id,
        text: `Contenido del art\u00edculo ${id}. Los ciudadanos tienen derecho a participar en los asuntos p\u00fablicos de conformidad con las disposiciones establecidas.`,
    }));

    return {
        law_id: 'cpeum',
        law_name: 'Constituci\u00f3n Pol\u00edtica de los Estados Unidos Mexicanos',
        total: count,
        articles,
        ...overrides,
    };
}

export function makeVersions(count: number, overrides: Partial<MockVersionItem> = {}): MockVersionItem[] {
    return Array.from({ length: count }, (_, i) => ({
        publication_date: i === 0 ? '2024-06-06' : `${2024 - i}-01-15`,
        valid_from: i === 0 ? '2024-06-07' : `${2024 - i}-01-16`,
        valid_to: i === 0 ? null : `${2025 - i}-01-14`,
        dof_url: i % 3 === 0 ? `https://www.dof.gob.mx/nota_detalle.php?codigo=${5000 + i}` : null,
        change_summary: i === 0 ? 'Reforma vigente' : `Reforma ${2024 - i}`,
        ...overrides,
    }));
}

export function makeRefStats(
    outgoingCount = 8,
    incomingCount = 6,
): MockRefStats {
    const outgoing: MockRefLaw[] = Array.from({ length: outgoingCount }, (_, i) => ({
        slug: `ley-${String.fromCharCode(97 + i)}`,
        count: 10 - i,
    }));
    const incoming: MockRefLaw[] = Array.from({ length: incomingCount }, (_, i) => ({
        slug: `ley-citante-${i + 1}`,
        count: 8 - i,
    }));

    return {
        total_outgoing: outgoing.reduce((s, r) => s + r.count, 0),
        total_incoming: incoming.reduce((s, r) => s + r.count, 0),
        most_referenced_laws: outgoing,
        most_citing_laws: incoming,
    };
}

export function makeSearchResponse(
    count = 10,
    overrides: Partial<{ total: number; facets: Record<string, { key: string; doc_count: number }[]>; max_page_size: number }> = {},
) {
    const results: MockSearchResult[] = Array.from({ length: count }, (_, i) => ({
        id: `result-${i}`,
        law_id: `ley-${i}`,
        law_name: `Ley de Prueba ${i + 1}`,
        article: `Art. ${i + 1}`,
        snippet: `Texto con <em>amparo</em> referencia legal n\u00famero ${i + 1}`,
        score: 10 - i * 0.5,
        tier: i < 3 ? 'federal' : i < 7 ? 'state' : 'municipal',
        date: `2024-0${(i % 9) + 1}-15`,
        hierarchy: i % 2 === 0 ? ['T\u00edtulo I', 'Cap\u00edtulo II'] : [],
        municipality: i >= 7 ? 'Guadalajara' : null,
        law_type: i === 5 ? 'non_legislative' : 'legislative',
    }));

    return {
        total: overrides.total ?? count * 10,
        total_pages: Math.ceil((overrides.total ?? count * 10) / 10),
        results,
        facets: overrides.facets ?? {
            tier: [
                { key: 'federal', doc_count: 500 },
                { key: 'state', doc_count: 300 },
                { key: 'municipal', doc_count: 100 },
            ],
            category: [
                { key: 'Constitucional', doc_count: 200 },
                { key: 'Civil', doc_count: 150 },
            ],
        },
        max_page_size: overrides.max_page_size ?? 100,
        warning: undefined,
    };
}

export function makeComparisonLawData(articleCount = 50) {
    const articles = Array.from({ length: articleCount }, (_, i) => ({
        article_id: String(i + 1),
        text: `Texto del art\u00edculo ${i + 1} de la ley. Contenido legal detallado que establece las disposiciones aplicables en la materia.`,
    }));

    return {
        meta: {
            id: 'test-law',
            name: 'Ley de Prueba',
            tier: 'federal',
            category: 'Civil',
            articles: articleCount,
        },
        details: {
            law_id: 'test-law',
            law_name: 'Ley de Prueba',
            total: articleCount,
            articles,
        },
        structure: [
            { label: 'T\u00edtulo Primero', children: [{ label: 'Cap\u00edtulo I', children: [] }] },
        ],
    };
}
