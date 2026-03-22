import { render, screen } from '@testing-library/react';
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

vi.mock('@/lib/config', () => ({
    MONETIZATION_ENABLED: false,
}));

const mockTrackEvent = vi.fn();
vi.mock('@/lib/analytics/posthog', () => ({
    trackEvent: (...args: any[]) => mockTrackEvent(...args),
}));

vi.mock('@/components/InterestGate', () => ({
    InterestGate: ({ featureKey, variant }: any) => (
        <div data-testid="interest-gate" data-feature={featureKey} data-variant={variant} />
    ),
}));

vi.mock('@/components/TierGate', () => ({
    TierGate: ({ requiredTier, variant }: any) => (
        <div data-testid="tier-gate" data-tier={requiredTier} data-variant={variant} />
    ),
}));

import { GraphTierMessage } from '@/components/graph/GraphTierMessage';

describe('GraphTierMessage', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        mockUseLang.mockReturnValue({ lang: 'es' as const, setLang: vi.fn() });
    });

    it('renders InterestGate for anon users when monetization disabled', () => {
        mockUseAuth.mockReturnValue(mockAuth({ tier: 'anon' }));
        render(<GraphTierMessage />);
        const gate = screen.getByTestId('interest-gate');
        expect(gate.getAttribute('data-feature')).toBe('graph_api');
        expect(gate.getAttribute('data-variant')).toBe('inline');
    });

    it('returns null for institutional users', () => {
        mockUseAuth.mockReturnValue(mockAuth({ tier: 'institutional', isAuthenticated: true }));
        const { container } = render(<GraphTierMessage />);
        expect(container.innerHTML).toBe('');
    });

    it('returns null for madfam users', () => {
        mockUseAuth.mockReturnValue(mockAuth({ tier: 'madfam', isAuthenticated: true }));
        const { container } = render(<GraphTierMessage />);
        expect(container.innerHTML).toBe('');
    });

    it('tracks graph_tier_message.shown for non-institutional users', () => {
        mockUseAuth.mockReturnValue(mockAuth({ tier: 'academic', isAuthenticated: true }));
        render(<GraphTierMessage />);
        expect(mockTrackEvent).toHaveBeenCalledWith('graph_tier_message.shown', {
            tier: 'academic',
            feature_key: 'graph_api',
        });
    });

    it('does NOT track for institutional users', () => {
        mockUseAuth.mockReturnValue(mockAuth({ tier: 'institutional', isAuthenticated: true }));
        render(<GraphTierMessage />);
        expect(mockTrackEvent).not.toHaveBeenCalled();
    });
});
