import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { mockAuth } from '../helpers/auth-mock';

const mockUseLang = vi.fn(() => ({ lang: 'es' as const, setLang: vi.fn() }));
vi.mock('@/components/providers/LanguageContext', () => ({
    useLang: (...args: any[]) => mockUseLang(...args),
}));

const mockUseAuth = vi.fn(() => mockAuth({ tier: 'anon' }));
vi.mock('@/components/providers/AuthContext', () => ({
    useAuth: (...args: any[]) => mockUseAuth(...args),
}));

vi.mock('@/lib/billing', () => ({
    getTrialCheckoutUrl: vi.fn(
        (plan: string, userId?: string, _returnUrl?: string) =>
            `https://app.dhan.am/checkout?plan=tezca_${plan}&mode=trial_cc`
    ),
    hasPaidAccess: vi.fn(() => false),
}));

vi.mock('next/link', () => ({
    default: ({ children, href, ...props }: any) => (
        <a href={href} {...props}>{children}</a>
    ),
}));

vi.mock('@tezca/ui', () => ({
    Card: ({ children, className }: any) => (
        <div data-testid="card" className={className}>{children}</div>
    ),
    CardContent: ({ children, className }: any) => (
        <div className={className}>{children}</div>
    ),
    Badge: ({ children, className }: any) => (
        <span data-testid="badge" className={className}>{children}</span>
    ),
    Button: ({ children, className, variant, ...props }: any) => (
        <button data-variant={variant} className={className} {...props}>{children}</button>
    ),
}));

vi.mock('lucide-react', () => ({
    Check: ({ className }: any) => <span data-testid="check" className={className} />,
    ArrowRight: ({ className }: any) => <span data-testid="arrow-right" className={className} />,
    Sparkles: ({ className }: any) => <span data-testid="sparkles" className={className} />,
}));

vi.mock('@/components/TierComparison', () => ({
    TierComparison: ({ showPricing }: any) => (
        <div data-testid="tier-comparison" data-show-pricing={showPricing} />
    ),
}));

vi.mock('@/lib/config', () => ({
    MONETIZATION_ENABLED: true,
}));

vi.mock('@/components/InterestGate', () => ({
    InterestGate: ({ featureKey }: any) => (
        <div data-testid="interest-gate" data-feature={featureKey} />
    ),
}));

const mockTrackEvent = vi.fn();
vi.mock('@/lib/analytics/posthog', () => ({
    trackEvent: (...args: any[]) => mockTrackEvent(...args),
}));

import PreciosPage from '@/app/precios/page';

describe('PreciosPage', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        mockUseLang.mockReturnValue({ lang: 'es' as const, setLang: vi.fn() });
        mockUseAuth.mockReturnValue(mockAuth({ tier: 'anon' }));
    });

    it('renders 4 pricing tier cards', () => {
        render(<PreciosPage />);
        const cards = screen.getAllByTestId('card');
        expect(cards.length).toBe(4);
    });

    it('shows "Popular" badge on academic card', () => {
        render(<PreciosPage />);
        const badges = screen.getAllByTestId('badge');
        const popularBadge = badges.find(b => b.textContent === 'Popular');
        expect(popularBadge).toBeDefined();
    });

    it('free member card shows "Gratis" label', () => {
        render(<PreciosPage />);
        expect(screen.getByText('Gratis')).toBeDefined();
    });

    it('paid cards show promo prices from PRICING constants', () => {
        render(<PreciosPage />);
        // PRICING: essentials promo=31, academic=32, institutional=33
        expect(screen.getByText('$31')).toBeDefined();
        expect(screen.getByText('$32')).toBeDefined();
        expect(screen.getByText('$33')).toBeDefined();
    });

    it('CTA for free tier links to login when unauthenticated', () => {
        mockUseAuth.mockReturnValue(mockAuth({ tier: 'anon', isAuthenticated: false }));
        render(<PreciosPage />);
        const ctaLink = screen.getByText('Crear cuenta').closest('a');
        expect(ctaLink?.getAttribute('href')).toBe('/login');
    });

    it('paid tier CTAs generate trial checkout URLs', () => {
        render(<PreciosPage />);
        const trialButtons = screen.getAllByText('Prueba gratis 3 dias');
        expect(trialButtons.length).toBe(3); // essentials, academic, institutional
    });

    it('FAQ section renders 4 items', () => {
        render(<PreciosPage />);
        const faqTitle = screen.getByText('Preguntas frecuentes');
        expect(faqTitle).toBeDefined();
        // 4 FAQ questions
        expect(screen.getByText('\u00bfPuedo probar gratis antes de pagar?')).toBeDefined();
        expect(screen.getByText('\u00bfPuedo cambiar de plan en cualquier momento?')).toBeDefined();
        expect(screen.getByText('\u00bfQue metodos de pago aceptan?')).toBeDefined();
        expect(screen.getByText('\u00bfLos precios incluyen IVA?')).toBeDefined();
    });

    it('TierComparison rendered with showPricing prop', () => {
        render(<PreciosPage />);
        const tierComp = screen.getByTestId('tier-comparison');
        expect(tierComp.getAttribute('data-show-pricing')).toBe('true');
    });

    it('tracks pricing.page_viewed on mount', () => {
        render(<PreciosPage />);
        expect(mockTrackEvent).toHaveBeenCalledWith('pricing.page_viewed', {
            is_authenticated: false,
            tier: 'anon',
            monetization_enabled: true,
        });
    });

    it('tracks pricing.cta_clicked on CTA click', () => {
        render(<PreciosPage />);
        fireEvent.click(screen.getByText('Crear cuenta'));
        expect(mockTrackEvent).toHaveBeenCalledWith('pricing.cta_clicked', {
            tier_key: 'free_member',
            is_authenticated: false,
        });
    });
});
