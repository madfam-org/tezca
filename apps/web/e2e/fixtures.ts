import { test as base, type Page } from '@playwright/test';

/**
 * Mock API data used across all E2E tests.
 * Intercepts fetch calls to the backend so tests run without a live Django server.
 */

export const MOCK_STATS = {
    total_laws: 11904,
    federal_count: 333,
    state_count: 11363,
    municipal_count: 208,
    last_update: '2026-02-01T00:00:00Z',
    recent_laws: [
        { id: 'ley-federal-del-trabajo', name: 'Ley Federal del Trabajo', tier: 'federal', date: '2026-01-15' },
        { id: 'codigo-civil-federal', name: 'Código Civil Federal', tier: 'federal', date: '2026-01-10' },
    ],
};

export const MOCK_LAW = {
    id: 'ley-federal-del-trabajo',
    name: 'Ley Federal del Trabajo',
    short_name: 'LFT',
    category: 'Laboral',
    tier: 'federal',
    articles: 0,
    grade: 'A',
    score: 92,
    priority: 1,
};

export const MOCK_LAW_2 = {
    id: 'codigo-civil-federal',
    name: 'Código Civil Federal',
    short_name: 'CCF',
    category: 'Civil',
    tier: 'federal',
    articles: 0,
    grade: 'B',
    score: 85,
    priority: 2,
};

export const MOCK_ARTICLES = {
    law_id: 'ley-federal-del-trabajo',
    law_name: 'Ley Federal del Trabajo',
    total: 3,
    articles: [
        { article_id: 'Art. 1', text: 'La presente Ley es de observancia general en toda la República.' },
        { article_id: 'Art. 2', text: 'Las normas del trabajo tienden a conseguir el equilibrio entre los factores de la producción.' },
        { article_id: 'Art. 3', text: 'El trabajo es un derecho y un deber social.' },
    ],
};

export const MOCK_ARTICLES_2 = {
    law_id: 'codigo-civil-federal',
    law_name: 'Código Civil Federal',
    total: 2,
    articles: [
        { article_id: 'Art. 1', text: 'Las disposiciones de este Código regirán en el Distrito Federal.' },
        { article_id: 'Art. 4', text: 'Las leyes, decretos, reglamentos y circulares se reputarán vigentes.' },
    ],
};

export const MOCK_STRUCTURE = {
    law_id: 'ley-federal-del-trabajo',
    structure: [
        { label: 'Título Primero - Principios Generales', children: [] },
        { label: 'Título Segundo - Relaciones de Trabajo', children: [] },
    ],
};

export const MOCK_STRUCTURE_2 = {
    law_id: 'codigo-civil-federal',
    structure: [
        { label: 'Libro Primero - De las Personas', children: [] },
    ],
};

export const MOCK_SEARCH_RESULTS = {
    results: [
        {
            id: '1',
            law_id: 'ley-federal-del-trabajo',
            law_name: 'Ley Federal del Trabajo',
            article: 'Art. 1',
            snippet: 'La presente <em>Ley</em> es de observancia general en toda la República.',
            score: 9.5,
            date: '2026-01-15',
        },
        {
            id: '2',
            law_id: 'codigo-civil-federal',
            law_name: 'Código Civil Federal',
            article: 'Art. 1',
            snippet: 'Las disposiciones de este <em>Código</em> regirán en el Distrito Federal.',
            score: 8.2,
            date: '2026-01-10',
        },
    ],
    total: 2,
    total_pages: 1,
};

/**
 * Setup API route mocking for a page.
 * Call this in beforeEach or at the start of each test.
 */
export async function mockApiRoutes(page: Page) {
    const API = '**/api/v1';

    await page.route(`${API}/stats/`, (route) =>
        route.fulfill({ json: MOCK_STATS })
    );

    await page.route(`${API}/search/?*`, (route) =>
        route.fulfill({ json: MOCK_SEARCH_RESULTS })
    );

    // Laws list (paginated) — must be before individual law routes
    await page.route(`${API}/laws/`, (route) => {
        const url = new URL(route.request().url());
        // Only intercept the list endpoint (no sub-path like /laws/some-id/)
        if (url.pathname.endsWith('/laws/') || url.pathname.endsWith('/laws')) {
            return route.fulfill({ json: {
                count: 2,
                next: null,
                previous: null,
                results: [
                    { id: MOCK_LAW.id, name: MOCK_LAW.name, tier: MOCK_LAW.tier, versions: 1 },
                    { id: MOCK_LAW_2.id, name: MOCK_LAW_2.name, tier: MOCK_LAW_2.tier, versions: 1 },
                ],
            } });
        }
        return route.fallback();
    });

    await page.route(`${API}/laws/ley-federal-del-trabajo/`, (route) =>
        route.fulfill({ json: MOCK_LAW })
    );
    await page.route(`${API}/laws/codigo-civil-federal/`, (route) =>
        route.fulfill({ json: MOCK_LAW_2 })
    );

    await page.route(`${API}/laws/ley-federal-del-trabajo/articles/`, (route) =>
        route.fulfill({ json: MOCK_ARTICLES })
    );
    await page.route(`${API}/laws/codigo-civil-federal/articles/`, (route) =>
        route.fulfill({ json: MOCK_ARTICLES_2 })
    );

    await page.route(`${API}/laws/ley-federal-del-trabajo/structure/`, (route) =>
        route.fulfill({ json: MOCK_STRUCTURE })
    );
    await page.route(`${API}/laws/codigo-civil-federal/structure/`, (route) =>
        route.fulfill({ json: MOCK_STRUCTURE_2 })
    );

    await page.route(`${API}/states/`, (route) =>
        route.fulfill({ json: { states: ['Jalisco', 'CDMX', 'Nuevo León'] } })
    );

    await page.route(`${API}/suggest/?*`, (route) =>
        route.fulfill({ json: { suggestions: [
            { id: 'ley-federal-del-trabajo', name: 'Ley Federal del Trabajo', tier: 'federal' },
        ] } })
    );

    await page.route(`${API}/municipalities/?*`, (route) =>
        route.fulfill({ json: [] })
    );

    await page.route(`${API}/laws/*/search/?*`, (route) =>
        route.fulfill({ json: { law_id: 'ley-federal-del-trabajo', query: 'test', total: 1, results: [
            { article_id: 'Art. 1', snippet: 'La presente <em>Ley</em> es de observancia general.', score: 5.0 },
        ] } })
    );
}

/** Extended test fixture with API mocking pre-applied */
export const test = base.extend<{ mockApi: void }>({
    mockApi: [async ({ page }, use) => {
        await mockApiRoutes(page);
        await use();
    }, { auto: true }],
});

export { expect } from '@playwright/test';
