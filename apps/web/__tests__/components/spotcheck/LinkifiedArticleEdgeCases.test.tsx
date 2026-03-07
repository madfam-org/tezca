import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { LinkifiedArticle } from '@/components/laws/LinkifiedArticle';
import { LanguageProvider } from '@/components/providers/LanguageContext';

// Prevent actual fetch calls (component uses raw fetch for cross-refs)
global.fetch = vi.fn().mockResolvedValue({
    ok: true,
    json: () => Promise.resolve({ outgoing: [] }),
});

function renderWithLang(ui: React.ReactElement) {
    return render(<LanguageProvider>{ui}</LanguageProvider>);
}

/**
 * These tests verify the prefix-stripping regex at LinkifiedArticle.tsx:64
 * and data fidelity of article text rendering.
 *
 * The regex: /^(?:Art[ií]culo|ARTÍCULO)\s+\d+[\w]*\.?\s* /i
 * Strips leading "Artículo N." prefix since the heading already shows it.
 *
 * All rendered with crossRefsDisabled=true (default) to avoid fetch.
 */

/** Unit test the prefix regex directly (isolated from jsdom rendering) */
const PREFIX_REGEX = /^(?:Art[i\u00ed]culo|ART\u00cdCULO)\s+\d+[\w]*\.?\s*/i;

describe('LinkifiedArticle prefix stripping edge cases', () => {
    describe('prefix regex unit tests', () => {
        it('strips "Art\u00edculo N." prefix', () => {
            const input = 'Art\u00edculo 10. Los ciudadanos tienen derecho.';
            const result = input.replace(PREFIX_REGEX, '').trim();
            expect(result).toBe('Los ciudadanos tienen derecho.');
        });

        it('strips "ART\u00cdCULO N." uppercase prefix', () => {
            const input = 'ART\u00cdCULO 5. El Estado garantiza la educaci\u00f3n.';
            const result = input.replace(PREFIX_REGEX, '').trim();
            expect(result).toBe('El Estado garantiza la educaci\u00f3n.');
        });

        it('strips "Art\u00edculo 14Bis." prefix', () => {
            const input = 'Art\u00edculo 14Bis. Disposici\u00f3n transitoria.';
            const result = input.replace(PREFIX_REGEX, '').trim();
            expect(result).toBe('Disposici\u00f3n transitoria.');
        });

        it('strips "Art\u00edculo 1o." ordinal prefix', () => {
            const input = 'Art\u00edculo 1o. Esta ley es de orden p\u00fablico.';
            const result = input.replace(PREFIX_REGEX, '').trim();
            expect(result).toBe('Esta ley es de orden p\u00fablico.');
        });

        it('does NOT strip roman numeral prefix (no \\d+ match)', () => {
            const input = 'Art\u00edculo XIV. Contenido con n\u00famero romano.';
            const result = input.replace(PREFIX_REGEX, '').trim();
            expect(result).toBe(input);
        });

        it('does NOT strip mid-text "Art\u00edculo" references', () => {
            const input = 'De conformidad con el Art\u00edculo 123 de esta ley.';
            const result = input.replace(PREFIX_REGEX, '').trim();
            expect(result).toBe(input);
        });

        it('does NOT strip "TRANSITORIO" prefix', () => {
            const input = 'TRANSITORIO PRIMERO. Las disposiciones entrar\u00e1n en vigor.';
            const result = input.replace(PREFIX_REGEX, '').trim();
            expect(result).toBe(input);
        });
    });

    describe('component rendering data fidelity', () => {
        it('preserves text when no prefix match', () => {
            const text = 'Los derechos fundamentales son inalienables.';
            renderWithLang(
                <LinkifiedArticle lawId="test" articleId="1" text={text} crossRefsDisabled />
            );
            expect(screen.getByText(text)).toBeInTheDocument();
        });

        it('renders article text with prefix (data not lost)', () => {
            renderWithLang(
                <LinkifiedArticle
                    lawId="test" articleId="10"
                    text={'Art\u00edculo 10. Los ciudadanos tienen derecho.'}
                    crossRefsDisabled
                />
            );
            // The important content must be present whether prefix is stripped or not
            const el = screen.getByText(/Los ciudadanos tienen derecho/);
            expect(el).toBeInTheDocument();
        });

        it('handles "Art\u00edculo XIV." roman numeral (preserved)', () => {
            const text = 'Art\u00edculo XIV. Contenido con n\u00famero romano.';
            renderWithLang(
                <LinkifiedArticle lawId="test" articleId="XIV" text={text} crossRefsDisabled />
            );
            expect(screen.getByText(/Contenido con n\u00famero romano/)).toBeInTheDocument();
        });

        it('handles multiline article text', () => {
            const text = 'I. Los tribunales resolver\u00e1n:\n\na) Controversias;\n\nb) Conflictos.';
            renderWithLang(
                <LinkifiedArticle lawId="test" articleId="107" text={text} crossRefsDisabled />
            );
            const el = screen.getByText(/Los tribunales/);
            expect(el).toBeInTheDocument();
            expect(el.textContent).toContain('Controversias');
            expect(el.textContent).toContain('Conflictos');
        });

        it('does not strip mid-text "Art\u00edculo" references', () => {
            const text = 'De conformidad con el Art\u00edculo 123 de esta ley.';
            renderWithLang(
                <LinkifiedArticle lawId="test" articleId="5" text={text} crossRefsDisabled />
            );
            expect(screen.getByText(/Art\u00edculo 123/)).toBeInTheDocument();
        });

        it('handles text starting with "TRANSITORIO"', () => {
            const text = 'TRANSITORIO PRIMERO. Las disposiciones entrar\u00e1n en vigor.';
            renderWithLang(
                <LinkifiedArticle lawId="test" articleId="Primero Transitorio" text={text} crossRefsDisabled />
            );
            expect(screen.getByText(text)).toBeInTheDocument();
        });

        it('renders reference count footer accurately (no refs when disabled)', () => {
            renderWithLang(
                <LinkifiedArticle lawId="test" articleId="1" text="Some text." crossRefsDisabled />
            );
            expect(screen.queryByText(/referencia/i)).not.toBeInTheDocument();
        });
    });
});
