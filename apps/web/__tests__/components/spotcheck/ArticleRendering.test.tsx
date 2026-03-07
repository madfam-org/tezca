import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { ArticleViewer } from '@/components/laws/ArticleViewer';
import { LanguageProvider } from '@/components/providers/LanguageContext';

// Mock scrollIntoView (not available in jsdom)
Element.prototype.scrollIntoView = vi.fn();

// Mock react-intersection-observer
vi.mock('react-intersection-observer', () => ({
    useInView: () => ({ ref: vi.fn(), inView: false }),
}));

// Mock LinkifiedArticle to capture rendered text without network calls
vi.mock('@/components/laws/LinkifiedArticle', () => ({
    LinkifiedArticle: ({ text }: { text: string }) => (
        <p data-testid="linkified-text">{text}</p>
    ),
}));

// Mock clipboard API
Object.assign(navigator, {
    clipboard: { writeText: vi.fn().mockResolvedValue(undefined) },
});

function renderWithLang(ui: React.ReactElement) {
    return render(<LanguageProvider>{ui}</LanguageProvider>);
}

describe('ArticleRendering spot-checks', () => {
    it('renders special characters correctly', () => {
        const articles = [
            {
                article_id: '10',
                text: 'Articulo decimo \u2014 segun \u00A72.1',
            },
        ];

        renderWithLang(
            <ArticleViewer
                articles={articles}
                activeArticle={null}
                lawId="test-law"
            />
        );

        const rendered = screen.getByTestId('linkified-text');
        expect(rendered).toHaveTextContent('\u2014');
        expect(rendered).toHaveTextContent('\u00A72.1');
    });

    it('renders very long article without truncation', () => {
        const longText = 'A'.repeat(100_000);
        const articles = [{ article_id: '1', text: longText }];

        renderWithLang(
            <ArticleViewer
                articles={articles}
                activeArticle={null}
                lawId="test-law"
            />
        );

        const rendered = screen.getByTestId('linkified-text');
        // Verify at least a significant portion of the text is present
        expect(rendered.textContent?.length).toBeGreaterThanOrEqual(100_000);
    });

    it('renders empty article list gracefully', () => {
        renderWithLang(
            <ArticleViewer
                articles={[]}
                activeArticle={null}
                lawId="test-law"
            />
        );

        // Should show the Spanish empty state, not crash
        expect(
            screen.getByText(/No hay art\u00edculos disponibles/)
        ).toBeInTheDocument();
        // No article elements should be present
        expect(screen.queryAllByTestId('linkified-text')).toHaveLength(0);
    });

    it('displays article prefix for numeric article IDs', () => {
        const articles = [
            { article_id: '1', text: 'La presente ley es de observancia general.' },
        ];

        renderWithLang(
            <ArticleViewer
                articles={articles}
                activeArticle={null}
                lawId="test-law"
            />
        );

        // ArticleViewer prefixes numeric IDs with "Articulo "
        expect(screen.getByText('Art\u00edculo 1')).toBeInTheDocument();
        expect(
            screen.getByTestId('linkified-text')
        ).toHaveTextContent('La presente ley es de observancia general.');
    });

    it('escapes HTML in article text (rendered as text, not executed)', () => {
        const xssPayload = "<script>alert('xss')</script>Contenido seguro";
        const articles = [{ article_id: '1', text: xssPayload }];

        renderWithLang(
            <ArticleViewer
                articles={articles}
                activeArticle={null}
                lawId="test-law"
            />
        );

        const rendered = screen.getByTestId('linkified-text');

        // The text content should include the literal script tag string,
        // because our mock renders it as text content inside a <p>, not as HTML.
        expect(rendered).toHaveTextContent('Contenido seguro');
        expect(rendered).toHaveTextContent("<script>alert('xss')</script>");

        // No actual <script> element should be in the DOM
        expect(document.querySelector('script[src]')).toBeNull();
        expect(
            document.querySelectorAll('script').length
        ).toBeLessThanOrEqual(0);
    });
});
