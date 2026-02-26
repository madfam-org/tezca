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

// Mock AuthContext
vi.mock('@/components/providers/AuthContext', () => ({
    useAuth: vi.fn(() => ({
        isAuthenticated: false,
        tier: 'anon' as const,
        loginUrl: '/api/auth/signin',
        userId: null,
        email: null,
        name: null,
        signOut: vi.fn(),
    })),
}));

// Mock CommandSearch
vi.mock('@/components/CommandSearch', () => ({
    CommandSearchTrigger: () => <button data-testid="command-search-trigger" aria-label="Buscar leyes y artículos...">Search</button>,
}));

// Mock AuthModal
vi.mock('@/components/AuthModal', () => ({
    AuthModal: ({ open }: { open: boolean; onClose: () => void }) =>
        open ? <div data-testid="auth-modal">Auth Modal</div> : null,
}));

import { Navbar } from '@/components/Navbar';
import { useAuth } from '@/components/providers/AuthContext';

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

    it('shows sign-in button when unauthenticated', () => {
        render(<Navbar />);
        expect(screen.getByLabelText('Iniciar sesión')).toBeInTheDocument();
    });

    it('opens auth modal when sign-in button clicked', () => {
        render(<Navbar />);
        fireEvent.click(screen.getByLabelText('Iniciar sesión'));
        expect(screen.getByTestId('auth-modal')).toBeInTheDocument();
    });

    it('shows UserButton when authenticated', () => {
        vi.mocked(useAuth).mockReturnValue({
            isAuthenticated: true,
            tier: 'free',
            loginUrl: '/api/auth/signin',
            userId: 'test-user',
            email: 'test@example.com',
            name: 'Test User',
            signOut: vi.fn(),
        });
        render(<Navbar />);
        // Sign-in button should not be present
        expect(screen.queryByLabelText('Iniciar sesión')).not.toBeInTheDocument();
    });
});
