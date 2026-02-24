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
