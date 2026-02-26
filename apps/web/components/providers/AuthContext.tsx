'use client';

import { createContext, useCallback, useContext, useMemo, type ReactNode } from 'react';
import { useAuth as useJanuaAuth, useJanua } from '@janua/nextjs';

export type UserTier = 'anon' | 'free' | 'premium';

interface AuthState {
    isAuthenticated: boolean;
    tier: UserTier;
    loginUrl: string;
    userId: string | null;
    email: string | null;
    name: string | null;
    signOut: () => void;
}

const DEFAULT_LOGIN_URL = '/api/auth/signin';

const defaultState: AuthState = {
    isAuthenticated: false,
    tier: 'anon',
    loginUrl: DEFAULT_LOGIN_URL,
    userId: null,
    email: null,
    name: null,
    signOut: () => {},
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
    const { client } = useJanua();

    const handleSignOut = useCallback(() => {
        client?.signOut?.();
        window.location.assign('/');
    }, [client]);

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
                userId: (claims.sub || claims.user_id || null) as string | null,
                email: (claims.email || null) as string | null,
                name: (claims.name || claims.full_name || null) as string | null,
                signOut: handleSignOut,
            };
        }

        // Fallback: check for raw JWT cookie (backward compat)
        const token = getToken();
        if (!token) return { ...defaultState, signOut: handleSignOut };

        const jwtClaims = decodeJwtPayload(token);
        if (!jwtClaims) return { ...defaultState, signOut: handleSignOut };

        const tier = (jwtClaims.tier || jwtClaims.plan || 'free') as UserTier;
        const validTier = ['anon', 'free', 'premium'].includes(tier) ? tier : 'free';

        return {
            isAuthenticated: true,
            tier: validTier as UserTier,
            loginUrl: DEFAULT_LOGIN_URL,
            userId: (jwtClaims.sub || jwtClaims.user_id || null) as string | null,
            email: (jwtClaims.email || null) as string | null,
            name: (jwtClaims.name || jwtClaims.full_name || null) as string | null,
            signOut: handleSignOut,
        };
    }, [januaAuth, handleSignOut]);

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
