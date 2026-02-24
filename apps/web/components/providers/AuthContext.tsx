'use client';

import { createContext, useContext, useMemo, type ReactNode } from 'react';
import { useAuth as useJanuaAuth } from '@janua/nextjs';

export type UserTier = 'anon' | 'free' | 'premium';

interface AuthState {
    isAuthenticated: boolean;
    tier: UserTier;
    loginUrl: string;
}

const DEFAULT_LOGIN_URL = '/api/auth/signin';

const defaultState: AuthState = {
    isAuthenticated: false,
    tier: 'anon',
    loginUrl: DEFAULT_LOGIN_URL,
};

const AuthContext = createContext<AuthState>(defaultState);

/**
 * Auth provider that bridges Janua SDK auth state into a simple
 * isAuthenticated/tier interface consumed by ExportDropdown et al.
 *
 * Falls back to raw JWT cookie reading if Janua is not configured
 * or the user isn't signed in via Janua.
 */
export function AuthProvider({ children }: { children: ReactNode }) {
    const januaAuth = useJanuaAuth();

    const state = useMemo<AuthState>(() => {
        // If Janua has an authenticated user, use that
        if (januaAuth?.isAuthenticated && januaAuth.user) {
            const claims = (januaAuth.user as unknown as Record<string, unknown>) ?? {};
            const tier = (claims.tier || claims.plan || 'free') as UserTier;
            const validTier = ['anon', 'free', 'premium'].includes(tier) ? tier : 'free';
            return {
                isAuthenticated: true,
                tier: validTier as UserTier,
                loginUrl: DEFAULT_LOGIN_URL,
            };
        }

        // Fallback: check for raw JWT cookie (backward compat)
        const token = getToken();
        if (!token) return defaultState;

        const jwtClaims = decodeJwtPayload(token);
        if (!jwtClaims) return defaultState;

        const tier = (jwtClaims.tier || jwtClaims.plan || 'free') as UserTier;
        const validTier = ['anon', 'free', 'premium'].includes(tier) ? tier : 'free';

        return {
            isAuthenticated: true,
            tier: validTier as UserTier,
            loginUrl: DEFAULT_LOGIN_URL,
        };
    }, [januaAuth]);

    return <AuthContext.Provider value={state}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
    return useContext(AuthContext);
}

function getToken(): string | null {
    if (typeof document !== 'undefined') {
        const match = document.cookie.match(/(?:^|;\s*)janua_token=([^;]*)/);
        if (match) return decodeURIComponent(match[1]);
    }
    if (typeof localStorage !== 'undefined') {
        return localStorage.getItem('janua_token');
    }
    return null;
}

function decodeJwtPayload(token: string): Record<string, unknown> | null {
    try {
        const parts = token.split('.');
        if (parts.length !== 3) return null;
        const payload = atob(parts[1].replace(/-/g, '+').replace(/_/g, '/'));
        return JSON.parse(payload);
    } catch {
        return null;
    }
}
