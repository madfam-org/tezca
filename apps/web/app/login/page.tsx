'use client';

import { useState, useEffect } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
// Import SignIn/SignUp from @janua/nextjs (not @janua/ui): the nextjs wrapper is
// resolved at a version that carries the OIDC "Sign in with Janua" flow
// (enableJanuaSSO), and it sources the Janua client from the app-wide
// JanuaProvider, so no januaClient prop is needed.
import { SignIn, SignUp } from '@janua/nextjs';
import { useLang } from '@/components/providers/LanguageContext';
import { useAuth } from '@/components/providers/AuthContext';
import { trackEvent } from '@/lib/analytics/posthog';

const content = {
    es: {
        signIn: 'Iniciar sesión',
        signUp: 'Crear cuenta',
        switchToSignUp: '¿No tienes cuenta? Regístrate',
        switchToSignIn: '¿Ya tienes cuenta? Inicia sesión',
    },
    en: {
        signIn: 'Sign in',
        signUp: 'Create account',
        switchToSignUp: "Don't have an account? Sign up",
        switchToSignIn: 'Already have an account? Sign in',
    },
    nah: {
        signIn: 'Xicalaqui',
        signUp: 'Xicchihua motocaitl',
        switchToSignUp: '¿Ahmo ticpiya motocaitl? Ximomachiyoti',
        switchToSignIn: '¿Ye ticpiya motocaitl? Xicalaqui',
    },
};

type AuthMode = 'signin' | 'signup';

export default function LoginPage() {
    const { lang } = useLang();
    const t = content[lang];
    const { isAuthenticated } = useAuth();
    const router = useRouter();
    const searchParams = useSearchParams();
    const [mode, setMode] = useState<AuthMode>('signin');

    const redirectTo = searchParams.get('redirect') || '/cuenta';

    useEffect(() => {
        if (isAuthenticated) {
            router.replace(redirectTo);
        }
    }, [isAuthenticated, router, redirectTo]);

    useEffect(() => {
        trackEvent('auth.login_page_viewed', { mode });
    // eslint-disable-next-line react-hooks/exhaustive-deps -- track once on mount
    }, []);

    if (isAuthenticated) return null;

    const title = mode === 'signin' ? t.signIn : t.signUp;

    const afterAuth = () => {
        if (mode === 'signup') {
            trackEvent('funnel.account_created', {});
        }
        window.location.assign(redirectTo);
    };

    return (
        <div className="flex min-h-[70vh] items-center justify-center px-4 py-12">
            <div className="w-full max-w-md space-y-6">
                <div className="text-center">
                    <h1 className="text-2xl font-bold">{title}</h1>
                </div>

                <div className="rounded-lg border border-border bg-background p-6 shadow-sm">
                    {mode === 'signin' ? (
                        <SignIn
                            onSuccess={afterAuth}
                            redirectTo={redirectTo}
                            // Primary path: "Sign in with Janua" runs the OIDC/PKCE
                            // provider flow, minting a token with aud=tezca-api that
                            // the API accepts.
                            enableJanuaSSO
                            // client_id is a PUBLIC OIDC identifier (safe to commit);
                            // hardcoded fallback avoids depending on a build-time
                            // NEXT_PUBLIC_* being inlined. Redirect defaults to
                            // ${origin}/auth/callback, matching the seeded redirect_uri.
                            januaClientId={process.env.NEXT_PUBLIC_JANUA_CLIENT_ID || 'tezca-web'}
                            // The four social providers are not configured in Janua
                            // (live provider list is empty), so hide their dead buttons.
                            socialProviders={{ google: false, github: false, microsoft: false, apple: false }}
                            showRememberMe={false}
                        />
                    ) : (
                        <SignUp
                            onSuccess={afterAuth}
                            redirectTo={redirectTo}
                            socialProviders={{ google: false, github: false, microsoft: false, apple: false }}
                        />
                    )}

                    <div className="mt-4 text-center">
                        <button
                            onClick={() => {
                                const newMode = mode === 'signin' ? 'signup' : 'signin';
                                trackEvent('auth.mode_switched', { from: mode, to: newMode });
                                setMode(newMode);
                            }}
                            className="text-sm text-muted-foreground hover:text-foreground transition-colors"
                        >
                            {mode === 'signin' ? t.switchToSignUp : t.switchToSignIn}
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
}
