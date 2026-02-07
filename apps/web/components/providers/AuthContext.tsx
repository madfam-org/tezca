'use client';

import { createContext, useContext, useState, type ReactNode } from 'react';

export type UserTier = 'anon' | 'free' | 'premium';

interface AuthState {
    isAuthenticated: boolean;
    tier: UserTier;
    loginUrl: string;
}

const DEFAULT_LOGIN_URL = process.env.NEXT_PUBLIC_JANUA_LOGIN_URL || '/auth/login';

const defaultState: AuthState = {
    isAuthenticated: false,
    tier: 'anon',
    loginUrl: DEFAULT_LOGIN_URL,
};

const AuthContext = createContext<AuthState>(defaultState);

function resolveAuthState(): AuthState {
    const token = getToken();
    if (!token) return defaultState;

    const claims = decodeJwtPayload(token);
    if (!claims) return defaultState;

    const tier = (claims.tier || claims.plan || 'free') as UserTier;
    const validTier = ['anon', 'free', 'premium'].includes(tier) ? tier : 'free';

    return {
        isAuthenticated: true,
        tier: validTier as UserTier,
        loginUrl: DEFAULT_LOGIN_URL,
    };
}

/**
 * Lightweight auth provider that checks for a Janua JWT in cookies/localStorage.
 * Does NOT manage the auth flow — Janua handles that.
 * Used by ExportDropdown to conditionally show format access.
 */
export function AuthProvider({ children }: { children: ReactNode }) {
    const [state] = useState<AuthState>(resolveAuthState);

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
