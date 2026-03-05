import { render, screen, fireEvent, act } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

// Mock next/link
vi.mock('next/link', () => ({
    default: ({ children, href, ...props }: any) => (
        <a href={href} {...props}>
            {children}
        </a>
    ),
}));

// Mock LanguageContext
vi.mock('@/components/providers/LanguageContext', () => ({
    useLang: vi.fn(() => ({ lang: 'es', setLang: vi.fn() })),
}));

// Mock AuthContext
const mockUseAuth = vi.fn(() => ({
    isAuthenticated: false,
    tier: 'anon' as const,
    userId: null,
    email: null,
    name: null,
    signOut: vi.fn(),
}));

vi.mock('@/components/providers/AuthContext', () => ({
    useAuth: (...args: any[]) => mockUseAuth(...args),
}));

// Mock billing
vi.mock('@/lib/billing', () => ({
    getCheckoutUrl: vi.fn(
        (plan: string, userId?: string) =>
            `https://dhanam.madfam.io/checkout?plan=tezca_${plan}&product=tezca${userId ? `&user_id=${userId}` : ''}`,
    ),
}));

// Mock @tezca/ui
vi.mock('@tezca/ui', () => ({
    Card: ({ children, className }: any) => (
        <div data-testid="card" className={className}>
            {children}
        </div>
    ),
    CardContent: ({ children, className }: any) => (
        <div className={className}>{children}</div>
    ),
    Badge: ({ children, className }: any) => (
        <span className={className}>{children}</span>
    ),
    Button: ({ children, className, ...props }: any) => (
        <button className={className} {...props}>
            {children}
        </button>
    ),
}));

// Mock lucide-react icons
vi.mock('lucide-react', () => ({
    Lock: ({ className }: any) => <span data-testid="lock-icon" className={className} />,
    ArrowRight: ({ className }: any) => <span data-testid="arrow-icon" className={className} />,
    Clock: ({ className }: any) => <span data-testid="clock-icon" className={className} />,
    Sparkles: ({ className }: any) => <span data-testid="sparkles-icon" className={className} />,
    X: ({ className }: any) => <span data-testid="x-icon" className={className} />,
}));

// Mock config
vi.mock('@/lib/config', () => ({
    API_BASE_URL: 'http://localhost:8000/api/v1',
}));

import { TierGate } from '@/components/TierGate';
import { useLang } from '@/components/providers/LanguageContext';
import { getCheckoutUrl } from '@/lib/billing';

