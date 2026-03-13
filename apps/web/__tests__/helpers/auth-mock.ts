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
 *   vi.mocked(useAuth).mockReturnValue(mockAuth({ isAuthenticated: true, tier: 'pro' }));
 */
import { vi } from 'vitest';

export type UserTier = 'anon' | 'essentials' | 'community' | 'pro' | 'madfam';

export interface AuthState {
    isAuthenticated: boolean;
    tier: UserTier;
    loginUrl: string;
    userId: string | null;
    email: string | null;
    name: string | null;
    signOut: () => void;
}

export const defaultAuthState: AuthState = {
    isAuthenticated: false,
    tier: 'anon',
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
    return {
        ...defaultAuthState,
        signOut: vi.fn(),
        ...overrides,
    };
}
