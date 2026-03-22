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
    hasPaidAccess: (tier: string) =>
        ['essentials', 'academic', 'institutional', 'madfam'].includes(tier),
}));

// Default: monetization enabled (tests original behavior)
vi.mock('@/lib/config', () => ({
    MONETIZATION_ENABLED: true,
}));

// Mock PostHog
const mockTrackEvent = vi.fn();
vi.mock('@/lib/analytics/posthog', () => ({
    trackEvent: (...args: any[]) => mockTrackEvent(...args),
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
    Button: ({ children, className, ...props }: any) => (
        <button className={className} {...props}>{children}</button>
    ),
}));

vi.mock('lucide-react', () => ({
    Sparkles: ({ className }: any) => <span data-testid="sparkles" className={className} />,
    ArrowRight: ({ className }: any) => <span data-testid="arrow-right" className={className} />,
    Search: ({ className }: any) => <span data-testid="search" className={className} />,
    Download: ({ className }: any) => <span data-testid="download" className={className} />,
    Code: ({ className }: any) => <span data-testid="code" className={className} />,
    Users: ({ className }: any) => <span data-testid="users" className={className} />,
}));

import { ConversionBanner } from '@/components/ConversionBanner';

describe('ConversionBanner', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        mockUseLang.mockReturnValue({ lang: 'es' as const, setLang: vi.fn() });
    });

    it('renders for anon users', () => {
        mockUseAuth.mockReturnValue(mockAuth({ tier: 'anon' }));
        render(<ConversionBanner />);
        expect(screen.getByText('Prueba cualquier plan gratis por 3 dias')).toBeDefined();
    });

    it('renders for community users', () => {
        mockUseAuth.mockReturnValue(mockAuth({ tier: 'community', isAuthenticated: true }));
        render(<ConversionBanner />);
        expect(screen.getByText('Prueba cualquier plan gratis por 3 dias')).toBeDefined();
    });

    it('renders for free_member users', () => {
        mockUseAuth.mockReturnValue(mockAuth({ tier: 'free_member', isAuthenticated: true }));
        render(<ConversionBanner />);
        expect(screen.getByText('Prueba cualquier plan gratis por 3 dias')).toBeDefined();
    });

    it('does NOT render for essentials users', () => {
        mockUseAuth.mockReturnValue(mockAuth({ tier: 'essentials', isAuthenticated: true }));
        const { container } = render(<ConversionBanner />);
        expect(container.innerHTML).toBe('');
    });

    it('does NOT render for academic users', () => {
        mockUseAuth.mockReturnValue(mockAuth({ tier: 'academic', isAuthenticated: true }));
        const { container } = render(<ConversionBanner />);
        expect(container.innerHTML).toBe('');
    });

    it('CTA links to /precios', () => {
        mockUseAuth.mockReturnValue(mockAuth({ tier: 'anon' }));
        render(<ConversionBanner />);
        const link = screen.getByText('Ver planes').closest('a');
        expect(link?.getAttribute('href')).toBe('/precios');
    });

    it('renders English content', () => {
        mockUseLang.mockReturnValue({ lang: 'en' as const, setLang: vi.fn() });
        mockUseAuth.mockReturnValue(mockAuth({ tier: 'anon' }));
        render(<ConversionBanner />);
        expect(screen.getByText('Try any plan free for 3 days')).toBeDefined();
        expect(screen.getByText('View plans')).toBeDefined();
    });

    it('renders Nahuatl content', () => {
        mockUseLang.mockReturnValue({ lang: 'nah' as const, setLang: vi.fn() });
        mockUseAuth.mockReturnValue(mockAuth({ tier: 'anon' }));
        render(<ConversionBanner />);
        expect(screen.getByText('Xicyeyeco tlaxtlahuilli 3 tonalli')).toBeDefined();
    });

    it('tracks CTA click event', () => {
        mockUseAuth.mockReturnValue(mockAuth({ tier: 'anon' }));
        render(<ConversionBanner />);
        fireEvent.click(screen.getByText('Ver planes'));
        expect(mockTrackEvent).toHaveBeenCalledWith('conversion_banner.cta_clicked', {
            mode: 'pricing',
            href: '/precios',
        });
    });
});