describe('TierGate', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        vi.useFakeTimers();
        mockUseAuth.mockReturnValue({
            isAuthenticated: false,
            tier: 'anon' as const,
            userId: null,
            email: null,
            name: null,
            signOut: vi.fn(),
        });
        (useLang as ReturnType<typeof vi.fn>).mockReturnValue({
            lang: 'es',
            setLang: vi.fn(),
        });
    });

    afterEach(() => {
        vi.useRealTimers();
    });

    // ---------------------------------------------------------------
    // 1. Inline variant for anonymous users
    // ---------------------------------------------------------------
    it('renders inline variant with title and CTA for anon users', () => {
        render(<TierGate variant="inline" requiredTier="pro" />);

        // Anon users get targetTier = 'essentials', so title/CTA are essentials-level
        expect(screen.getByText('Crea tu cuenta gratuita')).toBeDefined();
        expect(screen.getByText('Empieza gratis')).toBeDefined();
    });

    // ---------------------------------------------------------------
    // 2. Inline variant for authenticated essentials users
    // ---------------------------------------------------------------
    it('renders inline variant with upgrade text for authenticated essentials user', () => {
        mockUseAuth.mockReturnValue({
            isAuthenticated: true,
            tier: 'essentials' as const,
            userId: 'user-123',
            email: 'user@example.com',
            name: 'Test User',
            signOut: vi.fn(),
        });

        render(<TierGate variant="inline" requiredTier="pro" />);

        // Authenticated users get targetTier = requiredTier (pro)
        expect(screen.getByText('Desbloquea todo con Tezca Pro')).toBeDefined();
        expect(screen.getByText('Mejora a Pro')).toBeDefined();
    });

    // ---------------------------------------------------------------
    // 3. Card variant with benefits list
    // ---------------------------------------------------------------
    it('renders card variant with benefits list', () => {
        mockUseAuth.mockReturnValue({
            isAuthenticated: true,
            tier: 'essentials' as const,
            userId: 'user-456',
            email: null,
            name: null,
            signOut: vi.fn(),
        });

        const benefits = [
            'Acceso a API avanzada',
            'Descargas masivas',
            'Soporte prioritario',
        ];

        render(
            <TierGate
                variant="card"
                requiredTier="community"
                benefits={benefits}
            />,
        );

        expect(screen.getByText('Desbloquea más con Community')).toBeDefined();
        for (const benefit of benefits) {
            expect(screen.getByText(benefit)).toBeDefined();
        }
    });

    // ---------------------------------------------------------------
    // 4. Toast variant with dismiss button
    // ---------------------------------------------------------------
    it('renders toast variant with dismiss button', () => {
        render(<TierGate variant="toast" requiredTier="community" />);

        // Toast should have dismiss button with aria-label
        const dismissButton = screen.getByLabelText('Cerrar');
        expect(dismissButton).toBeDefined();
    });

    // ---------------------------------------------------------------
    // 5. Countdown timer
    // ---------------------------------------------------------------
    it('shows countdown timer when showCountdown + retryAfterSeconds provided', () => {
        render(
            <TierGate
                variant="inline"
                requiredTier="pro"
                showCountdown
                retryAfterSeconds={125}
            />,
        );

        // 125 seconds = 2:05
        expect(screen.getByText('2:05')).toBeDefined();
        expect(screen.getByText('Tus consultas se renuevan en')).toBeDefined();

        // Advance 5 seconds, countdown should become 2:00
        act(() => {
            vi.advanceTimersByTime(5000);
        });

        expect(screen.getByText('2:00')).toBeDefined();
    });

    // ---------------------------------------------------------------
    // 6. onDismiss callback
    // ---------------------------------------------------------------
    it('calls onDismiss when dismiss button clicked', () => {
        const onDismiss = vi.fn();

        render(
            <TierGate
                variant="toast"
                requiredTier="pro"
                onDismiss={onDismiss}
            />,
        );

        const dismissButton = screen.getByLabelText('Cerrar');
        fireEvent.click(dismissButton);

        expect(onDismiss).toHaveBeenCalledOnce();
    });

    // ---------------------------------------------------------------
    // 7. Feature text displayed
    // ---------------------------------------------------------------
    it('shows feature text when provided', () => {
        render(
            <TierGate
                variant="inline"
                requiredTier="community"
                feature="Exportar en PDF"
            />,
        );

        expect(screen.getByText('Exportar en PDF')).toBeDefined();
    });

    // ---------------------------------------------------------------
    // 8. Subtitle when no feature text
    // ---------------------------------------------------------------
    it('shows subtitle when no feature text provided', () => {
        mockUseAuth.mockReturnValue({
            isAuthenticated: true,
            tier: 'essentials' as const,
            userId: 'user-789',
            email: null,
            name: null,
            signOut: vi.fn(),
        });

        render(
            <TierGate variant="card" requiredTier="community" />,
        );

        // community subtitle in Spanish
        expect(
            screen.getByText(
                'Búsqueda avanzada, acceso a API y descargas masivas',
            ),
        ).toBeDefined();
    });

    // ---------------------------------------------------------------
    // 9. Login link for unauthenticated users
    // ---------------------------------------------------------------
    it('links to /login for unauthenticated users', () => {
        render(<TierGate variant="inline" requiredTier="pro" />);

        const ctaLink = screen.getByText('Empieza gratis').closest('a');
        expect(ctaLink).toBeDefined();
        expect(ctaLink?.getAttribute('href')).toBe('/login');
    });

    // ---------------------------------------------------------------
    // 10. Checkout URL for authenticated users
    // ---------------------------------------------------------------
    it('links to checkout URL for authenticated users', () => {
        mockUseAuth.mockReturnValue({
            isAuthenticated: true,
            tier: 'essentials' as const,
            userId: 'user-abc',
            email: null,
            name: null,
            signOut: vi.fn(),
        });

        render(<TierGate variant="inline" requiredTier="pro" />);

        const ctaLink = screen.getByText('Mejora a Pro').closest('a');
        expect(ctaLink).toBeDefined();
        // getCheckoutUrl is called with ('pro', 'user-abc', window.location.href)
        expect(ctaLink?.getAttribute('href')).toContain('dhanam.madfam.io/checkout');
        expect(ctaLink?.getAttribute('href')).toContain('tezca_pro');
    });

    // ---------------------------------------------------------------
    // Additional edge cases
    // ---------------------------------------------------------------

    it('dismisses toast and renders nothing after dismiss', () => {
        const { container } = render(
            <TierGate variant="toast" requiredTier="pro" />,
        );

        expect(container.innerHTML).not.toBe('');

        const dismissButton = screen.getByLabelText('Cerrar');
        fireEvent.click(dismissButton);

        expect(container.innerHTML).toBe('');
    });

    it('renders overlay variant with backdrop blur', () => {
        render(<TierGate variant="overlay" requiredTier="community" />);

        // Overlay has backdrop-blur-sm class
        const overlay = document.querySelector('.backdrop-blur-sm');
        expect(overlay).toBeDefined();
        expect(overlay).not.toBeNull();
    });

    it('shows current tier badge in card variant', () => {
        mockUseAuth.mockReturnValue({
            isAuthenticated: true,
            tier: 'essentials' as const,
            userId: 'user-tier',
            email: null,
            name: null,
            signOut: vi.fn(),
        });

        render(<TierGate variant="card" requiredTier="pro" />);

        // Shows current plan label and tier display names
        expect(screen.getByText(/Tu plan actual.*Essentials/)).toBeDefined();
        expect(screen.getByText('Pro')).toBeDefined();
    });

    it('renders in English when lang is en', () => {
        (useLang as ReturnType<typeof vi.fn>).mockReturnValue({
            lang: 'en',
            setLang: vi.fn(),
        });

        render(<TierGate variant="inline" requiredTier="pro" />);

        // Anon -> essentials target
        expect(screen.getByText('Create your free account')).toBeDefined();
        expect(screen.getByText('Start free')).toBeDefined();
    });

    it('renders in Nahuatl when lang is nah', () => {
        (useLang as ReturnType<typeof vi.fn>).mockReturnValue({
            lang: 'nah',
            setLang: vi.fn(),
        });

        render(<TierGate variant="inline" requiredTier="pro" />);

        // Anon -> essentials target
        expect(screen.getByText('Xictlālia mocuenta')).toBeDefined();
        expect(screen.getByText('Xipēhua')).toBeDefined();
    });

    it('for essentials requiredTier authenticated user, checkout uses community plan', () => {
        mockUseAuth.mockReturnValue({
            isAuthenticated: true,
            tier: 'anon' as const,
            userId: 'user-ess',
            email: null,
            name: null,
            signOut: vi.fn(),
        });

        render(<TierGate variant="inline" requiredTier="essentials" />);

        // When requiredTier is essentials and user is authenticated,
        // getCheckoutUrl receives 'community' (not 'essentials')
        expect(getCheckoutUrl).toHaveBeenCalledWith(
            'community',
            'user-ess',
            expect.any(String),
        );
    });

    it('countdown reaches zero and stops', () => {
        render(
            <TierGate
                variant="inline"
                requiredTier="pro"
                showCountdown
                retryAfterSeconds={2}
            />,
        );

        // Initial: 0:02
        expect(screen.getByText('0:02')).toBeDefined();

        act(() => {
            vi.advanceTimersByTime(1000);
        });
        expect(screen.getByText('0:01')).toBeDefined();

        act(() => {
            vi.advanceTimersByTime(1000);
        });

        // At 0, the countdown display is null, so rateLimited text should not appear
        expect(screen.queryByText('0:00')).toBeNull();
    });

    it('applies custom className', () => {
        const { container } = render(
            <TierGate
                variant="inline"
                requiredTier="pro"
                className="custom-test-class"
            />,
        );

        const root = container.firstElementChild;
        expect(root?.className).toContain('custom-test-class');
    });
});
