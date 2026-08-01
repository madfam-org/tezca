'use client';

import { Suspense, useEffect } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useAuth } from '@janua/nextjs';

/**
 * Janua OIDC/PKCE callback landing (redirect_uri = https://tezca.mx/auth/callback,
 * the redirect registered for the `tezca-web` OIDC client).
 *
 * The JanuaProvider mounted in app/layout.tsx detects the `?code=&state=` on load
 * and performs the PKCE token exchange automatically (see @janua/nextjs provider:
 * validateState → handleOAuthCallback → strips the query). This page only reflects
 * status and forwards the user on: to their intended destination once the SDK
 * reports authenticated, or back to /login on an OAuth error.
 */
function CallbackContent() {
    const router = useRouter();
    const searchParams = useSearchParams();
    const { isAuthenticated, isLoading } = useAuth();

    const error = searchParams.get('error');
    const errorDescription = searchParams.get('error_description');
    // The provider strips the query after exchanging, so `state` may already be
    // gone; fall back to the account home.
    const redirectTo = searchParams.get('state') || '/cuenta';

    useEffect(() => {
        if (!error) return;
        const timer = setTimeout(() => {
            router.replace(`/login?error=${encodeURIComponent(errorDescription || error)}`);
        }, 1500);
        return () => clearTimeout(timer);
    }, [error, errorDescription, router]);

    useEffect(() => {
        if (!error && !isLoading && isAuthenticated) {
            router.replace(redirectTo);
        }
    }, [error, isLoading, isAuthenticated, redirectTo, router]);

    return (
        <div className="flex min-h-[70vh] items-center justify-center px-4 py-12">
            <div className="text-center">
                {error ? (
                    <>
                        <h2 className="text-xl font-semibold">No se pudo iniciar sesión</h2>
                        <p className="mt-2 text-sm text-muted-foreground">
                            Regresando al inicio de sesión…
                        </p>
                    </>
                ) : (
                    <>
                        <div className="mx-auto mb-4 h-10 w-10 animate-spin rounded-full border-4 border-primary border-t-transparent" />
                        <h2 className="text-xl font-semibold">Completando inicio de sesión…</h2>
                        <p className="mt-2 text-sm text-muted-foreground">Verificando tus credenciales</p>
                    </>
                )}
            </div>
        </div>
    );
}

export default function AuthCallbackPage() {
    return (
        <Suspense
            fallback={
                <div className="flex min-h-[70vh] items-center justify-center">
                    <div className="h-10 w-10 animate-spin rounded-full border-4 border-primary border-t-transparent" />
                </div>
            }
        >
            <CallbackContent />
        </Suspense>
    );
}
