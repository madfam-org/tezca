import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { ArticleViewer } from '@/components/laws/ArticleViewer';

// Mock scrollIntoView (not available in jsdom)
Element.prototype.scrollIntoView = vi.fn();

// Mock react-intersection-observer
vi.mock('react-intersection-observer', () => ({
    useInView: () => ({ ref: vi.fn(), inView: false }),
}));

// Mock LinkifiedArticle to avoid fetch calls
vi.mock('@/components/laws/LinkifiedArticle', () => ({
    LinkifiedArticle: ({ text }: { text: string }) => (
        <p data-testid="linkified-text">{text}</p>
    ),
}));

describe('ArticleViewer', () => {
    const mockArticles = [
        { article_id: '1', text: 'Primer artículo de la ley.' },
        { article_id: '2', text: 'Segundo artículo de la ley.' },
        { article_id: 'texto_completo', text: 'Texto completo de la ley.' },
    ];

    it('renders all articles', () => {
        render(
            <ArticleViewer
                articles={mockArticles}
                activeArticle={null}
                lawId="test-law"
            />
        );

        expect(screen.getByText('Artículo 1')).toBeInTheDocument();
        expect(screen.getByText('Artículo 2')).toBeInTheDocument();
        expect(screen.getByText('Texto Completo')).toBeInTheDocument();
    });

    it('renders article text content', () => {
        render(
            <ArticleViewer
                articles={mockArticles}
                activeArticle={null}
                lawId="test-law"
            />
        );

        const texts = screen.getAllByTestId('linkified-text');
        expect(texts[0]).toHaveTextContent('Primer artículo de la ley.');
        expect(texts[1]).toHaveTextContent('Segundo artículo de la ley.');
    });

    it('shows empty state when no articles', () => {
        render(
            <ArticleViewer
                articles={[]}
                activeArticle={null}
                lawId="test-law"
            />
        );

        expect(screen.getByText(/No hay artículos disponibles/)).toBeInTheDocument();
    });

    it('highlights active article differently from inactive', () => {
        render(
            <ArticleViewer
                articles={mockArticles}
                activeArticle="1"
                lawId="test-law"
            />
        );

        const activeArticle = document.getElementById('article-1');
        const inactiveArticle = document.getElementById('article-2');
        expect(activeArticle).toBeInTheDocument();
        expect(inactiveArticle).toBeInTheDocument();
        // Active article should have different styling than inactive
        expect(activeArticle?.className).not.toBe(inactiveArticle?.className);
    });

    it('assigns correct IDs for anchor links', () => {
        render(
            <ArticleViewer
                articles={mockArticles}
                activeArticle={null}
                lawId="test-law"
            />
        );

        expect(document.getElementById('article-1')).toBeInTheDocument();
        expect(document.getElementById('article-2')).toBeInTheDocument();
        expect(document.getElementById('article-texto_completo')).toBeInTheDocument();
    });
});
