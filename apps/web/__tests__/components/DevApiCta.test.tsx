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
    ArrowRight: ({ className }: any) => <span data-testid="arrow-right" className={className} />,
    Code2: ({ className }: any) => <span data-testid="code2" className={className} />,
}));

import { DevApiCta } from '@/components/DevApiCta';

describe('DevApiCta', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        mockUseLang.mockReturnValue({ lang: 'es' as const, setLang: vi.fn() });
    });

    it('renders for anon users', () => {
        mockUseAuth.mockReturnValue(mockAuth({ tier: 'anon' }));
        render(<DevApiCta />);
        expect(screen.getByText('Obt\u00e9n acceso a la API')).toBeDefined();
    });

    it('renders for free_member users', () => {
        mockUseAuth.mockReturnValue(mockAuth({ tier: 'free_member', isAuthenticated: true }));
        render(<DevApiCta />);
        expect(screen.getByText('Obt\u00e9n acceso a la API')).toBeDefined();
    });

    it('does NOT render for paid users', () => {
        mockUseAuth.mockReturnValue(mockAuth({ tier: 'academic', isAuthenticated: true }));
        const { container } = render(<DevApiCta />);
        expect(container.innerHTML).toBe('');
    });

    it('CTA links to /login?redirect=/precios for anon users', () => {
        mockUseAuth.mockReturnValue(mockAuth({ tier: 'anon' }));
        render(<DevApiCta />);
        const link = screen.getByText('Ver planes').closest('a');
        expect(link?.getAttribute('href')).toBe('/login?redirect=/precios');
    });

    it('CTA links to /precios for authenticated users', () => {
        mockUseAuth.mockReturnValue(mockAuth({ tier: 'free_member', isAuthenticated: true }));
        render(<DevApiCta />);
        const link = screen.getByText('Ver planes').closest('a');
        expect(link?.getAttribute('href')).toBe('/precios');
    });

    it('tracks dev_docs.cta_clicked on click', () => {
        mockUseAuth.mockReturnValue(mockAuth({ tier: 'anon' }));
        render(<DevApiCta />);
        fireEvent.click(screen.getByText('Ver planes'));
        expect(mockTrackEvent).toHaveBeenCalledWith('dev_docs.cta_clicked', { tier: 'anon' });
    });

    it('renders English content', () => {
        mockUseLang.mockReturnValue({ lang: 'en' as const, setLang: vi.fn() });
        mockUseAuth.mockReturnValue(mockAuth({ tier: 'anon' }));
        render(<DevApiCta />);
        expect(screen.getByText('Get API access')).toBeDefined();
    });
});
