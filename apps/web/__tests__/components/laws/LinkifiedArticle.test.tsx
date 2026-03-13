import { render, screen, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { LinkifiedArticle } from '@/components/laws/LinkifiedArticle';
import { LanguageProvider } from '@/components/providers/LanguageContext';

function renderWithLang(ui: React.ReactElement) {
    return render(<LanguageProvider>{ui}</LanguageProvider>);
}

// Mock global fetch
const mockFetch = vi.fn();
global.fetch = mockFetch;

describe('LinkifiedArticle', () => {
    beforeEach(() => {
        mockFetch.mockReset();
    });

    it('renders plain text while loading', () => {
        mockFetch.mockReturnValue(new Promise(() => {})); // never resolves

        renderWithLang(
            <LinkifiedArticle
                lawId="amparo"
                articleId="107"
                text="Los tribunales de la Federacion resolveran toda controversia."
            />
        );

        expect(screen.getByText('Los tribunales de la Federacion resolveran toda controversia.')).toBeInTheDocument();
    });

    it('renders plain text when no references returned', async () => {
        mockFetch.mockResolvedValue({
            ok: true,
            json: () => Promise.resolve({ outgoing: [] }),
        });

        renderWithLang(
            <LinkifiedArticle
                lawId="amparo"
                articleId="1"
                text="Articulo simple sin referencias."
            />
        );

        await waitFor(() => {
            expect(screen.getByText('Articulo simple sin referencias.')).toBeInTheDocument();
        });
    });

    it('renders links for cross-references with target URLs', async () => {
        mockFetch.mockResolvedValue({
            ok: true,
            json: () => Promise.resolve({
                outgoing: [
                    {
                        text: 'Ley de Amparo',
                        targetLawSlug: 'amparo',
                        targetArticle: '5',
                        confidence: 0.95,
                        startPos: 18,
                        endPos: 32,
                        targetUrl: '/leyes/amparo#article-5',
                    },
                ],
            }),
        });

        renderWithLang(
            <LinkifiedArticle
                lawId="constitucion"
                articleId="103"
                text="De acuerdo con la Ley de Amparo vigente en la materia."
                crossRefsDisabled={false}
            />
        );

        await waitFor(() => {
            const link = screen.getByRole('link', { name: 'Ley de Amparo' });
            expect(link).toHaveAttribute('href', '/leyes/amparo#article-5');
        });
    });

    it('renders emphasized text for references without target URL', async () => {
        mockFetch.mockResolvedValue({
            ok: true,
            json: () => Promise.resolve({
                outgoing: [
                    {
                        text: 'articulo 27',
                        targetLawSlug: null,
                        targetArticle: '27',
                        confidence: 0.7,
                        startPos: 5,
                        endPos: 16,
                        targetUrl: null,
                    },
                ],
            }),
        });

        renderWithLang(
            <LinkifiedArticle
                lawId="test-law"
                articleId="1"
                text="En el articulo 27 se establece lo anterior."
                crossRefsDisabled={false}
            />
        );

        await waitFor(() => {
            const refSpan = screen.getByTitle(/Referencia: articulo 27|Reference: articulo 27/);
            expect(refSpan).toBeInTheDocument();
            expect(refSpan.className).toContain('font-semibold');
        });
    });

    it('handles fetch errors gracefully', async () => {
        mockFetch.mockResolvedValue({
            ok: false,
            status: 500,
            json: () => Promise.resolve({ outgoing: [] }),
        });

        renderWithLang(
            <LinkifiedArticle
                lawId="test-law"
                articleId="1"
                text="Texto de prueba."
            />
        );

        await waitFor(() => {
            expect(screen.getByText('Texto de prueba.')).toBeInTheDocument();
        });
    });

    it('shows reference count when references are present', async () => {
        mockFetch.mockResolvedValue({
            ok: true,
            json: () => Promise.resolve({
                outgoing: [
                    { text: 'ref1', startPos: 0, endPos: 4, confidence: 0.9, targetUrl: '/a' },
                    { text: 'ref2', startPos: 10, endPos: 14, confidence: 0.9, targetUrl: '/b' },
                ],
            }),
        });

        const { container } = renderWithLang(
            <LinkifiedArticle
                lawId="test"
                articleId="1"
                text="ref1 text ref2 more text"
                crossRefsDisabled={false}
            />
        );

        await waitFor(() => {
            // The count "2" is inside a <span class="font-medium"> and the rest is text nodes
            const countSpan = container.querySelector('.font-medium');
            expect(countSpan).not.toBeNull();
            expect(countSpan?.textContent).toBe('2');
        });
    });

    describe('preloadedRefs', () => {
        it('renders links from preloadedRefs without making a fetch call', () => {
            const preloaded = [
                {
                    text: 'Ley Federal',
                    targetLawSlug: 'ley-federal',
                    targetArticle: '10',
                    fraction: null,
                    confidence: 0.9,
                    startPos: 14,
                    endPos: 25,
                    targetUrl: '/leyes/ley-federal#article-10',
                },
            ];

            renderWithLang(
                <LinkifiedArticle
                    lawId="test"
                    articleId="1"
                    text="De acuerdo a Ley Federal se establece."
                    preloadedRefs={preloaded}
                    crossRefsDisabled={false}
                />
            );

            // Should NOT call fetch since preloaded data is provided
            expect(mockFetch).not.toHaveBeenCalled();

            const link = screen.getByRole('link', { name: 'Ley Federal' });
            expect(link).toHaveAttribute('href', '/leyes/ley-federal#article-10');
        });

        it('renders plain text with empty preloadedRefs (no fetch)', () => {
            renderWithLang(
                <LinkifiedArticle
                    lawId="test"
                    articleId="1"
                    text="Sin referencias cruzadas."
                    preloadedRefs={[]}
                    crossRefsDisabled={false}
                />
            );

            expect(mockFetch).not.toHaveBeenCalled();
            expect(screen.getByText('Sin referencias cruzadas.')).toBeInTheDocument();
        });

        it('falls back to per-article fetch when preloadedRefs is not provided and crossRefsDisabled is false', async () => {
            mockFetch.mockResolvedValue({
                ok: true,
                json: () => Promise.resolve({
                    outgoing: [
                        {
                            text: 'articulo 5',
                            targetLawSlug: null,
                            targetArticle: '5',
                            confidence: 0.8,
                            startPos: 0,
                            endPos: 10,
                            targetUrl: null,
                        },
                    ],
                }),
            });

            renderWithLang(
                <LinkifiedArticle
                    lawId="test"
                    articleId="1"
                    text="articulo 5 de esta ley."
                    crossRefsDisabled={false}
                />
            );

            // Should call fetch since no preloadedRefs
            await waitFor(() => {
                expect(mockFetch).toHaveBeenCalledTimes(1);
            });
        });
    });
});
