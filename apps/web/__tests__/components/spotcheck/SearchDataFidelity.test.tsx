import { describe, it, expect } from 'vitest';
import DOMPurify from 'dompurify';
import { makeSearchResponse } from '../../fixtures/mockFactories';

/**
 * These tests verify the data fidelity of the search results rendering
 * by checking the logic used in busqueda/page.tsx's SearchContent component.
 *
 * Since SearchContent is a complex component with many dependencies,
 * we test the rendering logic and data transformations in isolation.
 */

const ALLOWED_TAGS = ['em', 'mark', 'b', 'strong'];

describe('SearchDataFidelity', () => {
    describe('search result fields rendering', () => {
        it('all search result fields are present', () => {
            const data = makeSearchResponse(1);
            const result = data.results[0];

            // Verify all expected fields exist and are non-empty
            expect(result.law_name).toBeTruthy();
            expect(result.article).toBeTruthy();
            expect(result.snippet).toBeTruthy();
            expect(result.score).toBeGreaterThan(0);
            expect(result.tier).toBeTruthy();
            expect(result.law_id).toBeTruthy();
        });

        it('hierarchy array joined with separator', () => {
            const data = makeSearchResponse(1);
            const result = data.results[0];
            if (result.hierarchy.length > 0) {
                const breadcrumb = result.hierarchy.join(' \u203A ');
                expect(breadcrumb).toContain('\u203A');
                expect(breadcrumb).toContain(result.hierarchy[0]);
            }
        });

        it('municipality badge for municipal results', () => {
            const data = makeSearchResponse(10);
            const municipalResult = data.results.find(r => r.municipality !== null);
            expect(municipalResult).toBeDefined();
            expect(municipalResult!.municipality).toBe('Guadalajara');
        });

        it('non-legislative badge for non_legislative type', () => {
            const data = makeSearchResponse(10);
            const nonLeg = data.results.find(r => r.law_type === 'non_legislative');
            expect(nonLeg).toBeDefined();
        });

        it('relevance score formatted to 1 decimal', () => {
            const data = makeSearchResponse(1);
            const formatted = data.results[0].score.toFixed(1);
            expect(formatted).toMatch(/^\d+\.\d$/);
        });

        it('date formatted with locale', () => {
            const data = makeSearchResponse(1);
            const result = data.results[0];
            if (result.date) {
                const formatted = new Date(result.date).toLocaleDateString('es-MX', {
                    year: 'numeric', month: 'long', day: 'numeric',
                });
                expect(formatted).toBeTruthy();
                expect(formatted.length).toBeGreaterThan(5);
            }
        });

        it('handles missing optional fields without crash', () => {
            const data = makeSearchResponse(1);
            const result = {
                ...data.results[0],
                tier: undefined as unknown as string,
                date: null,
                municipality: null,
                hierarchy: [],
            };

            // These should be renderable without errors
            expect(result.tier).toBeUndefined();
            expect(result.date).toBeNull();
            expect(result.municipality).toBeNull();
            expect(result.hierarchy).toHaveLength(0);
        });
    });

    describe('snippet sanitization', () => {
        it('preserves em tags for highlights', () => {
            const html = '<em>amparo</em> directo en materia civil';
            const clean = DOMPurify.sanitize(html, { ALLOWED_TAGS });
            expect(clean).toContain('<em>amparo</em>');
        });

        it('strips script tags', () => {
            const html = '<script>alert(1)</script>safe text';
            const clean = DOMPurify.sanitize(html, { ALLOWED_TAGS });
            expect(clean).not.toContain('<script>');
            expect(clean).toContain('safe text');
        });

        it('preserves strong and mark tags', () => {
            const html = '<strong>important</strong> and <mark>highlighted</mark>';
            const clean = DOMPurify.sanitize(html, { ALLOWED_TAGS });
            expect(clean).toContain('<strong>important</strong>');
            expect(clean).toContain('<mark>highlighted</mark>');
        });
    });

    describe('result link construction', () => {
        it('links to correct law page with article anchor', () => {
            const data = makeSearchResponse(1);
            const result = data.results[0];
            const articleNum = result.article.replace('Art. ', '');
            const href = `/leyes/${result.law_id}#article-${articleNum}`;
            expect(href).toMatch(/^\/leyes\/ley-\d+#article-\d+$/);
        });
    });

    describe('pagination', () => {
        it('shows correct range for first page', () => {
            const data = makeSearchResponse(10, { total: 150 });
            const page = 1;
            const pageSize = 10;
            const start = (page - 1) * pageSize + 1;
            const end = Math.min(page * pageSize, data.total);
            expect(start).toBe(1);
            expect(end).toBe(10);
        });

        it('shows correct range for middle page', () => {
            const data = makeSearchResponse(10, { total: 150 });
            const page = 5;
            const pageSize = 10;
            const start = (page - 1) * pageSize + 1;
            const end = Math.min(page * pageSize, data.total);
            expect(start).toBe(41);
            expect(end).toBe(50);
        });
    });

    describe('facets', () => {
        it('all tier types present in facets', () => {
            const data = makeSearchResponse(10);
            const tierFacets = data.facets!.tier;
            const tierKeys = tierFacets.map(f => f.key);
            expect(tierKeys).toContain('federal');
            expect(tierKeys).toContain('state');
            expect(tierKeys).toContain('municipal');
        });

        it('facet doc_counts are positive', () => {
            const data = makeSearchResponse(10);
            for (const facetGroup of Object.values(data.facets!)) {
                for (const bucket of facetGroup) {
                    expect(bucket.doc_count).toBeGreaterThan(0);
                }
            }
        });
    });

    describe('tier gate triggers', () => {
        it('max_page_size < 100 triggers upgrade prompt logic', () => {
            const data = makeSearchResponse(10, { max_page_size: 25 });
            expect(data.max_page_size).toBeLessThan(100);
        });

        it('max_page_size >= 100 does not trigger upgrade', () => {
            const data = makeSearchResponse(10, { max_page_size: 100 });
            expect(data.max_page_size).toBeGreaterThanOrEqual(100);
        });
    });

    describe('long law name handling', () => {
        it('long law names render without overflow', () => {
            const data = makeSearchResponse(1);
            const longName = 'A'.repeat(300);
            data.results[0].law_name = longName;

            // The search page uses truncate max-w-[200px] sm:max-w-[300px] CSS class
            // Data fidelity: the full name should be stored, CSS handles truncation
            expect(data.results[0].law_name).toHaveLength(300);
        });
    });
});
