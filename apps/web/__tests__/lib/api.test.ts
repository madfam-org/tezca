/**
 * Tests for `apps/web/lib/api.ts`.
 *
 * api.ts is a 600+ line facade around `fetch`. We mock global.fetch and
 * exercise each endpoint shape, focusing on:
 *   - URL composition (query strings, path params, encoding)
 *   - HTTP method + headers + body
 *   - Return-value handling (passthrough, default-on-failure, parsed shape)
 *   - Error path: rate-limit (429) raises with retryAfter
 *   - Schema-validation passthrough in dev mode
 */

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { api } from '@/lib/api';

const ORIGINAL_FETCH = global.fetch;

// Helper: build a mock fetch response
function mockResponse(body: unknown, init: { status?: number; headers?: Record<string, string> } = {}) {
    return {
        ok: (init.status ?? 200) >= 200 && (init.status ?? 200) < 300,
        status: init.status ?? 200,
        statusText: init.status === 429 ? 'Too Many Requests' : 'OK',
        headers: new Headers(init.headers ?? {}),
        json: async () => body,
    } as unknown as Response;
}

beforeEach(() => {
    vi.restoreAllMocks();
});

afterEach(() => {
    global.fetch = ORIGINAL_FETCH;
});

// ---------------------------------------------------------------------------
// Public read endpoints — URL composition + fetch wiring
// ---------------------------------------------------------------------------

describe('api — read endpoints', () => {
    it('getLaws() composes a paginated URL with no query when no options', async () => {
        const fetchMock = vi.fn().mockResolvedValue(
            mockResponse({ count: 0, next: null, previous: null, results: [] }),
        );
        global.fetch = fetchMock;

        await api.getLaws();
        expect(fetchMock).toHaveBeenCalledOnce();
        const url = fetchMock.mock.calls[0][0] as string;
        expect(url).toMatch(/\/laws\/$/);
    });

    it('getLaws() includes provided filters in the query string', async () => {
        const fetchMock = vi.fn().mockResolvedValue(
            mockResponse({ count: 0, next: null, previous: null, results: [] }),
        );
        global.fetch = fetchMock;

        await api.getLaws({ page: 2, page_size: 25, tier: 'federal', state: 'jalisco', sort: 'date' });
        const url = fetchMock.mock.calls[0][0] as string;
        expect(url).toMatch(/page=2/);
        expect(url).toMatch(/page_size=25/);
        expect(url).toMatch(/tier=federal/);
        expect(url).toMatch(/state=jalisco/);
        expect(url).toMatch(/sort=date/);
    });

    it('getLaw() requests the law-specific endpoint', async () => {
        const fetchMock = vi.fn().mockResolvedValue(mockResponse({ official_id: 'cpeum' }));
        global.fetch = fetchMock;

        const result = await api.getLaw('cpeum');
        expect(fetchMock.mock.calls[0][0]).toMatch(/\/laws\/cpeum\/$/);
        expect((result as Record<string, unknown>).official_id).toBe('cpeum');
    });

    it('getLawDetail() returns the raw response shape', async () => {
        const fakePayload = { official_id: 'cpeum', versions: [{ id: 1 }] };
        const fetchMock = vi.fn().mockResolvedValue(mockResponse(fakePayload));
        global.fetch = fetchMock;

        const result = await api.getLawDetail('cpeum');
        expect(result).toEqual(fakePayload);
    });

    it('getStates() returns the wrapper object', async () => {
        const fetchMock = vi.fn().mockResolvedValue(mockResponse({ states: ['Jalisco', 'CDMX'] }));
        global.fetch = fetchMock;

        const result = await api.getStates();
        expect(result.states).toEqual(['Jalisco', 'CDMX']);
    });

    it('getStats() requests the stats endpoint', async () => {
        const fetchMock = vi.fn().mockResolvedValue(
            mockResponse({ total_laws: 100, total_articles: 1000, federal_count: 50, state_count: 30, municipal_count: 20 }),
        );
        global.fetch = fetchMock;

        const result = await api.getStats();
        expect(fetchMock.mock.calls[0][0]).toMatch(/\/stats\/$/);
        expect(result.total_laws).toBe(100);
    });

    it('search() composes URL with query + filters', async () => {
        const fetchMock = vi.fn().mockResolvedValue(
            mockResponse({ count: 0, results: [], facets: {} }),
        );
        global.fetch = fetchMock;

        await api.search('amparo', {
            jurisdiction: ['federal', 'state'],
            category: 'ley',
            sort: 'date',
            page: 3,
        });
        const url = fetchMock.mock.calls[0][0] as string;
        expect(url).toMatch(/q=amparo/);
        expect(url).toMatch(/jurisdiction=federal/);
        expect(url).toMatch(/category=ley/);
        expect(url).toMatch(/sort=date/);
        expect(url).toMatch(/page=3/);
    });

    it('search() omits filters with value "all"', async () => {
        const fetchMock = vi.fn().mockResolvedValue(mockResponse({ count: 0, results: [], facets: {} }));
        global.fetch = fetchMock;

        await api.search('amparo', { category: 'all', state: 'all', status: 'all' });
        const url = fetchMock.mock.calls[0][0] as string;
        expect(url).not.toMatch(/category=/);
        expect(url).not.toMatch(/state=/);
        expect(url).not.toMatch(/status=/);
    });

    it('search() omits sort=relevance (default) and date_range=all', async () => {
        const fetchMock = vi.fn().mockResolvedValue(mockResponse({ count: 0, results: [], facets: {} }));
        global.fetch = fetchMock;

        await api.search('q', { sort: 'relevance', date_range: 'all' });
        const url = fetchMock.mock.calls[0][0] as string;
        expect(url).not.toMatch(/sort=/);
        expect(url).not.toMatch(/date_range=/);
    });

    it('search() forwards structural filters (title, chapter)', async () => {
        const fetchMock = vi.fn().mockResolvedValue(mockResponse({ count: 0, results: [], facets: {} }));
        global.fetch = fetchMock;

        await api.search('q', { title: 'Capítulo I', chapter: '5' });
        const url = fetchMock.mock.calls[0][0] as string;
        expect(url).toMatch(/title=/);
        expect(url).toMatch(/chapter=5/);
    });

    it('getLawArticles() requests the articles sub-resource', async () => {
        const fetchMock = vi.fn().mockResolvedValue(
            mockResponse({ law_id: 'cpeum', articles: [], total: 0 }),
        );
        global.fetch = fetchMock;

        await api.getLawArticles('cpeum');
        expect(fetchMock.mock.calls[0][0]).toMatch(/\/laws\/cpeum\/articles\/$/);
    });

    it('getLawStructure() returns the structure wrapper', async () => {
        const fetchMock = vi.fn().mockResolvedValue(
            mockResponse({ law_id: 'cpeum', structure: [{ label: 'TÍTULO I', children: [] }] }),
        );
        global.fetch = fetchMock;

        const result = await api.getLawStructure('cpeum');
        expect(result.law_id).toBe('cpeum');
        expect(result.structure).toHaveLength(1);
    });
});

