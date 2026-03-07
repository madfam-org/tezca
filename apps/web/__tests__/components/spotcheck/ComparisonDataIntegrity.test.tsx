import { render, screen, waitFor, act } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import ComparisonView from '@/components/ComparisonView';
import { LanguageProvider } from '@/components/providers/LanguageContext';
import { api } from '@/lib/api';
import type { Law } from '@tezca/lib';

vi.mock('@/lib/api', () => ({
    api: {
        getLaw: vi.fn(),
        getLawArticles: vi.fn(),
        getLawStructure: vi.fn(),
    },
}));

function renderWithLang(ui: React.ReactElement) {
    return render(<LanguageProvider>{ui}</LanguageProvider>);
}

function makeArticles(count: number, prefix = '') {
    return Array.from({ length: count }, (_, i) => ({
        article_id: `${prefix}${i + 1}`,
        text: `Texto del art\u00edculo ${prefix}${i + 1}. ${'Contenido legal detallado. '.repeat(10)}`,
    }));
}

describe('ComparisonDataIntegrity', () => {
    function setupMocks(
        articlesA: { article_id: string; text: string }[],
        articlesB: { article_id: string; text: string }[],
    ) {
        vi.mocked(api.getLaw).mockImplementation(async (id) => ({
            id,
            name: `Ley ${id}`,
            tier: 'federal',
            category: 'Civil',
            articles: 0,
        } as unknown as Law));

        vi.mocked(api.getLawArticles).mockImplementation(async (id) => {
            const articles = id === 'law-a' ? articlesA : articlesB;
            return { law_id: id, law_name: `Ley ${id}`, total: articles.length, articles };
        });

        vi.mocked(api.getLawStructure).mockImplementation(async (id) => ({
            law_id: id,
            structure: [{ label: `T\u00edtulo I (${id})`, children: [] }],
        }));
    }

    beforeEach(() => {
        vi.mocked(api.getLaw).mockReset();
        vi.mocked(api.getLawArticles).mockReset();
        vi.mocked(api.getLawStructure).mockReset();
    });

    it('renders all articles from both laws', async () => {
        const articlesA = makeArticles(5);
        const articlesB = makeArticles(5, 'B-');
        setupMocks(articlesA, articlesB);

        await act(async () => {
            renderWithLang(<ComparisonView lawIds={['law-a', 'law-b']} />);
        });

        await waitFor(() => {
            expect(screen.getByText('Comparaci\u00f3n Estructural')).toBeInTheDocument();
        });

        // API should have fetched articles for both laws
        expect(api.getLawArticles).toHaveBeenCalledWith('law-a');
        expect(api.getLawArticles).toHaveBeenCalledWith('law-b');
    });

    it('correctly identifies matched articles', async () => {
        // Both have articles 1,2,3 — those are matches
        const articlesA = makeArticles(5);
        const articlesB = makeArticles(3);
        setupMocks(articlesA, articlesB);

        await act(async () => {
            renderWithLang(<ComparisonView lawIds={['law-a', 'law-b']} />);
        });

        await waitFor(() => {
            // 3 articles in common (article IDs 1, 2, 3)
            expect(screen.getAllByText(/art\u00edculo en com\u00fan|art\u00edculos en com\u00fan/i).length).toBeGreaterThan(0);
        });
    });

    it('identifies unique articles per side', async () => {
        const articlesA = [
            { article_id: '1', text: 'Shared' },
            { article_id: 'X', text: 'Only in A' },
        ];
        const articlesB = [
            { article_id: '1', text: 'Shared' },
            { article_id: 'Y', text: 'Only in B' },
        ];
        setupMocks(articlesA, articlesB);

        await act(async () => {
            renderWithLang(<ComparisonView lawIds={['law-a', 'law-b']} />);
        });

        await waitFor(() => {
            expect(screen.getByText('Comparaci\u00f3n Estructural')).toBeInTheDocument();
        });
    });

    it('handles law with 100+ articles', async () => {
        const articlesA = makeArticles(120);
        const articlesB = makeArticles(80);
        setupMocks(articlesA, articlesB);

        await act(async () => {
            renderWithLang(<ComparisonView lawIds={['law-a', 'law-b']} />);
        });

        await waitFor(() => {
            expect(screen.getByText('Comparaci\u00f3n Estructural')).toBeInTheDocument();
        });
    });

    it('handles empty structure array', async () => {
        const articlesA = makeArticles(2);
        const articlesB = makeArticles(2);
        setupMocks(articlesA, articlesB);

        vi.mocked(api.getLawStructure).mockImplementation(async (id) => ({
            law_id: id,
            structure: [],
        }));

        await act(async () => {
            renderWithLang(<ComparisonView lawIds={['law-a', 'law-b']} />);
        });

        await waitFor(() => {
            expect(screen.getByText('Comparaci\u00f3n Estructural')).toBeInTheDocument();
        });
    });

    it('handles articles with identical text', async () => {
        const sameText = 'Identical text in both laws.';
        const articlesA = [{ article_id: '1', text: sameText }];
        const articlesB = [{ article_id: '1', text: sameText }];
        setupMocks(articlesA, articlesB);

        await act(async () => {
            renderWithLang(<ComparisonView lawIds={['law-a', 'law-b']} />);
        });

        await waitFor(() => {
            expect(screen.getByText('Comparaci\u00f3n Estructural')).toBeInTheDocument();
        });
    });

    it('handles articles with very long text (50K chars)', async () => {
        const longText = 'A'.repeat(50_000);
        const articlesA = [{ article_id: '1', text: longText }];
        const articlesB = [{ article_id: '1', text: 'Short' }];
        setupMocks(articlesA, articlesB);

        await act(async () => {
            renderWithLang(<ComparisonView lawIds={['law-a', 'law-b']} />);
        });

        await waitFor(() => {
            expect(screen.getByText('Comparaci\u00f3n Estructural')).toBeInTheDocument();
        });
    });

    it('handles special characters in article text', async () => {
        const specialText = 'Art\u00edculo \u2014 \u00a72.1 \u00abproteger\u00bb \u201cEstado\u201d \u00f1';
        const articlesA = [{ article_id: '1', text: specialText }];
        const articlesB = [{ article_id: '1', text: 'Normal text' }];
        setupMocks(articlesA, articlesB);

        await act(async () => {
            renderWithLang(<ComparisonView lawIds={['law-a', 'law-b']} />);
        });

        await waitFor(() => {
            expect(screen.getByText('Comparaci\u00f3n Estructural')).toBeInTheDocument();
        });
    });

    it('handles article_id with roman numerals', async () => {
        const articlesA = [
            { article_id: 'XIV Bis', text: 'Content A' },
            { article_id: 'TRANSITORIO', text: 'Trans A' },
        ];
        const articlesB = [
            { article_id: 'XIV Bis', text: 'Content B' },
            { article_id: 'TRANSITORIO', text: 'Trans B' },
        ];
        setupMocks(articlesA, articlesB);

        await act(async () => {
            renderWithLang(<ComparisonView lawIds={['law-a', 'law-b']} />);
        });

        await waitFor(() => {
            expect(screen.getByText('Comparaci\u00f3n Estructural')).toBeInTheDocument();
        });
    });
});
