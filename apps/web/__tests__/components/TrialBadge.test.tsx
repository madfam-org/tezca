import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { mockAuth } from '../helpers/auth-mock';

const mockUseLang = vi.fn(() => ({ lang: 'es' as const, setLang: vi.fn() }));
vi.mock('@/components/providers/LanguageContext', () => ({
    useLang: (...args: any[]) => mockUseLang(...args),
}));

const mockUseAuth = vi.fn(() => mockAuth({ isOnTrial: false }));
vi.mock('@/components/providers/AuthContext', () => ({
    useAuth: (...args: any[]) => mockUseAuth(...args),
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

vi.mock('lucide-react', () => ({
    Clock: ({ className }: any) => <span data-testid="clock" className={className} />,
}));

import { TrialBadge } from '@/components/TrialBadge';

describe('TrialBadge', () => {
    beforeEach(() => {
        vi.useFakeTimers();
        vi.setSystemTime(new Date('2026-03-10T12:00:00Z'));
        vi.clearAllMocks();
        mockUseLang.mockReturnValue({ lang: 'es' as const, setLang: vi.fn() });
    });

    afterEach(() => {
        vi.useRealTimers();
    });

    it('returns null when isOnTrial is false', () => {
        mockUseAuth.mockReturnValue(mockAuth({ isOnTrial: false }));
        const { container } = render(<TrialBadge />);
        expect(container.innerHTML).toBe('');
    });

    it('returns null when trialEndsAt is null', () => {
        mockUseAuth.mockReturnValue(mockAuth({ isOnTrial: true, trialEndsAt: null }));
        const { container } = render(<TrialBadge />);
        expect(container.innerHTML).toBe('');
    });

    it('shows days+hours format when >24h remaining', () => {
        const trialEndsAt = new Date('2026-03-12T18:00:00Z'); // 2d 6h from now
        mockUseAuth.mockReturnValue(mockAuth({
            isOnTrial: true,
            trialEndsAt,
            trialTier: 'essentials',
        }));
        render(<TrialBadge />);
        expect(screen.getByText(/Prueba: 2d 6h/)).toBeDefined();
    });

    it('shows hours-only format when <24h remaining', () => {
        const trialEndsAt = new Date('2026-03-10T22:00:00Z'); // 10h from now
        mockUseAuth.mockReturnValue(mockAuth({
            isOnTrial: true,
            trialEndsAt,
            trialTier: 'essentials',
        }));
        render(<TrialBadge />);
        expect(screen.getByText(/Prueba: 10h/)).toBeDefined();
    });

    it('has animate-pulse class when <24h remaining', () => {
        const trialEndsAt = new Date('2026-03-10T22:00:00Z'); // 10h
        mockUseAuth.mockReturnValue(mockAuth({
            isOnTrial: true,
            trialEndsAt,
            trialTier: 'essentials',
        }));
        const { container } = render(<TrialBadge />);
        const link = container.querySelector('a');
        expect(link?.className).toContain('animate-pulse');
    });

    it('links to /precios', () => {
        const trialEndsAt = new Date('2026-03-12T12:00:00Z');
        mockUseAuth.mockReturnValue(mockAuth({
            isOnTrial: true,
            trialEndsAt,
            trialTier: 'academic',
        }));
        render(<TrialBadge />);
        const link = screen.getByRole('link');
        expect(link.getAttribute('href')).toBe('/precios');
    });

    it('shows "Trial" in English', () => {
        mockUseLang.mockReturnValue({ lang: 'en' as const, setLang: vi.fn() });
        const trialEndsAt = new Date('2026-03-12T12:00:00Z');
        mockUseAuth.mockReturnValue(mockAuth({
            isOnTrial: true,
            trialEndsAt,
            trialTier: 'essentials',
        }));
        render(<TrialBadge />);
        expect(screen.getByText(/Trial: 2d 0h/)).toBeDefined();
    });

    it('shows "Yeyecoliztli" in Nahuatl', () => {
        mockUseLang.mockReturnValue({ lang: 'nah' as const, setLang: vi.fn() });
        const trialEndsAt = new Date('2026-03-12T12:00:00Z');
        mockUseAuth.mockReturnValue(mockAuth({
            isOnTrial: true,
            trialEndsAt,
            trialTier: 'essentials',
        }));
        render(<TrialBadge />);
        expect(screen.getByText(/Yeyecoliztli: 2d 0h/)).toBeDefined();
    });

    it('tracks trial_badge.clicked on click', () => {
        const trialEndsAt = new Date('2026-03-12T18:00:00Z'); // 2d 6h
        mockUseAuth.mockReturnValue(mockAuth({
            isOnTrial: true,
            trialEndsAt,
            trialTier: 'essentials',
        }));
        render(<TrialBadge />);
        fireEvent.click(screen.getByRole('link'));
        expect(mockTrackEvent).toHaveBeenCalledWith('trial_badge.clicked', {
            trial_tier: 'essentials',
            days_remaining: 2,
            is_urgent: false,
        });
    });
});
