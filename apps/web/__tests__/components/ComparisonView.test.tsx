import { render, screen, waitFor, act } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import ComparisonView from '@/components/ComparisonView';
import { api } from '@/lib/api';

// Mock API
vi.mock('@/lib/api', () => ({
    api: {
        getLawArticles: vi.fn(),
        getLawStructure: vi.fn(),
    },
}));

describe('ComparisonView', () => {
    const mockArticles1 = {
        law_id: 'law_1',
        law_name: 'Law 1',
        total: 1,
        articles: [{ article_id: 'Art 1', text: 'Text 1' }],
    };
    const mockArticles2 = {
        law_id: 'law_2',
        law_name: 'Law 2',
        total: 1,
        articles: [{ article_id: 'Art 1', text: 'Text 1 modified' }],
    };

    const mockStructure1 = {
        law_id: 'law_1',
        structure: [{ label: 'Book I', children: [] }],
    };
    const mockStructure2 = {
        law_id: 'law_2',
        structure: [{ label: 'Book II', children: [] }],
    };

    beforeEach(() => {
        vi.mocked(api.getLawArticles).mockReset();
        vi.mocked(api.getLawStructure).mockReset();
    });

    it('renders loading state initially', async () => {
        // Mock with never-resolving promises to keep loading state
        vi.mocked(api.getLawArticles).mockReturnValue(new Promise(() => {}));
        vi.mocked(api.getLawStructure).mockReturnValue(new Promise(() => {}));

        await act(async () => {
            render(<ComparisonView lawIds={['1', '2']} />);
        });

        expect(screen.getByText(/Analizando estructura legal/i)).toBeInTheDocument();
    });

    it('renders comparison split view', async () => {
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

        await act(async () => {
            render(<ComparisonView lawIds={['1', '2']} />);
        });

        await waitFor(() => {
            expect(screen.getByText('Law 1')).toBeInTheDocument();
            expect(screen.getByText('Law 2')).toBeInTheDocument();
        });

        expect(screen.getByText('Comparación Estructural')).toBeInTheDocument();
    });

    it('renders structure sidebar', async () => {
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

        await act(async () => {
            render(<ComparisonView lawIds={['1', '2']} />);
        });

        await waitFor(() => {
            expect(screen.getAllByText('Book I')[0]).toBeInTheDocument();
        });
    });
});
