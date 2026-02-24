import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';

// Mock next/link
vi.mock('next/link', () => ({
    default: ({ children, href, ...props }: { children: React.ReactNode; href: string; [key: string]: unknown }) => (
        <a href={href} {...props}>{children}</a>
    ),
}));

// Mock @tezca/ui
vi.mock('@tezca/ui', () => ({
    Card: ({ children, className }: { children: React.ReactNode; className?: string }) => (
        <div data-testid="card" className={className}>{children}</div>
    ),
    CardContent: ({ children, className }: { children: React.ReactNode; className?: string }) => (
        <div className={className}>{children}</div>
    ),
}));

// Mock global fetch
const mockFetch = vi.fn();
global.fetch = mockFetch;

// Import after mocks
import CategoriesIndexPage from '@/app/categorias/page';

const mockCategories = [
    { category: 'civil', count: 120, label: 'Civil' },
    { category: 'penal', count: 85, label: 'Penal' },
    { category: 'fiscal', count: 60, label: 'Fiscal' },
    { category: 'laboral', count: 45, label: 'Laboral' },
];

describe('CategoriesIndexPage (/categorias)', () => {
    beforeEach(() => {
        mockFetch.mockReset();
    });

    it('renders category cards with counts from API', async () => {
        mockFetch.mockResolvedValue({
            ok: true,
            json: () => Promise.resolve(mockCategories),
        });

        const Page = await CategoriesIndexPage({ searchParams: Promise.resolve({}) });
        render(Page);

        // Page title
        expect(screen.getByRole('heading', { level: 1, name: 'Categorias' })).toBeInTheDocument();

        // Subtitle
        expect(screen.getByText(/Explora la legislacion mexicana por categoria/)).toBeInTheDocument();

        // Category names from CATEGORY_META (in Spanish)
        expect(screen.getByText('Civil')).toBeInTheDocument();
        expect(screen.getByText('Penal')).toBeInTheDocument();
        expect(screen.getByText('Fiscal')).toBeInTheDocument();
        expect(screen.getByText('Laboral')).toBeInTheDocument();

        // Counts displayed
        expect(screen.getByText(/120/)).toBeInTheDocument();
        expect(screen.getByText(/85/)).toBeInTheDocument();
    });

    it('renders all hardcoded categories even without API data', async () => {
        mockFetch.mockResolvedValue({
            ok: true,
            json: () => Promise.resolve([]),
        });

        const Page = await CategoriesIndexPage({ searchParams: Promise.resolve({}) });
        render(Page);

        // All seven hardcoded categories should appear
        expect(screen.getByText('Civil')).toBeInTheDocument();
        expect(screen.getByText('Penal')).toBeInTheDocument();
        expect(screen.getByText('Mercantil')).toBeInTheDocument();
        expect(screen.getByText('Fiscal')).toBeInTheDocument();
        expect(screen.getByText('Laboral')).toBeInTheDocument();
        expect(screen.getByText('Administrativo')).toBeInTheDocument();
        expect(screen.getByText('Constitucional')).toBeInTheDocument();
    });

    it('generates correct links to category detail pages', async () => {
        mockFetch.mockResolvedValue({
            ok: true,
            json: () => Promise.resolve(mockCategories),
        });

        const Page = await CategoriesIndexPage({ searchParams: Promise.resolve({}) });
        render(Page);

        const civilLink = screen.getByText('Civil').closest('a');
        expect(civilLink).toHaveAttribute('href', '/categorias/civil');

        const penalLink = screen.getByText('Penal').closest('a');
        expect(penalLink).toHaveAttribute('href', '/categorias/penal');
    });

    it('falls back gracefully when fetch fails', async () => {
        mockFetch.mockRejectedValue(new Error('Network error'));

        const Page = await CategoriesIndexPage({ searchParams: Promise.resolve({}) });
        render(Page);

        // Should still render the page with hardcoded categories, just no counts
        expect(screen.getByRole('heading', { level: 1, name: 'Categorias' })).toBeInTheDocument();
        expect(screen.getByText('Civil')).toBeInTheDocument();
        expect(screen.getByText('Penal')).toBeInTheDocument();
    });

    it('falls back gracefully when fetch returns non-OK', async () => {
        mockFetch.mockResolvedValue({
            ok: false,
            status: 500,
            json: () => Promise.resolve([]),
        });

        const Page = await CategoriesIndexPage({ searchParams: Promise.resolve({}) });
        render(Page);

        // Page renders with categories but without counts
        expect(screen.getByText('Civil')).toBeInTheDocument();
        expect(screen.getByText('Constitucional')).toBeInTheDocument();
    });

    it('renders breadcrumb navigation', async () => {
        mockFetch.mockResolvedValue({
            ok: true,
            json: () => Promise.resolve(mockCategories),
        });

        const Page = await CategoriesIndexPage({ searchParams: Promise.resolve({}) });
        render(Page);

        const breadcrumbNav = screen.getByRole('navigation', { name: 'Breadcrumb' });
        expect(breadcrumbNav).toBeInTheDocument();

        expect(screen.getByText('Inicio')).toBeInTheDocument();
    });
});
