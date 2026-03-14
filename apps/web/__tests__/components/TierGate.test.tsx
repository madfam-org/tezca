import { render, screen, fireEvent, act } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { defaultAuthState, mockAuth } from '../helpers/auth-mock';

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
const mockUseAuth = vi.fn(() => defaultAuthState);

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
        mockUseAuth.mockReturnValue(defaultAuthState);
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
        render(<TierGate variant="inline" requiredTier="academic" />);

        // Anon users get targetTier = 'essentials', so title/CTA are essentials-level
        expect(screen.getByText('Crea tu cuenta gratuita')).toBeDefined();
        expect(screen.getByText('Empieza gratis')).toBeDefined();
    });

    // ---------------------------------------------------------------
    // 2. Inline variant for authenticated essentials users
    // ---------------------------------------------------------------
    it('renders inline variant with upgrade text for authenticated essentials user', () => {
        mockUseAuth.mockReturnValue(mockAuth({
            isAuthenticated: true,
            tier: 'essentials',
            userId: 'user-123',
            email: 'user@example.com',
            name: 'Test User',
        }));

        render(<TierGate variant="inline" requiredTier="academic" />);

        // Authenticated users get targetTier = requiredTier (academic)
        expect(screen.getByText('Desbloquea todo con Academic')).toBeDefined();
        expect(screen.getByText('Mejora a Academic')).toBeDefined();
    });

    // ---------------------------------------------------------------
    // 3. Card variant with benefits list
    // ---------------------------------------------------------------
    it('renders card variant with benefits list', () => {
        mockUseAuth.mockReturnValue(mockAuth({
            isAuthenticated: true,
            tier: 'essentials',
            userId: 'user-456',
        }));

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

        expect(screen.getByText('Crea tu cuenta gratuita')).toBeDefined();
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
                requiredTier="academic"
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
                requiredTier="academic"
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
        mockUseAuth.mockReturnValue(mockAuth({
            isAuthenticated: true,
            tier: 'essentials',
            userId: 'user-789',
        }));

        render(
            <TierGate variant="card" requiredTier="community" />,
        );

        // community subtitle in Spanish
        expect(
            screen.getByText(
                'Accede a PDF, JSON y funciones básicas',
            ),
        ).toBeDefined();
    });

    // ---------------------------------------------------------------
    // 9. Login link for unauthenticated users
    // ---------------------------------------------------------------
    it('links to /login for unauthenticated users', () => {
        render(<TierGate variant="inline" requiredTier="academic" />);

        const ctaLink = screen.getByText('Empieza gratis').closest('a');
        expect(ctaLink).toBeDefined();
        expect(ctaLink?.getAttribute('href')).toBe('/login');
    });

    // ---------------------------------------------------------------
    // 10. Checkout URL for authenticated users
    // ---------------------------------------------------------------
    it('links to checkout URL for authenticated users', () => {
        mockUseAuth.mockReturnValue(mockAuth({
            isAuthenticated: true,
            tier: 'essentials',
            userId: 'user-abc',
        }));

        render(<TierGate variant="inline" requiredTier="academic" />);

        const ctaLink = screen.getByText('Mejora a Academic').closest('a');
        expect(ctaLink).toBeDefined();
        // getCheckoutUrl is called with ('academic', 'user-abc', window.location.href)
        expect(ctaLink?.getAttribute('href')).toContain('dhanam.madfam.io/checkout');
        expect(ctaLink?.getAttribute('href')).toContain('tezca_academic');
    });

    // ---------------------------------------------------------------
    // Additional edge cases
    // ---------------------------------------------------------------

    it('dismisses toast and renders nothing after dismiss', () => {
        const { container } = render(
            <TierGate variant="toast" requiredTier="academic" />,
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
        mockUseAuth.mockReturnValue(mockAuth({
            isAuthenticated: true,
            tier: 'essentials',
            userId: 'user-tier',
        }));

        render(<TierGate variant="card" requiredTier="academic" />);

        // Shows current plan label and tier display names
        expect(screen.getByText(/Tu plan actual.*Essentials/)).toBeDefined();
        expect(screen.getByText('Academic')).toBeDefined();
    });

    it('renders in English when lang is en', () => {
        (useLang as ReturnType<typeof vi.fn>).mockReturnValue({
            lang: 'en',
            setLang: vi.fn(),
        });

        render(<TierGate variant="inline" requiredTier="academic" />);

        // Anon -> essentials target
        expect(screen.getByText('Create your free account')).toBeDefined();
        expect(screen.getByText('Start free')).toBeDefined();
    });

    it('renders in Nahuatl when lang is nah', () => {
        (useLang as ReturnType<typeof vi.fn>).mockReturnValue({
            lang: 'nah',
            setLang: vi.fn(),
        });

        render(<TierGate variant="inline" requiredTier="academic" />);

        // Anon -> essentials target
        expect(screen.getByText('Xictlālia mocuenta')).toBeDefined();
        expect(screen.getByText('Xipēhua')).toBeDefined();
    });

    it('for essentials requiredTier authenticated user, checkout uses essentials plan', () => {
        mockUseAuth.mockReturnValue(mockAuth({
            isAuthenticated: true,
            tier: 'anon',
            userId: 'user-ess',
        }));

        render(<TierGate variant="inline" requiredTier="essentials" />);

        // When requiredTier is essentials and user is authenticated,
        // getCheckoutUrl receives 'essentials'
        expect(getCheckoutUrl).toHaveBeenCalledWith(
            'essentials',
            'user-ess',
            expect.any(String),
        );
    });

    it('countdown reaches zero and stops', () => {
        render(
            <TierGate
                variant="inline"
                requiredTier="academic"
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
                requiredTier="academic"
                className="custom-test-class"
            />,
        );

        const root = container.firstElementChild;
        expect(root?.className).toContain('custom-test-class');
    });
});
