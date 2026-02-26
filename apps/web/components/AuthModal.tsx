'use client';

import { useState, useEffect, useCallback } from 'react';
import { useJanua } from '@janua/nextjs';
import { SignIn, SignUp } from '@janua/ui';
import { X } from 'lucide-react';
import { useLang } from '@/components/providers/LanguageContext';

const content = {
    es: {
        signIn: 'Iniciar sesión',
        signUp: 'Crear cuenta',
        close: 'Cerrar',
        switchToSignUp: '¿No tienes cuenta? Regístrate',
        switchToSignIn: '¿Ya tienes cuenta? Inicia sesión',
    },
    en: {
        signIn: 'Sign in',
        signUp: 'Create account',
        close: 'Close',
        switchToSignUp: "Don't have an account? Sign up",
        switchToSignIn: 'Already have an account? Sign in',
    },
    nah: {
        signIn: 'Xicalaqui',
        signUp: 'Xicchihua motocaitl',
        close: 'Xictlatzacua',
        switchToSignUp: '¿Ahmo ticpiya motocaitl? Ximomachiyoti',
        switchToSignIn: '¿Ye ticpiya motocaitl? Xicalaqui',
    },
};

type AuthMode = 'signin' | 'signup';

interface AuthModalProps {
    open: boolean;
    onClose: () => void;
    initialMode?: AuthMode;
}

export function AuthModal({ open, onClose, initialMode = 'signin' }: AuthModalProps) {
    const { lang } = useLang();
    const t = content[lang];
    const { client } = useJanua();
    const [mode, setMode] = useState<AuthMode>(initialMode);

    // Reset mode when modal opens
    useEffect(() => {
        if (open) setMode(initialMode);
    }, [open, initialMode]);

    const handleKeyDown = useCallback(
        (e: KeyboardEvent) => {
            if (e.key === 'Escape') onClose();
        },
        [onClose],
    );

    useEffect(() => {
        if (!open) return;
        document.addEventListener('keydown', handleKeyDown);
        document.body.style.overflow = 'hidden';
        return () => {
            document.removeEventListener('keydown', handleKeyDown);
            document.body.style.overflow = '';
        };
    }, [open, handleKeyDown]);

    if (!open) return null;

    const title = mode === 'signin' ? t.signIn : t.signUp;

    const afterAuth = () => {
        onClose();
        window.location.assign('/cuenta');
    };

    return (
        <div
            className="fixed inset-0 z-50 flex items-center justify-center"
            role="dialog"
            aria-modal="true"
            aria-label={title}
        >
            {/* Backdrop */}
            <div
                className="absolute inset-0 bg-black/50 backdrop-blur-sm"
                onClick={onClose}
                aria-hidden="true"
            />

            {/* Modal */}
            <div className="relative z-10 w-full max-w-md mx-4 bg-background rounded-lg border border-border shadow-lg p-6">
                <div className="flex items-center justify-between mb-4">
                    <h2 className="text-lg font-semibold">{title}</h2>
                    <button
                        onClick={onClose}
                        className="p-1.5 rounded-md hover:bg-muted transition-colors"
                        aria-label={t.close}
                    >
                        <X className="h-4 w-4" />
                    </button>
                </div>

                {mode === 'signin' ? (
                    <SignIn
                        januaClient={client}
                        afterSignIn={afterAuth}
                        redirectUrl="/cuenta"
                        socialProviders={{ google: true, github: true, microsoft: true, apple: true }}
                        showRememberMe={false}
                    />
                ) : (
                    <SignUp
                        januaClient={client}
                        afterSignUp={afterAuth}
                        redirectUrl="/cuenta"
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
    );
}
