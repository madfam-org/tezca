import { render, screen, waitFor, act } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import ComparisonView from '@/components/ComparisonView';
import { LanguageProvider } from '@/components/providers/LanguageContext';
import { api } from '@/lib/api';
import type { Law } from '@tezca/lib';

// Mock API
vi.mock('@/lib/api', () => ({
    api: {
        getLaw: vi.fn(),
        getLawArticles: vi.fn(),
        getLawStructure: vi.fn(),
    },
}));

describe('ComparisonView', () => {
    const mockLaw1 = {
        id: 'law_1',
        name: 'Law 1',
        tier: 'federal',
        category: 'Constitucional',
        articles: 0,
    };
    const mockLaw2 = {
        id: 'law_2',
        name: 'Law 2',
        tier: 'state',
        category: 'Civil',
        articles: 0,
    };

    const mockArticles1 = {
        law_id: 'law_1',
        law_name: 'Law 1',
        total: 2,
        articles: [
            { article_id: 'Art 1', text: 'Text 1' },
            { article_id: 'Art 2', text: 'Text 2' },
        ],
    };
    const mockArticles2 = {
        law_id: 'law_2',
        law_name: 'Law 2',
        total: 2,
        articles: [
            { article_id: 'Art 1', text: 'Text 1 modified' },
            { article_id: 'Art 3', text: 'Text 3' },
        ],
    };

    const mockStructure1 = {
        law_id: 'law_1',
        structure: [{ label: 'Book I', children: [] }],
    };
    const mockStructure2 = {
        law_id: 'law_2',
        structure: [{ label: 'Book II', children: [] }],
    };

    function setupMocks() {
        vi.mocked(api.getLaw).mockImplementation(async (id) => {
            if (id === '1') return mockLaw1 as unknown as Law;
            if (id === '2') return mockLaw2 as unknown as Law;
            throw new Error('Not found');
        });
        vi.mocked(api.getLawArticles).mockImplementation(async (id) => {
            if (id === '1') return mockArticles1;
            if (id === '2') return mockArticles2;
            throw new Error('Not found');
        });
        vi.mocked(api.getLawStructure).mockImplementation(async (id) => {
            if (id === '1') return mockStructure1;
            if (id === '2') return mockStructure2;
            throw new Error('Not found');
        });
    }

    beforeEach(() => {
        vi.mocked(api.getLaw).mockReset();
        vi.mocked(api.getLawArticles).mockReset();
        vi.mocked(api.getLawStructure).mockReset();
    });

    it('renders loading state initially', async () => {
        vi.mocked(api.getLaw).mockReturnValue(new Promise(() => {}));
        vi.mocked(api.getLawArticles).mockReturnValue(new Promise(() => {}));
        vi.mocked(api.getLawStructure).mockReturnValue(new Promise(() => {}));

        await act(async () => {
            render(<LanguageProvider><ComparisonView lawIds={['1', '2']} /></LanguageProvider>);
        });

        expect(screen.getByText(/Analizando estructura legal/i)).toBeInTheDocument();
    });

    it('renders comparison split view with law names', async () => {
        setupMocks();

        await act(async () => {
            render(<LanguageProvider><ComparisonView lawIds={['1', '2']} /></LanguageProvider>);
        });

        await waitFor(() => {
            expect(screen.getByText('Comparación Estructural')).toBeInTheDocument();
            // Law names appear in metadata panel and pane headers
            expect(screen.getAllByText('Law 1').length).toBeGreaterThanOrEqual(1);
            expect(screen.getAllByText('Law 2').length).toBeGreaterThanOrEqual(1);
        });
    });

    it('renders structure sidebar', async () => {
        setupMocks();

        await act(async () => {
            render(<LanguageProvider><ComparisonView lawIds={['1', '2']} /></LanguageProvider>);
        });

        await waitFor(() => {
            expect(screen.getAllByText('Book I')[0]).toBeInTheDocument();
        });
    });

    it('renders metadata panel with tier badges', async () => {
        setupMocks();

        await act(async () => {
            render(<LanguageProvider><ComparisonView lawIds={['1', '2']} /></LanguageProvider>);
        });

        await waitFor(() => {
            expect(screen.getByText('Federal')).toBeInTheDocument();
            expect(screen.getByText('Estatal')).toBeInTheDocument();
        });
    });

    it('displays article match count', async () => {
        setupMocks();

        await act(async () => {
            render(<LanguageProvider><ComparisonView lawIds={['1', '2']} /></LanguageProvider>);
        });

        // "Art 1" is shared between both laws → 1 match
        await waitFor(() => {
            expect(screen.getAllByText('1')[0]).toBeInTheDocument();
            expect(screen.getAllByText(/artículo en común/i)[0]).toBeInTheDocument();
        });
    });

    it('renders toolbar with sync and copy buttons', async () => {
        setupMocks();

        await act(async () => {
            render(<LanguageProvider><ComparisonView lawIds={['1', '2']} /></LanguageProvider>);
        });

        await waitFor(() => {
            expect(screen.getAllByText(/Sincronizar scroll|Sync/i)[0]).toBeInTheDocument();
            expect(screen.getAllByText(/Copiar enlace|URL/i)[0]).toBeInTheDocument();
        });
    });
});
