import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';

// Mock next/navigation
vi.mock('next/navigation', () => ({
    usePathname: vi.fn(() => '/busqueda'),
    useRouter: vi.fn(() => ({ push: vi.fn() })),
    useSearchParams: vi.fn(() => new URLSearchParams()),
}));

// Mock next-themes
vi.mock('next-themes', () => ({
    useTheme: vi.fn(() => ({ theme: 'light', setTheme: vi.fn() })),
}));

// Mock LanguageContext
vi.mock('@/components/providers/LanguageContext', () => ({
    useLang: vi.fn(() => ({ lang: 'es', setLang: vi.fn() })),
    LanguageProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

// Mock CommandSearch
vi.mock('@/components/CommandSearch', () => ({
    CommandSearchTrigger: () => <button data-testid="command-search-trigger" aria-label="Buscar leyes y artículos...">Search</button>,
}));

import { Navbar } from '@/components/Navbar';

describe('Navbar', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it('renders brand name', () => {
        render(<Navbar />);
        expect(screen.getByText('Tezca')).toBeDefined();
    });

    it('renders nav links', () => {
        render(<Navbar />);
        expect(screen.getByText('Inicio')).toBeDefined();
        expect(screen.getByText('Buscar')).toBeDefined();
        expect(screen.getByText('Explorar')).toBeDefined();
        expect(screen.getByText('Favoritos')).toBeDefined();
    });

    it('has mobile menu button', () => {
        render(<Navbar />);
        const btn = screen.getByLabelText('Abrir menú');
        expect(btn).toBeDefined();
    });

    it('toggles mobile menu', () => {
        render(<Navbar />);
        const btn = screen.getByLabelText('Abrir menú');
        fireEvent.click(btn);
        expect(screen.getByLabelText('Cerrar menú')).toBeDefined();
    });

    it('highlights active link', () => {
        render(<Navbar />);
        // /search is the mocked pathname
        const searchLinks = screen.getAllByText('Buscar');
        const desktopLink = searchLinks[0];
        expect(desktopLink.className).toContain('text-primary');
    });

    it('renders command search trigger', () => {
        render(<Navbar />);
        expect(screen.getByTestId('command-search-trigger')).toBeDefined();
    });
});
