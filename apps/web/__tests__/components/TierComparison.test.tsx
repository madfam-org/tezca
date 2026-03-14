import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { mockAuth } from '../helpers/auth-mock';

const mockUseLang = vi.fn(() => ({ lang: 'es' as const, setLang: vi.fn() }));
vi.mock('@/components/providers/LanguageContext', () => ({
    useLang: (...args: any[]) => mockUseLang(...args),
}));

const mockUseAuth = vi.fn(() => mockAuth({
    tier: 'essentials',
    userId: 'user-123',
    isAuthenticated: true,
}));
vi.mock('@/components/providers/AuthContext', () => ({
    useAuth: (...args: any[]) => mockUseAuth(...args),
}));

vi.mock('@/lib/billing', () => ({
    getCheckoutUrl: vi.fn(
        (tier: string, userId?: string, _returnUrl?: string) =>
            `https://dhanam.madfam.io/checkout?tier=${tier}&uid=${userId ?? ''}`
    ),
}));

vi.mock('next/link', () => ({
    default: ({ children, href, ...props }: any) => (
        <a href={href} {...props}>
            {children}
        </a>
    ),
}));

vi.mock('@tezca/ui', () => ({
    Card: ({ children, className }: any) => (
        <div data-testid="card" className={className}>
            {children}
        </div>
    ),
    CardContent: ({ children, className }: any) => (
        <div className={className}>{children}</div>
    ),
    Badge: ({ children, className, variant }: any) => (
        <span data-variant={variant} className={className}>
            {children}
        </span>
    ),
    Button: ({ children, className, ...props }: any) => (
        <button className={className} {...props}>
            {children}
        </button>
    ),
}));

import { TierComparison } from '@/components/TierComparison';

describe('TierComparison', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        mockUseLang.mockReturnValue({ lang: 'es' as const, setLang: vi.fn() });
        mockUseAuth.mockReturnValue(mockAuth({
            tier: 'essentials',
            userId: 'user-123',
            isAuthenticated: true,
        }));
    });

    it('renders compact mode with 4 tier columns', () => {
        const { container } = render(<TierComparison compact />);
        const grid = container.querySelector('.grid.grid-cols-4');
        expect(grid).toBeTruthy();
        expect(screen.getByText('Community')).toBeDefined();
        expect(screen.getByText('Essentials')).toBeDefined();
        expect(screen.getByText('Academic')).toBeDefined();
        expect(screen.getByText('Institutional')).toBeDefined();
    });

    it('renders full mode with feature comparison table (desktop)', () => {
        const { container } = render(<TierComparison />);
        const table = container.querySelector('table');
        expect(table).toBeTruthy();
        // Full mode renders both desktop table and mobile cards simultaneously
        // (CSS handles visibility), so feature labels appear multiple times.
        // Verify all 10 feature rows exist in the desktop table.
        const rows = table!.querySelectorAll('tbody tr');
        expect(rows.length).toBe(10);
        // Verify specific feature labels are present (using getAllByText since
        // they also appear in the mobile card section)
        expect(screen.getAllByText('Resultados por página').length).toBeGreaterThanOrEqual(1);
        expect(screen.getAllByText('Descargar TXT').length).toBeGreaterThanOrEqual(1);
        expect(screen.getAllByText('Descargar PDF/JSON').length).toBeGreaterThanOrEqual(1);
        expect(screen.getAllByText('Acceso API').length).toBeGreaterThanOrEqual(1);
        expect(screen.getAllByText('Descarga masiva').length).toBeGreaterThanOrEqual(1);
        expect(screen.getAllByText('Webhooks').length).toBeGreaterThanOrEqual(1);
        expect(screen.getAllByText('Análisis de búsqueda').length).toBeGreaterThanOrEqual(1);
    });

    it('renders mobile stacked cards in full mode', () => {
        render(<TierComparison />);
        const cards = screen.getAllByTestId('card');
        expect(cards.length).toBe(4);
    });

    it('highlights current tier with ring styling in compact mode', () => {
        mockUseAuth.mockReturnValue(mockAuth({
            tier: 'community',
            userId: 'user-123',
            isAuthenticated: true,
        }));
        const { container } = render(<TierComparison compact />);
        const highlighted = container.querySelector('.ring-1.ring-primary\\/30');
        expect(highlighted).toBeTruthy();
        expect(highlighted!.textContent).toContain('Community');
    });

    it('shows "Tu plan" badge for current tier', () => {
        mockUseAuth.mockReturnValue(mockAuth({
            tier: 'community',
            userId: 'user-123',
            isAuthenticated: true,
        }));
        render(<TierComparison />);
        const currentBadges = screen.getAllByText('Tu plan');
        // Appears in both desktop table header and mobile card
        expect(currentBadges.length).toBe(2);
    });

    it('shows upgrade buttons for higher tiers only', () => {
        mockUseAuth.mockReturnValue(mockAuth({
            tier: 'essentials',
            userId: 'user-123',
            isAuthenticated: true,
        }));
        render(<TierComparison />);
        // Essentials is rank 2, so upgrade buttons appear for academic and institutional
        // Desktop tfoot: 2 buttons + Mobile cards: 2 buttons = 4 total
        const upgradeButtons = screen.getAllByText('Mejora tu plan');
        expect(upgradeButtons.length).toBe(4);
    });

    it('hides upgrade button for current and lower tiers (isDowngrade)', () => {
        mockUseAuth.mockReturnValue(mockAuth({
            tier: 'institutional',
            userId: 'user-123',
            isAuthenticated: true,
        }));
        render(<TierComparison />);
        // All tiers are at or below institutional rank, so no upgrade buttons should render
        const upgradeButtons = screen.queryAllByText('Mejora tu plan');
        expect(upgradeButtons.length).toBe(0);
    });

    it('shows "Gratis" badge for community tier', () => {
        render(<TierComparison />);
        const freeBadges = screen.getAllByText('Gratis');
        // Desktop table header + mobile card = 2
        expect(freeBadges.length).toBe(2);
    });

    it('shows "Popular" badge for academic tier', () => {
        render(<TierComparison />);
        const popularBadges = screen.getAllByText('Popular');
        // Desktop table header + mobile card = 2
        expect(popularBadges.length).toBe(2);
    });
});
