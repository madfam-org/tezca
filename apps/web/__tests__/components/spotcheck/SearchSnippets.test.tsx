import { describe, it, expect } from 'vitest';
import DOMPurify from 'dompurify';

/**
 * These tests validate the exact sanitization logic used in the search page
 * (apps/web/app/busqueda/page.tsx) to render search result snippets.
 *
 * The search page uses:
 *   DOMPurify.sanitize(result.snippet, { ALLOWED_TAGS: ['em', 'mark', 'b', 'strong'] })
 */

const ALLOWED_TAGS = ['em', 'mark', 'b', 'strong'];

function sanitizeSnippet(html: string): string {
    return DOMPurify.sanitize(html, { ALLOWED_TAGS });
}

describe('Search snippet sanitization', () => {
    it('preserves em tags used for search highlights', () => {
        const input = '<em>amparo</em> es un recurso constitucional';
        const result = sanitizeSnippet(input);

        expect(result).toContain('<em>amparo</em>');
        expect(result).toContain('es un recurso constitucional');
    });

    it('preserves special characters and accented text', () => {
        const input = 'Art\u00edculo d\u00e9cimo \u2014 seg\u00fan \u00A72.1';
        const result = sanitizeSnippet(input);

        expect(result).toContain('Art\u00edculo');
        expect(result).toContain('d\u00e9cimo');
        expect(result).toContain('\u2014');
        expect(result).toContain('\u00A7');
    });

    it('strips script tags while keeping surrounding text', () => {
        const input = '<script>alert(1)</script>amparo directo';
        const result = sanitizeSnippet(input);

        expect(result).not.toContain('<script>');
        expect(result).not.toContain('alert');
        expect(result).toContain('amparo directo');
    });
});