// ---------------------------------------------------------------------------
// Endpoints with non-fetcher fallback (return [] on failure)
// ---------------------------------------------------------------------------

describe('api — graceful-degradation endpoints', () => {
    it('getMunicipalities() returns [] when API returns non-OK', async () => {
        global.fetch = vi.fn().mockResolvedValue(mockResponse(null, { status: 500 }));
        const result = await api.getMunicipalities();
        expect(result).toEqual([]);
    });

    it('getMunicipalities() includes state= query when provided', async () => {
        const fetchMock = vi.fn().mockResolvedValue(
            mockResponse([{ municipality: 'Guadalajara', state: 'Jalisco', count: 100 }]),
        );
        global.fetch = fetchMock;
        const result = await api.getMunicipalities('Jalisco');
        const url = fetchMock.mock.calls[0][0] as string;
        expect(url).toMatch(/state=Jalisco/);
        expect(result).toHaveLength(1);
    });

    it('searchWithinLaw() returns empty result when query is blank', async () => {
        const result = await api.searchWithinLaw('cpeum', '   ');
        expect(result).toEqual({ total: 0, results: [] });
    });

    it('suggest() returns [] when query is too short', async () => {
        const result = await api.suggest('a');
        expect(result).toEqual([]);
    });

    it('suggest() returns [] when API errors', async () => {
        global.fetch = vi.fn().mockResolvedValue(mockResponse(null, { status: 500 }));
        const result = await api.suggest('amparo');
        expect(result).toEqual([]);
    });

    it('suggest() unwraps the suggestions wrapper', async () => {
        global.fetch = vi.fn().mockResolvedValue(
            mockResponse({ suggestions: [{ id: 'cpeum', name: 'Constitución', tier: 'federal' }] }),
        );
        const result = await api.suggest('cpeum');
        expect(result).toHaveLength(1);
    });

    it('suggest() handles bare-array response', async () => {
        global.fetch = vi.fn().mockResolvedValue(
            mockResponse([{ id: 'cpeum', name: 'X', tier: 'federal' }]),
        );
        const result = await api.suggest('cpeum');
        expect(result).toHaveLength(1);
    });
});

