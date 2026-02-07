import { render, screen, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { api } from '@/lib/api';

// Mock next/navigation
const mockPush = vi.fn();
const mockSearchParams = new URLSearchParams();
vi.mock('next/navigation', () => ({
    useRouter: () => ({ push: mockPush }),
    useSearchParams: () => mockSearchParams,
}));

// Mock API
vi.mock('@/lib/api', () => ({
    api: {
        getLaws: vi.fn(),
    },
}));

// Mock LanguageContext
vi.mock('@/components/providers/LanguageContext', () => ({
    useLang: () => ({ lang: 'es' }),
}));

// Mock next/link
vi.mock('next/link', () => ({
    default: ({ children, href, ...props }: { children: React.ReactNode; href: string; [key: string]: unknown }) => (
        <a href={href} {...props}>{children}</a>
    ),
}));

// Mock @tezca/ui Select components
vi.mock('@tezca/ui', () => ({
    Select: ({ children, value, onValueChange: _onValueChange }: { children: React.ReactNode; value?: string; onValueChange?: (v: string) => void }) => (
        <div data-testid="select" data-value={value}>{children}</div>
    ),
    SelectTrigger: ({ children, className }: { children: React.ReactNode; className?: string }) => (
        <button data-testid="select-trigger" className={className}>{children}</button>
    ),
    SelectContent: ({ children }: { children: React.ReactNode }) => (
        <div data-testid="select-content">{children}</div>
    ),
    SelectItem: ({ children, value }: { children: React.ReactNode; value: string }) => (
        <div data-testid="select-item" data-value={value}>{children}</div>
    ),
    SelectValue: ({ placeholder }: { placeholder?: string }) => (
        <span data-testid="select-value">{placeholder}</span>
    ),
}));

// Mock LawCard
vi.mock('@/components/LawCard', () => ({
    default: ({ law }: { law: { id: string; name: string } }) => (
        <div data-testid="law-card">{law.name}</div>
    ),
}));

// Mock Pagination
vi.mock('@/components/Pagination', () => ({
    Pagination: ({ currentPage, totalPages, onPageChange: _onPageChange }: { currentPage: number; totalPages: number; onPageChange: (p: number) => void }) => (
        <div data-testid="pagination">Page {currentPage} of {totalPages}</div>
    ),
}));

// Import after mocks are set up
import LawsPage from '@/app/leyes/page';

const mockLawsResponse = {
    count: 120,
    next: null,
    previous: null,
    results: [
        { id: 'ley-amparo', name: 'Ley de Amparo', grade: 'A', priority: 1, articles: 271, score: 98.5, transitorios: 12 },
        { id: 'codigo-civil', name: 'Codigo Civil Federal', grade: 'B', priority: 2, articles: 450, score: 85.0, transitorios: 5 },
    ],
};

describe('LawsPage (/leyes)', () => {
    beforeEach(() => {
        vi.mocked(api.getLaws).mockReset();
        mockPush.mockReset();
    });

    it('shows loading skeleton while fetching laws', () => {
        vi.mocked(api.getLaws).mockReturnValue(new Promise(() => {})); // never resolves

        const { container } = render(<LawsPage />);

        expect(container.querySelector('.animate-pulse')).toBeInTheDocument();
        expect(screen.getByText('Cargando leyes...')).toBeInTheDocument();
    });

    it('renders law cards after loading', async () => {
        vi.mocked(api.getLaws).mockResolvedValue(mockLawsResponse);

        render(<LawsPage />);

        await waitFor(() => {
            expect(screen.getByText('Ley de Amparo')).toBeInTheDocument();
        });

        expect(screen.getByText('Codigo Civil Federal')).toBeInTheDocument();
    });

    it('renders sort dropdown and total count', async () => {
        vi.mocked(api.getLaws).mockResolvedValue(mockLawsResponse);

        render(<LawsPage />);

        await waitFor(() => {
            expect(screen.getByText(/120/)).toBeInTheDocument();
        });

        expect(screen.getByText(/leyes disponibles/)).toBeInTheDocument();
        // Sort dropdown rendered via mocked Select
        expect(screen.getByTestId('select')).toBeInTheDocument();
    });

    it('calls api.getLaws with default params', async () => {
        vi.mocked(api.getLaws).mockResolvedValue(mockLawsResponse);

        render(<LawsPage />);

        await waitFor(() => {
            expect(api.getLaws).toHaveBeenCalledWith(
                expect.objectContaining({
                    page: 1,
                    page_size: 50,
                    sort: 'name_asc',
                })
            );
        });
    });

    it('renders pagination when multiple pages exist', async () => {
        vi.mocked(api.getLaws).mockResolvedValue({
            ...mockLawsResponse,
            count: 200, // 200 / 50 = 4 pages
        });

        render(<LawsPage />);

        await waitFor(() => {
            expect(screen.getByTestId('pagination')).toBeInTheDocument();
        });

        expect(screen.getByText(/Page 1 of 4/)).toBeInTheDocument();
    });

    it('shows error state and retry button when API fails', async () => {
        vi.mocked(api.getLaws).mockRejectedValue(new Error('Network error'));

        render(<LawsPage />);

        await waitFor(() => {
            expect(screen.getByText(/No se pudieron cargar las leyes/)).toBeInTheDocument();
        });

        expect(screen.getByText('Reintentar')).toBeInTheDocument();
    });

    it('shows empty state when no laws returned', async () => {
        vi.mocked(api.getLaws).mockResolvedValue({
            count: 0,
            next: null,
            previous: null,
            results: [],
        });

        render(<LawsPage />);

        await waitFor(() => {
            expect(screen.getByText('No se encontraron leyes.')).toBeInTheDocument();
        });
    });
});
