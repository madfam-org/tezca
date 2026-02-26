'use client';

import { useEffect, useCallback } from 'react';
import { useJanua } from '@janua/nextjs';
import { SignIn } from '@janua/ui';
import { X } from 'lucide-react';
import { useLang } from '@/components/providers/LanguageContext';

const content = {
    es: { title: 'Iniciar sesión', close: 'Cerrar' },
    en: { title: 'Sign in', close: 'Close' },
    nah: { title: 'Xicalaqui', close: 'Xictlatzacua' },
};

interface AuthModalProps {
    open: boolean;
    onClose: () => void;
}

export function AuthModal({ open, onClose }: AuthModalProps) {
    const { lang } = useLang();
    const t = content[lang];
    const { client } = useJanua();

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

    return (
        <div
            className="fixed inset-0 z-50 flex items-center justify-center"
            role="dialog"
            aria-modal="true"
            aria-label={t.title}
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
                    <h2 className="text-lg font-semibold">{t.title}</h2>
                    <button
                        onClick={onClose}
                        className="p-1.5 rounded-md hover:bg-muted transition-colors"
                        aria-label={t.close}
                    >
                        <X className="h-4 w-4" />
                    </button>
                </div>
                <SignIn
                    januaClient={client}
                    afterSignIn={() => {
                        onClose();
                        window.location.assign('/');
                    }}
                    redirectUrl="/"
                    socialProviders={{ google: true, github: true, microsoft: true, apple: true }}
                    showRememberMe={false}
                />
            </div>
        </div>
    );
}