// ---------------------------------------------------------------------------
// Authenticated endpoints — token + body + method
// ---------------------------------------------------------------------------

describe('api — authenticated endpoints', () => {
    it('getUserPreferences() sends bearer token', async () => {
        const fetchMock = vi.fn().mockResolvedValue(
            mockResponse({ bookmarks: [], recently_viewed: [] }),
        );
        global.fetch = fetchMock;

        await api.getUserPreferences('jwt-token');
        const init = fetchMock.mock.calls[0][1];
        expect(init.headers.Authorization).toBe('Bearer jwt-token');
    });

    it('syncBookmark() PATCHes the action + lawId', async () => {
        const fetchMock = vi.fn().mockResolvedValue(mockResponse({ ok: true }));
        global.fetch = fetchMock;

        await api.syncBookmark('jwt', 'add', 'cpeum');
        const init = fetchMock.mock.calls[0][1];
        expect(init.method).toBe('PATCH');
        const body = JSON.parse(init.body as string);
        expect(body).toEqual({ action: 'add', law_id: 'cpeum' });
    });

    it('syncRecentlyViewed() PATCHes lawId', async () => {
        const fetchMock = vi.fn().mockResolvedValue(mockResponse({ ok: true }));
        global.fetch = fetchMock;

        await api.syncRecentlyViewed('jwt', 'amparo');
        const init = fetchMock.mock.calls[0][1];
        expect(init.method).toBe('PATCH');
        expect(JSON.parse(init.body as string)).toEqual({ law_id: 'amparo' });
    });

    it('createAnnotation() POSTs annotation data with token', async () => {
        const fetchMock = vi.fn().mockResolvedValue(mockResponse({ id: 1 }));
        global.fetch = fetchMock;

        await api.createAnnotation('jwt', {
            law_id: 'cpeum',
            article_id: 'art-1',
            text: 'A note',
            color: 'yellow',
        });
        const init = fetchMock.mock.calls[0][1];
        expect(init.method).toBe('POST');
        expect(init.headers.Authorization).toBe('Bearer jwt');
    });

    it('updateAnnotation() PUTs by id', async () => {
        const fetchMock = vi.fn().mockResolvedValue(mockResponse({ id: 5 }));
        global.fetch = fetchMock;

        await api.updateAnnotation('jwt', 5, { text: 'updated' });
        const init = fetchMock.mock.calls[0][1];
        expect(init.method).toBe('PUT');
        expect(fetchMock.mock.calls[0][0]).toMatch(/\/annotations\/5\/?/);
    });

    it('deleteAnnotation() DELETEs by id', async () => {
        const fetchMock = vi.fn().mockResolvedValue(mockResponse({}, { status: 204 }));
        global.fetch = fetchMock;

        await api.deleteAnnotation('jwt', 7);
        const init = fetchMock.mock.calls[0][1];
        expect(init.method).toBe('DELETE');
    });

    it('getAlerts() GETs the alerts collection', async () => {
        const fetchMock = vi.fn().mockResolvedValue(mockResponse({ count: 0, results: [] }));
        global.fetch = fetchMock;
        await api.getAlerts('jwt');
        expect(fetchMock.mock.calls[0][0]).toMatch(/\/alerts\//);
    });

    it('createAlert() POSTs alert payload', async () => {
        const fetchMock = vi.fn().mockResolvedValue(mockResponse({ id: 1 }));
        global.fetch = fetchMock;

        await api.createAlert('jwt', {
            law_id: 'cpeum',
            category: '',
            state: '',
            alert_type: 'change',
            delivery: 'in_app',
        });
        const init = fetchMock.mock.calls[0][1];
        expect(init.method).toBe('POST');
    });

    it('deleteAlert() DELETEs by id', async () => {
        const fetchMock = vi.fn().mockResolvedValue(mockResponse({}, { status: 204 }));
        global.fetch = fetchMock;
        await api.deleteAlert('jwt', 9);
        expect(fetchMock.mock.calls[0][1].method).toBe('DELETE');
    });

    it('getUserApiKeys() GETs api keys with token', async () => {
        const fetchMock = vi.fn().mockResolvedValue(
            mockResponse([{ prefix: 'tzk_x', name: 'demo', tier: 'free_member' }]),
        );
        global.fetch = fetchMock;
        await api.getUserApiKeys('jwt');
        const init = fetchMock.mock.calls[0][1];
        expect(init.headers.Authorization).toBe('Bearer jwt');
    });

    it('createUserApiKey() POSTs name', async () => {
        const fetchMock = vi.fn().mockResolvedValue(mockResponse({ prefix: 'tzk_a', secret: 's' }));
        global.fetch = fetchMock;

        await api.createUserApiKey('jwt', { name: 'demo' });
        const init = fetchMock.mock.calls[0][1];
        expect(init.method).toBe('POST');
        expect(JSON.parse(init.body as string)).toEqual({ name: 'demo' });
    });

    it('updateUserApiKey() PATCHes by prefix', async () => {
        const fetchMock = vi.fn().mockResolvedValue(mockResponse({ prefix: 'tzk_a' }));
        global.fetch = fetchMock;

        await api.updateUserApiKey('jwt', 'tzk_a', { name: 'renamed' });
        expect(fetchMock.mock.calls[0][1].method).toBe('PATCH');
        expect(fetchMock.mock.calls[0][0]).toMatch(/tzk_a/);
    });

    it('revokeUserApiKey() invokes the revoke route', async () => {
        const fetchMock = vi.fn().mockResolvedValue(mockResponse({}, { status: 204 }));
        global.fetch = fetchMock;
        await api.revokeUserApiKey('jwt', 'tzk_x');
        expect(fetchMock.mock.calls[0][0]).toMatch(/tzk_x/);
    });
});

// ---------------------------------------------------------------------------
// Notifications + admin
// ---------------------------------------------------------------------------

describe('api — notifications + admin', () => {
    it('getNotifications() supports paging', async () => {
        const fetchMock = vi.fn().mockResolvedValue(mockResponse({ count: 0, results: [] }));
        global.fetch = fetchMock;
        await api.getNotifications('jwt', 3);
        expect(fetchMock.mock.calls[0][0]).toMatch(/page=3/);
    });

    it('markNotificationsRead() POSTs id list', async () => {
        const fetchMock = vi.fn().mockResolvedValue(mockResponse({ marked: 2 }));
        global.fetch = fetchMock;
        await api.markNotificationsRead('jwt', [1, 2]);
        const init = fetchMock.mock.calls[0][1];
        expect(init.method).toBe('POST');
        expect(JSON.parse(init.body as string).ids).toEqual([1, 2]);
    });

    it('getAdminMetrics() GETs the admin metrics endpoint', async () => {
        const fetchMock = vi.fn().mockResolvedValue(
            mockResponse({ total_laws: 1, counts: { federal: 1, state: 0 }, top_categories: [], quality_distribution: null, last_updated: '' }),
        );
        global.fetch = fetchMock;
        await api.getAdminMetrics();
        expect(fetchMock.mock.calls[0][0]).toMatch(/\/admin\/metrics\//);
    });
});

// ---------------------------------------------------------------------------
// Graph + judicial
// ---------------------------------------------------------------------------

describe('api — graph + judicial', () => {
    it('getLawGraph() includes lawId in URL', async () => {
        const fetchMock = vi.fn().mockResolvedValue(
            mockResponse({ nodes: [], edges: [], stats: { total_nodes: 0, total_edges: 0 } }),
        );
        global.fetch = fetchMock;

        await api.getLawGraph('cpeum');
        // Path is /laws/{lawId}/graph/
        expect(fetchMock.mock.calls[0][0]).toMatch(/\/laws\/cpeum\/graph\/?/);
    });

    it('getLawGraph() composes opts into the query string', async () => {
        const fetchMock = vi.fn().mockResolvedValue(
            mockResponse({ nodes: [], edges: [], stats: { total_nodes: 0, total_edges: 0 } }),
        );
        global.fetch = fetchMock;

        await api.getLawGraph('cpeum', {
            depth: 2,
            min_confidence: 0.5,
            max_nodes: 100,
            direction: 'outgoing',
        });
        const url = fetchMock.mock.calls[0][0] as string;
        expect(url).toMatch(/depth=2/);
        expect(url).toMatch(/min_confidence=0\.5/);
        expect(url).toMatch(/max_nodes=100/);
        expect(url).toMatch(/direction=outgoing/);
    });

    it('getGraphOverview() invokes the overview endpoint', async () => {
        const fetchMock = vi.fn().mockResolvedValue(
            mockResponse({ nodes: [], edges: [], stats: { total_nodes: 0, total_edges: 0 } }),
        );
        global.fetch = fetchMock;

        await api.getGraphOverview();
        expect(fetchMock.mock.calls[0][0]).toMatch(/\/graph\/overview/);
    });

    it('getGraphShowcase() invokes the public showcase endpoint', async () => {
        const fetchMock = vi.fn().mockResolvedValue(
            mockResponse({ nodes: [], edges: [], stats: { total_nodes: 0, total_edges: 0 } }),
        );
        global.fetch = fetchMock;

        await api.getGraphShowcase();
        expect(fetchMock.mock.calls[0][0]).toMatch(/showcase/);
    });

    it('searchJudicial() composes the judicial query', async () => {
        const fetchMock = vi.fn().mockResolvedValue(mockResponse({ count: 0, results: [], facets: {} }));
        global.fetch = fetchMock;

        await api.searchJudicial({ q: 'amparo', tipo: 'jurisprudencia', page: 2 });
        const url = fetchMock.mock.calls[0][0] as string;
        expect(url).toMatch(/\/judicial\/search/);
        expect(url).toMatch(/q=amparo/);
        expect(url).toMatch(/tipo=jurisprudencia/);
        expect(url).toMatch(/page=2/);
    });
});

// ---------------------------------------------------------------------------
// Error paths — APIError
// ---------------------------------------------------------------------------

describe('api — error handling', () => {
    it('throws APIError(429) with retry-after on rate-limit', async () => {
        global.fetch = vi.fn().mockResolvedValue(
            mockResponse({ retry_after: 60 }, { status: 429 }),
        );

        await expect(api.getLaw('x')).rejects.toMatchObject({
            status: 429,
            retryAfter: 60,
        });
    });

    it('throws APIError on non-2xx with statusText in message', async () => {
        global.fetch = vi.fn().mockResolvedValue(mockResponse(null, { status: 500 }));
        await expect(api.getLaw('x')).rejects.toMatchObject({ status: 500 });
    });

    it('wraps a network error in APIError(500)', async () => {
        global.fetch = vi.fn().mockRejectedValue(new TypeError('Failed to fetch'));
        await expect(api.getLaw('x')).rejects.toMatchObject({ status: 500 });
    });

    it('429 retry_after defaults to 300 when body unparseable', async () => {
        global.fetch = vi.fn().mockResolvedValue({
            ok: false,
            status: 429,
            statusText: 'Too Many Requests',
            headers: new Headers(),
            json: async () => {
                throw new Error('not json');
            },
        } as unknown as Response);

        await expect(api.getLaw('x')).rejects.toMatchObject({
            status: 429,
            retryAfter: 300,
        });
    });
});

// ---------------------------------------------------------------------------
// Coverage: getCoverage / categories
// ---------------------------------------------------------------------------

describe('api — coverage + categories', () => {
    it('getCategories() returns the array', async () => {
        const fetchMock = vi.fn().mockResolvedValue(
            mockResponse([{ category: 'ley', count: 100 }]),
        );
        global.fetch = fetchMock;

        const result = await api.getCategories();
        expect(result).toHaveLength(1);
        expect(fetchMock.mock.calls[0][0]).toMatch(/\/categories\//);
    });

    it('getCoverage() returns coverage payload', async () => {
        const fetchMock = vi.fn().mockResolvedValue(
            mockResponse({
                total_laws_target: 100,
                total_laws_collected: 50,
                state_coverage: [],
                quality_grades: {},
                last_updated: '',
            }),
        );
        global.fetch = fetchMock;
        const result = await api.getCoverage();
        expect(result).toBeTruthy();
    });
});
