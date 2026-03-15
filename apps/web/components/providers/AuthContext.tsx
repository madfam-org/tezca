'use client';

import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import { useAuth as useJanuaAuth, useJanua } from '@janua/nextjs';
import { identifyUser, resetUser } from '@/lib/analytics/posthog';

export type UserTier = 'anon' | 'free_member' | 'community' | 'essentials' | 'academic' | 'institutional' | 'madfam';

/** Normalize legacy/alias tier names from JWT claims to canonical form. */
const TIER_NORMALIZE: Record<string, UserTier> = {
    free: 'essentials',
    premium: 'academic',
    enterprise: 'academic',
    pro: 'academic',
    internal: 'madfam',
};

const VALID_TIERS: UserTier[] = ['anon', 'free_member', 'community', 'essentials', 'academic', 'institutional', 'madfam'];

interface AuthState {
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

const DEFAULT_LOGIN_URL = '/api/auth/signin';

const defaultState: AuthState = {
    isAuthenticated: false,
    tier: 'anon',
    effectiveTier: 'anon',
    trialTier: null,
    trialEndsAt: null,
    trialCcProvided: false,
    isOnTrial: false,
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

    const [trialState, setTrialState] = useState<{
        trialTier: UserTier | null;
        trialEndsAt: Date | null;
        trialCcProvided: boolean;
    }>({ trialTier: null, trialEndsAt: null, trialCcProvided: false });

    const handleSignOut = useCallback(() => {
        resetUser();
        client?.signOut?.();
        window.location.assign('/');
    }, [client]);

    const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

    useEffect(() => {
        if (!januaAuth?.isAuthenticated) return;
        const token = getToken();
        if (!token) return;

        fetch(`${API_BASE}/trial/status/`, {
            headers: { 'Authorization': `Bearer ${token}` },
        })
            .then(res => res.ok ? res.json() : null)
            .then(data => {
                if (data && data.active) {
                    setTrialState({
                        trialTier: data.trial_tier as UserTier,
                        trialEndsAt: data.trial_ends_at ? new Date(data.trial_ends_at) : null,
                        trialCcProvided: data.trial_cc_provided ?? false,
                    });
                }
            })
            .catch(() => {});
    }, [januaAuth?.isAuthenticated, API_BASE]);

    const state = useMemo<AuthState>(() => {
        function normalizeTier(raw: unknown): UserTier {
            const str = String(raw || 'free_member');
            const normalized = TIER_NORMALIZE[str] ?? str;
            return VALID_TIERS.includes(normalized as UserTier)
                ? (normalized as UserTier)
                : 'free_member';
        }

        const isTrialActive = trialState.trialTier !== null && trialState.trialEndsAt !== null && trialState.trialEndsAt > new Date();

        // If Janua has an authenticated user, use that
        if (januaAuth?.isAuthenticated && januaAuth.user) {
            const claims = (januaAuth.user as unknown as Record<string, unknown>) ?? {};
            const baseTier = normalizeTier(claims.tier || claims.plan);
            return {
                isAuthenticated: true,
                tier: baseTier,
                effectiveTier: isTrialActive ? trialState.trialTier! : baseTier,
                trialTier: trialState.trialTier,
                trialEndsAt: trialState.trialEndsAt,
                trialCcProvided: trialState.trialCcProvided,
                isOnTrial: isTrialActive,
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

        const baseTier = normalizeTier(jwtClaims.tier || jwtClaims.plan);
        return {
            isAuthenticated: true,
            tier: baseTier,
            effectiveTier: isTrialActive ? trialState.trialTier! : baseTier,
            trialTier: trialState.trialTier,
            trialEndsAt: trialState.trialEndsAt,
            trialCcProvided: trialState.trialCcProvided,
            isOnTrial: isTrialActive,
            loginUrl: DEFAULT_LOGIN_URL,
            userId: (jwtClaims.sub || jwtClaims.user_id || null) as string | null,
            email: (jwtClaims.email || null) as string | null,
            name: (jwtClaims.name || jwtClaims.full_name || null) as string | null,
            signOut: handleSignOut,
        };
    }, [januaAuth, handleSignOut, trialState]);

    const prevAuthRef = useRef(false);
    useEffect(() => {
        if (state.isAuthenticated && !prevAuthRef.current && state.userId) {
            identifyUser(state.userId, { email: state.email, name: state.name, tier: state.tier });
        }
        prevAuthRef.current = state.isAuthenticated;
    }, [state.isAuthenticated, state.userId, state.email, state.name, state.tier]);

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
