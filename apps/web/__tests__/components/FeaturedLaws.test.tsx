import { render, screen, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';

// Mock next/link
vi.mock('next/link', () => ({
    default: ({ children, href }: { children: React.ReactNode; href: string }) => (
        <a href={href}>{children}</a>
    ),
}));

// Mock LanguageContext
vi.mock('@/components/providers/LanguageContext', () => ({
    useLang: vi.fn(() => ({ lang: 'es', setLang: vi.fn() })),
}));

// Mock @tezca/ui
vi.mock('@tezca/ui', () => ({
    Card: ({ children, className }: { children: React.ReactNode; className?: string }) => (
        <div data-testid="card" className={className}>{children}</div>
    ),
    CardContent: ({ children, className }: { children: React.ReactNode; className?: string }) => (
        <div className={className}>{children}</div>
    ),
    Badge: ({ children }: { children: React.ReactNode }) => (
        <span data-testid="badge">{children}</span>
    ),
}));

// Mock api
const mockGetLaws = vi.fn();
vi.mock('@/lib/api', () => ({
    api: {
        getLaws: (...args: unknown[]) => mockGetLaws(...args),
    },
}));

import { FeaturedLaws } from '@/components/FeaturedLaws';

describe('FeaturedLaws', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it('shows loading skeleton initially', () => {
        mockGetLaws.mockReturnValue(new Promise(() => {})); // never resolves
        render(<FeaturedLaws />);
        const skeletons = document.querySelectorAll('.animate-pulse');
        expect(skeletons.length).toBeGreaterThan(0);
    });

    it('fetches laws with correct params', async () => {
        mockGetLaws.mockResolvedValue({ results: [] });
        render(<FeaturedLaws />);

        await waitFor(() => {
            expect(mockGetLaws).toHaveBeenCalledWith({ sort: 'date_desc', page_size: 4 });
        });
    });

    it('renders law cards after loading', async () => {
        mockGetLaws.mockResolvedValue({
            results: [
                { id: 'law-1', name: 'Ley Federal del Trabajo', tier: 'federal', versions: 5 },
                { id: 'law-2', name: 'Código Civil Federal', tier: 'federal', versions: 3 },
            ],
        });

        render(<FeaturedLaws />);

        await waitFor(() => {
            expect(screen.getByText('Ley Federal del Trabajo')).toBeInTheDocument();
            expect(screen.getByText('Código Civil Federal')).toBeInTheDocument();
        });
    });

    it('shows tier badges on cards', async () => {
        mockGetLaws.mockResolvedValue({
            results: [
                { id: 'law-1', name: 'Ley Test', tier: 'federal', versions: 1 },
            ],
        });

        render(<FeaturedLaws />);

        await waitFor(() => {
            expect(screen.getByText('Federal')).toBeInTheDocument();
        });
    });

    it('renders view all link', async () => {
        mockGetLaws.mockResolvedValue({
            results: [{ id: 'law-1', name: 'Test', tier: 'federal', versions: 1 }],
        });

        render(<FeaturedLaws />);

        await waitFor(() => {
            const links = screen.getAllByText('Ver catálogo completo');
            expect(links.length).toBeGreaterThan(0);
        });
    });

    it('renders nothing when no results', async () => {
        mockGetLaws.mockResolvedValue({ results: [] });

        const { container } = render(<FeaturedLaws />);

        await waitFor(() => {
            // After loading with empty results, component returns null
            expect(container.querySelector('section')).toBeNull();
        });
    });

    it('handles API errors gracefully', async () => {
        mockGetLaws.mockRejectedValue(new Error('Network error'));

        const { container } = render(<FeaturedLaws />);

        await waitFor(() => {
            // Should not crash — renders nothing
            expect(container.querySelector('section')).toBeNull();
        });
    });

    it('links to correct law detail pages', async () => {
        mockGetLaws.mockResolvedValue({
            results: [
                { id: 'mx-fed-lft', name: 'Ley Federal del Trabajo', tier: 'federal', versions: 5 },
            ],
        });

        render(<FeaturedLaws />);

        await waitFor(() => {
            const link = screen.getByText('Ley Federal del Trabajo').closest('a');
            expect(link?.getAttribute('href')).toBe('/leyes/mx-fed-lft');
        });
    });

    it('renders section title', async () => {
        mockGetLaws.mockResolvedValue({
            results: [{ id: 'law-1', name: 'Test', tier: 'federal', versions: 1 }],
        });

        render(<FeaturedLaws />);

        await waitFor(() => {
            expect(screen.getByText('Leyes Destacadas')).toBeInTheDocument();
        });
    });
});
