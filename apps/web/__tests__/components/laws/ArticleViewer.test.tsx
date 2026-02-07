import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { ArticleViewer } from '@/components/laws/ArticleViewer';
import { LanguageProvider } from '@/components/providers/LanguageContext';

function renderWithLang(ui: React.ReactElement) {
    return render(<LanguageProvider>{ui}</LanguageProvider>);
}

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

// Mock clipboard API
const mockWriteText = vi.fn().mockResolvedValue(undefined);
Object.assign(navigator, {
    clipboard: { writeText: mockWriteText },
});

describe('ArticleViewer', () => {
    const mockArticles = [
        { article_id: '1', text: 'Primer artículo de la ley.' },
        { article_id: '2', text: 'Segundo artículo de la ley.' },
        { article_id: 'texto_completo', text: 'Texto completo de la ley.' },
    ];

    beforeEach(() => {
        vi.clearAllMocks();
    });

    it('renders all articles', () => {
        renderWithLang(
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
        renderWithLang(
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
        renderWithLang(
            <ArticleViewer
                articles={[]}
                activeArticle={null}
                lawId="test-law"
            />
        );

        expect(screen.getByText(/No hay artículos disponibles/)).toBeInTheDocument();
    });

    it('highlights active article differently from inactive', () => {
        renderWithLang(
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
        renderWithLang(
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

    it('renders citation, bibtex, and link copy buttons on each article', () => {
        renderWithLang(
            <ArticleViewer
                articles={[mockArticles[0]]}
                activeArticle={null}
                lawId="test-law"
                lawName="Ley de Prueba"
            />
        );

        expect(screen.getByLabelText('Copiar cita legal')).toBeInTheDocument();
        expect(screen.getByLabelText('Copiar cita BibTeX')).toBeInTheDocument();
        expect(screen.getByLabelText('Copiar enlace directo al artículo')).toBeInTheDocument();
    });

    it('copies legal citation to clipboard including law name', async () => {
        renderWithLang(
            <ArticleViewer
                articles={[mockArticles[0]]}
                activeArticle={null}
                lawId="test-law"
                lawName="Constitución Política"
                publicationDate="2024-02-05"
            />
        );

        fireEvent.click(screen.getByLabelText('Copiar cita legal'));

        await waitFor(() => {
            expect(mockWriteText).toHaveBeenCalledTimes(1);
            const clipboardText = mockWriteText.mock.calls[0][0];
            expect(clipboardText).toContain('Art. 1');
            expect(clipboardText).toContain('Constitución Política');
            expect(clipboardText).toContain('DOF');
        });
    });

    it('copies BibTeX citation to clipboard', async () => {
        renderWithLang(
            <ArticleViewer
                articles={[mockArticles[0]]}
                activeArticle={null}
                lawId="test-law"
                lawName="Ley de Prueba"
                publicationDate="2024-01-15"
                tier="federal"
            />
        );

        fireEvent.click(screen.getByLabelText('Copiar cita BibTeX'));

        await waitFor(() => {
            expect(mockWriteText).toHaveBeenCalledTimes(1);
            const bibtex = mockWriteText.mock.calls[0][0];
            expect(bibtex).toContain('@misc{');
            expect(bibtex).toContain('Ley de Prueba');
            expect(bibtex).toContain('2024');
            expect(bibtex).toContain('Federal');
        });
    });

    it('copies direct link to clipboard', async () => {
        renderWithLang(
            <ArticleViewer
                articles={[mockArticles[0]]}
                activeArticle={null}
                lawId="test-law"
            />
        );

        fireEvent.click(screen.getByLabelText('Copiar enlace directo al artículo'));

        await waitFor(() => {
            expect(mockWriteText).toHaveBeenCalledTimes(1);
            const url = mockWriteText.mock.calls[0][0];
            expect(url).toContain('#article-1');
        });
    });
});
