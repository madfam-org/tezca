'use client';

import { useState, useEffect } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { useJanua } from '@janua/nextjs';
import { SignIn, SignUp } from '@janua/ui';
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
    const { client } = useJanua();
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
                            januaClient={client}
                            afterSignIn={afterAuth}
                            redirectUrl={redirectTo}
                            socialProviders={{ google: true, github: true, microsoft: true, apple: true }}
                            showRememberMe={false}
                        />
                    ) : (
                        <SignUp
                            januaClient={client}
                            afterSignUp={afterAuth}
                            redirectUrl={redirectTo}
                            socialProviders={{ google: true, github: true, microsoft: true, apple: true }}
                        />
                    )}

                    <div className="mt-4 text-center">
                        <button
                            onClick={() => setMode(mode === 'signin' ? 'signup' : 'signin')}
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
