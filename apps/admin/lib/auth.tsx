"use client";

import { type ComponentProps, useEffect, useLayoutEffect, useMemo } from "react";
import { setTokenSource } from "./api";
import { serverSafeJanuaConfig } from "./janua-config";

// Re-export Janua components for use across the app
export { UserButton, SignInForm, useJanua, useAuth } from "@janua/nextjs";

// Import for internal use
import { JanuaProvider as BaseJanuaProvider, useJanua } from "@janua/nextjs";

/**
 * App-wide `<JanuaProvider>`. The root layout is a server component, so the
 * server/browser decision happens here, at render time in this client module:
 * on the server the client is built with `autoRefreshTokens: false` (see
 * `lib/janua-config.ts` — the SDK leaks one interval per server render), in
 * the browser the layout's config (`autoRefreshTokens: true`) passes through
 * unchanged.
 */
export function JanuaProvider({
    config,
    ...rest
}: ComponentProps<typeof BaseJanuaProvider>) {
    const effectiveConfig = useMemo(() => serverSafeJanuaConfig(config), [config]);
    return <BaseJanuaProvider {...rest} config={effectiveConfig} />;
}

/**
 * AdminAuthBridge — transparent wrapper that wires the Janua SDK's
 * access-token getter into the api.ts fetcher via setTokenSource().
 *
 * On mount, checks the local /api/auth/me endpoint (which validates the
 * janua-session cookie server-side) to hydrate SDK state without making
 * a direct browser XHR to auth.madfam.io (which fails with CORS).
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
            return;
        }

        // If no SSO bridge cookie, check for an existing server-side session.
        // This avoids the Janua SDK's built-in /auth/me XHR that fails with CORS.
        const hasToken = !!localStorage.getItem("janua_access_token");
        if (!hasToken) {
            fetch("/api/auth/me")
                .then((res) => {
                    if (!res.ok) return;
                    return res.json();
                })
                .then((data) => {
                    if (data?.authenticated && data.access_token) {
                        localStorage.setItem("janua_access_token", data.access_token);
                        if (data.refresh_token) {
                            localStorage.setItem("janua_refresh_token", data.refresh_token);
                        }
                        if (data.expires_at) {
                            localStorage.setItem(
                                "janua_token_expires_at",
                                String(data.expires_at)
                            );
                        }
                        // Reload so JanuaProvider picks up the hydrated tokens
                        window.location.reload();
                    }
                })
                .catch(() => {
                    // session check failed — user will see sign-in page
                });
        }
    }, []);

    useLayoutEffect(() => {
        if (client) {
            setTokenSource(() => client.getAccessToken());
        }
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
