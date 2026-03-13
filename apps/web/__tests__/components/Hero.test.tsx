import { render, screen, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';

// Mock LanguageContext
vi.mock('@/components/providers/LanguageContext', () => ({
    useLang: vi.fn(() => ({ lang: 'es', setLang: vi.fn() })),
    LOCALE_MAP: { es: 'es-MX', en: 'en-US', nah: 'es-MX' },
}));

// Mock @tezca/ui
vi.mock('@tezca/ui', () => ({
    Button: ({ children, className, ...props }: any) => (
        <button className={className} {...props}>{children}</button>
    ),
}));

// Mock lucide-react
vi.mock('lucide-react', () => ({
    Search: ({ className }: any) => <span data-testid="search-icon" className={className} />,
}));

// Mock SearchAutocomplete
vi.mock('@/components/SearchAutocomplete', () => ({
    SearchAutocomplete: ({ placeholder, onSearch }: any) => (
        <input
            role="combobox"
            placeholder={placeholder}
            data-testid="search-autocomplete"
            onChange={(e: any) => {}}
        />
    ),
}));

// Mock DashboardStats
const mockGetSharedStats = vi.fn();
vi.mock('@/components/DashboardStats', () => ({
    getSharedStats: (...args: any[]) => mockGetSharedStats(...args),
}));

import { Hero } from '@/components/Hero';
import { useLang } from '@/components/providers/LanguageContext';

describe('Hero', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        mockGetSharedStats.mockResolvedValue({ total_laws: 35000 });
        (useLang as ReturnType<typeof vi.fn>).mockReturnValue({ lang: 'es', setLang: vi.fn() });
    });

    // ---------------------------------------------------------------
    // 1. Renders Tezca headline
    // ---------------------------------------------------------------
    it('renders the Tezca headline', () => {
        render(<Hero />);
        expect(screen.getByText('Tezca')).toBeInTheDocument();
    });

    // ---------------------------------------------------------------
    // 2. Renders Spanish subtitle
    // ---------------------------------------------------------------
    it('renders the Spanish subtitle', () => {
        render(<Hero />);
        expect(screen.getByText('El Espejo de la Ley')).toBeInTheDocument();
    });

    // ---------------------------------------------------------------
    // 3. Renders search button
    // ---------------------------------------------------------------
    it('renders the search button', () => {
        render(<Hero />);
        expect(screen.getByText('Buscar')).toBeInTheDocument();
    });

    // ---------------------------------------------------------------
    // 4. Shows tagline
    // ---------------------------------------------------------------
    it('shows the tagline', () => {
        render(<Hero />);
        expect(screen.getByText(/Búsqueda inteligente en tiempo real/)).toBeInTheDocument();
    });

    // ---------------------------------------------------------------
    // 5. Renders search autocomplete
    // ---------------------------------------------------------------
    it('renders search autocomplete input', () => {
        render(<Hero />);
        expect(screen.getByTestId('search-autocomplete')).toBeInTheDocument();
    });

    // ---------------------------------------------------------------
    // 6. Shows placeholder with law count
    // ---------------------------------------------------------------
    it('shows placeholder with law count after stats load', async () => {
        render(<Hero />);

        await waitFor(() => {
            expect(screen.getByPlaceholderText(/Buscar en 35,000 leyes/)).toBeInTheDocument();
        });
    });

    // ---------------------------------------------------------------
    // 7. Shows fallback placeholder before stats
    // ---------------------------------------------------------------
    it('shows fallback placeholder before stats load', () => {
        mockGetSharedStats.mockReturnValue(new Promise(() => {}));
        render(<Hero />);

        expect(screen.getByPlaceholderText('Buscar leyes...')).toBeInTheDocument();
    });

    // ---------------------------------------------------------------
    // 8. English subtitle
    // ---------------------------------------------------------------
    it('renders English subtitle when lang is en', () => {
        (useLang as ReturnType<typeof vi.fn>).mockReturnValue({ lang: 'en', setLang: vi.fn() });
        render(<Hero />);

        expect(screen.getByText('The Mirror of the Law')).toBeInTheDocument();
        expect(screen.getByText('Search')).toBeInTheDocument();
    });

    // ---------------------------------------------------------------
    // 9. Nahuatl subtitle
    // ---------------------------------------------------------------
    it('renders Nahuatl subtitle when lang is nah', () => {
        (useLang as ReturnType<typeof vi.fn>).mockReturnValue({ lang: 'nah', setLang: vi.fn() });
        render(<Hero />);

        expect(screen.getByText('In Tezcatl in Tenahuatilli')).toBeInTheDocument();
        expect(screen.getByText('Xictlatemo')).toBeInTheDocument();
    });

    // ---------------------------------------------------------------
    // 10. h1 exists for SEO
    // ---------------------------------------------------------------
    it('has a proper h1 heading for SEO', () => {
        render(<Hero />);
        const h1 = document.querySelector('h1');
        expect(h1).toBeDefined();
        expect(h1?.textContent).toBe('Tezca');
    });

    // ---------------------------------------------------------------
    // 11. Handles stats failure gracefully
    // ---------------------------------------------------------------
    it('handles stats failure gracefully and shows fallback placeholder', async () => {
        mockGetSharedStats.mockRejectedValue(new Error('API error'));
        render(<Hero />);

        // Should still render with fallback placeholder
        await waitFor(() => {
            expect(screen.getByPlaceholderText('Buscar leyes...')).toBeInTheDocument();
        });
    });

    // ---------------------------------------------------------------
    // 12. Section element wraps hero
    // ---------------------------------------------------------------
    it('renders a section element', () => {
        render(<Hero />);
        const section = document.querySelector('section');
        expect(section).toBeDefined();
        expect(section).not.toBeNull();
    });
});
