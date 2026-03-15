/**
 * Shared auth mock helper for Vitest.
 *
 * Provides a canonical default AuthState and a factory function to create
 * overrides, eliminating duplicated auth mock definitions across test files.
 *
 * Usage:
 *   import { defaultAuthState, mockAuth } from '../helpers/auth-mock';
 *
 *   // Use the default (anon, unauthenticated):
 *   vi.mocked(useAuth).mockReturnValue(defaultAuthState);
 *
 *   // Override specific fields:
 *   vi.mocked(useAuth).mockReturnValue(mockAuth({ isAuthenticated: true, tier: 'academic' }));
 */
import { vi } from 'vitest';

export type UserTier = 'anon' | 'free_member' | 'community' | 'essentials' | 'academic' | 'institutional' | 'madfam';

export interface AuthState {
    isAuthenticated: boolean;
    tier: UserTier;
    effectiveTier: UserTier;
    trialTier: UserTier | null;
    trialEndsAt: Date | null;
    trialCcProvided: boolean;
    isOnTrial: boolean;
    loginUrl: string;
    userId: string | null;
    email: string | null;
    name: string | null;
    signOut: () => void;
}

export const defaultAuthState: AuthState = {
    isAuthenticated: false,
    tier: 'anon',
    effectiveTier: 'anon',
    trialTier: null,
    trialEndsAt: null,
    trialCcProvided: false,
    isOnTrial: false,
    loginUrl: '/api/auth/signin',
    userId: null,
    email: null,
    name: null,
    signOut: vi.fn(),
};

/**
 * Create an AuthState with optional overrides merged onto the defaults.
 * Always returns a fresh `signOut` mock unless explicitly overridden.
 */
export function mockAuth(overrides: Partial<AuthState> = {}): AuthState {
    const base = {
        ...defaultAuthState,
        signOut: vi.fn(),
        ...overrides,
    };
    // If tier was overridden but effectiveTier was not, default effectiveTier to tier
    if (overrides.tier && !overrides.effectiveTier) {
        base.effectiveTier = overrides.tier;
    }
    return base;
}
