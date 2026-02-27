"use client";

import { useEffect } from "react";
import { setTokenSource } from "./api";

// Re-export Janua components for use across the app
export { JanuaProvider, UserButton, SignInForm, useJanua, useAuth } from "@janua/nextjs";

// Import for internal use
import { useJanua } from "@janua/nextjs";

/**
 * AdminAuthBridge — transparent wrapper that wires the Janua SDK's
 * access-token getter into the api.ts fetcher via setTokenSource().
 * Renders children unchanged.
 */
export function AdminAuthBridge({ children }: { children: React.ReactNode }) {
    const { client } = useJanua();

    // Hydrate SDK localStorage from SSO token bridge cookie (set by /api/auth/callback)
    useEffect(() => {
        if (typeof document === "undefined") return;
        const match = document.cookie.match(/(?:^|;\s*)janua-sso-tokens=([^;]*)/);
        if (match) {
            try {
                const tokens = JSON.parse(decodeURIComponent(match[1]));
                localStorage.setItem("janua_access_token", tokens.access_token);
                if (tokens.refresh_token) {
                    localStorage.setItem("janua_refresh_token", tokens.refresh_token);
                }
                if (tokens.expires_at) {
                    localStorage.setItem("janua_token_expires_at", String(tokens.expires_at));
                }
            } catch {
                // ignore malformed cookie
            }
            // Delete the bridge cookie
            document.cookie = "janua-sso-tokens=; path=/; max-age=0";
            // Reload so JanuaProvider picks up the new tokens
            window.location.reload();
        }
    }, []);

    useEffect(() => {
        if (client) {
            setTokenSource(() => client.getAccessToken());
        } else {
            setTokenSource(null);
        }
        return () => {
            setTokenSource(null);
        };
    }, [client]);

    return <>{children}</>;
}

/**
 * useAdminAuth — convenience hook wrapping Janua auth state.
 */
export function useAdminAuth() {
    const janua = useJanua();
    return {
        isAuthenticated: !!janua?.user,
        isLoading: janua?.isLoading ?? false,
        user: janua?.user ?? null,
        signOut: janua?.signOut ?? null,
    };
}
