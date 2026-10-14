import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { mockAuth } from '../helpers/auth-mock';
import { makeLangMock, langState } from '../helpers/lang-mock';

const mockUseLang = makeLangMock();
vi.mock('@/components/providers/LanguageContext', () => ({
    useLang: () => mockUseLang(),
}));

const mockUseAuth = vi.fn(() => mockAuth({ tier: 'anon' }));
vi.mock('@/components/providers/AuthContext', () => ({
    useAuth: () => mockUseAuth(),
}));

vi.mock('@/lib/billing', () => ({
    getCheckoutUrl: vi.fn(
        (plan: string, _userId?: string, _returnUrl?: string) =>
            `https://app.dhan.am/checkout?plan=tezca_${plan}&product=tezca`
    ),
    hasPaidAccess: vi.fn(() => false),
}));

// Dhanam's catalog prices (owner ruling 2026-10-14): MXN 199 / 599 / 1,999
// before IVA, as the catalog lists them until it sends `grossPrices`.
type Price = { amount: number; ivaIncluded: boolean } | null;
const NET_PRICES: Record<string, Price> = {
    free: null,
    essentials: { amount: 19900, ivaIncluded: false },
    academic: { amount: 59900, ivaIncluded: false },
    institutional: { amount: 199900, ivaIncluded: false },
};
// The IVA-inclusive amounts Dhanam's checkout charges, from `grossPrices`.
const GROSS_PRICES: Record<string, Price> = {
    free: null,
    essentials: { amount: 23100, ivaIncluded: true },
    academic: { amount: 69500, ivaIncluded: true },
    institutional: { amount: 231900, ivaIncluded: true },
};
const mockUseTezcaPrices = vi.hoisted(() =>
    vi.fn(() => ({
        prices: null as Record<string, { amount: number; ivaIncluded: boolean } | null> | null,
        failed: false,
    })),
);
vi.mock('@/lib/dhanam-catalog', async (importOriginal) => ({
    ...(await importOriginal<typeof import('@/lib/dhanam-catalog')>()),
    useTezcaPrices: () => mockUseTezcaPrices(),
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
        mockUseLang.mockReturnValue(langState('es'));
        mockUseAuth.mockReturnValue(mockAuth({ tier: 'anon' }));
        mockUseTezcaPrices.mockReturnValue({ prices: NET_PRICES, failed: false });
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

    it('paid cards show the prices Dhanam charges, from its catalog', () => {
        render(<PreciosPage />);
        expect(screen.getByText('$199')).toBeDefined();
        expect(screen.getByText('$599')).toBeDefined();
        expect(screen.getByText('$1,999')).toBeDefined();
        // The 3-month promo is gone: Dhanam's checkout cannot charge it.
        expect(screen.queryByText('$31')).toBeNull();
        expect(screen.queryByText(/Primeros 3 meses/)).toBeNull();
    });

    it('labels a net catalog price "+ IVA", never a bare figure, and the FAQ says so', () => {
        render(<PreciosPage />);
        expect(screen.getAllByText('MXN/mes + IVA').length).toBe(3);
        expect(screen.getByText(/marcados «\+ IVA» no lo incluyen/)).toBeDefined();
        expect(screen.queryByText(/no incluyen IVA\. El impuesto se calcula/)).toBeNull();
    });

    it('shows the IVA-inclusive amount from grossPrices, labelled "IVA incluido"', () => {
        mockUseTezcaPrices.mockReturnValue({ prices: GROSS_PRICES, failed: false });
        render(<PreciosPage />);
        expect(screen.getByText('$231')).toBeDefined();
        expect(screen.getByText('$695')).toBeDefined();
        expect(screen.getByText('$2,319')).toBeDefined();
        expect(screen.queryByText('$199')).toBeNull();
        expect(screen.getAllByText('MXN/mes, IVA incluido').length).toBe(3);
        expect(screen.getByText(/Los precios mostrados incluyen IVA \(16%\)/)).toBeDefined();
        expect(screen.queryByText(/\+ IVA/)).toBeNull();
    });

    it('labels prices "VAT" in English', () => {
        mockUseLang.mockReturnValue(langState('en'));
        mockUseTezcaPrices.mockReturnValue({ prices: GROSS_PRICES, failed: false });
        render(<PreciosPage />);
        expect(screen.getAllByText('MXN/mo, VAT included').length).toBe(3);
        expect(screen.getByText(/Prices shown include VAT/)).toBeDefined();
    });

    it('never shows a typed price when the catalog is unreachable', () => {
        mockUseTezcaPrices.mockReturnValue({ prices: null, failed: true });
        render(<PreciosPage />);
        expect(screen.getAllByText('Precio al pagar').length).toBe(3);
        expect(screen.queryByText('$199')).toBeNull();
        expect(screen.getByText('El checkout cobra el total con IVA (16%) incluido.')).toBeDefined();
    });

    it('CTA for free tier links to login when unauthenticated', () => {
        mockUseAuth.mockReturnValue(mockAuth({ tier: 'anon', isAuthenticated: false }));
        render(<PreciosPage />);
        const ctaLink = screen.getByText('Crear cuenta').closest('a');
        expect(ctaLink?.getAttribute('href')).toBe('/login');
    });

    it('paid tier CTAs go to the hosted checkout, with no trial', () => {
        render(<PreciosPage />);
        const buttons = screen.getAllByText('Suscribirme');
        expect(buttons.length).toBe(3); // essentials, academic, institutional
        const href = buttons[0].closest('a')?.getAttribute('href') ?? '';
        expect(href).toContain('plan=tezca_essentials');
        expect(href).not.toContain('trial');
        expect(screen.queryByText(/Prueba gratis/)).toBeNull();
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
