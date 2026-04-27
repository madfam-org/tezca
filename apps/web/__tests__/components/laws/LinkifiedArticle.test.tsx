import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { LinkifiedArticle } from '@/components/laws/LinkifiedArticle';
import { LanguageProvider } from '@/components/providers/LanguageContext';

function renderWithLang(ui: React.ReactElement) {
    return render(<LanguageProvider>{ui}</LanguageProvider>);
}

// LinkifiedArticle no longer fetches — refs come from useBatchCrossRefs at the
// caller level. Keep a fetch spy to assert that fact.
const mockFetch = vi.fn();
global.fetch = mockFetch;

describe('LinkifiedArticle', () => {
    beforeEach(() => {
        mockFetch.mockReset();
    });

    it('renders plain text when no preloadedRefs are provided', () => {
        renderWithLang(
            <LinkifiedArticle
                text="Los tribunales de la Federacion resolveran toda controversia."
            />
        );

        expect(screen.getByText('Los tribunales de la Federacion resolveran toda controversia.')).toBeInTheDocument();
        expect(mockFetch).not.toHaveBeenCalled();
    });

    it('renders plain text when preloadedRefs is empty', () => {
        renderWithLang(
            <LinkifiedArticle
                text="Articulo simple sin referencias."
                preloadedRefs={[]}
            />
        );

        expect(screen.getByText('Articulo simple sin referencias.')).toBeInTheDocument();
        expect(mockFetch).not.toHaveBeenCalled();
    });

    it('renders links for cross-references with target URLs', () => {
        renderWithLang(
            <LinkifiedArticle
                text="De acuerdo con la Ley de Amparo vigente en la materia."
                preloadedRefs={[
                    {
                        text: 'Ley de Amparo',
                        targetLawSlug: 'amparo',
                        targetArticle: '5',
                        confidence: 0.95,
                        startPos: 18,
                        endPos: 32,
                        targetUrl: '/leyes/amparo#article-5',
                    },
                ]}
            />
        );

        const link = screen.getByRole('link', { name: 'Ley de Amparo' });
        expect(link).toHaveAttribute('href', '/leyes/amparo#article-5');
    });

    it('renders emphasized text for references without target URL', () => {
        renderWithLang(
            <LinkifiedArticle
                text="En el articulo 27 se establece lo anterior."
                preloadedRefs={[
                    {
                        text: 'articulo 27',
                        targetLawSlug: null,
                        targetArticle: '27',
                        confidence: 0.7,
                        startPos: 5,
                        endPos: 16,
                        targetUrl: null,
                    },
                ]}
            />
        );

        const refSpan = screen.getByTitle(/Referencia: articulo 27|Reference: articulo 27/);
        expect(refSpan).toBeInTheDocument();
        expect(refSpan.className).toContain('font-semibold');
    });

    it('shows reference count when references are present', () => {
        const { container } = renderWithLang(
            <LinkifiedArticle
                text="ref1 text ref2 more text"
                preloadedRefs={[
                    { text: 'ref1', startPos: 0, endPos: 4, confidence: 0.9, targetUrl: '/a' },
                    { text: 'ref2', startPos: 10, endPos: 14, confidence: 0.9, targetUrl: '/b' },
                ]}
            />
        );

        const countSpan = container.querySelector('.font-medium');
        expect(countSpan).not.toBeNull();
        expect(countSpan?.textContent).toBe('2');
    });

    it('filters references below the confidence threshold', () => {
        renderWithLang(
            <LinkifiedArticle
                text="alpha bravo charlie delta echo"
                minConfidence={0.7}
                preloadedRefs={[
                    { text: 'alpha', startPos: 0, endPos: 5, confidence: 0.9, targetUrl: '/a' },
                    { text: 'bravo', startPos: 6, endPos: 11, confidence: 0.5, targetUrl: '/b' }, // filtered
                ]}
            />
        );

        // High-confidence ref renders as a link.
        expect(screen.getByRole('link', { name: 'alpha' })).toBeInTheDocument();
        // Low-confidence ref is skipped — no link rendered for "bravo".
        expect(screen.queryByRole('link', { name: 'bravo' })).toBeNull();
    });

    it('never calls fetch (refs are caller-supplied)', () => {
        renderWithLang(
            <LinkifiedArticle
                text="anything"
                preloadedRefs={[
                    { text: 'anything', startPos: 0, endPos: 8, confidence: 0.9, targetUrl: '/x' },
                ]}
            />
        );

        expect(mockFetch).not.toHaveBeenCalled();
    });
});
