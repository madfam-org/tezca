'use client';

import { useState, useCallback, useSyncExternalStore } from 'react';
import { X } from 'lucide-react';
import { useLang } from '@/components/providers/LanguageContext';

const STORAGE_KEY = 'comparison-hint-dismissed';

const labels = {
    es: 'Selecciona leyes para compararlas',
    en: 'Select laws to compare them',
    nah: 'Xictlapēpeni tenahuatilli ic motlanānamiqui',
};

function useIsDismissed() {
    const subscribe = useCallback(() => () => {}, []);
    const getSnapshot = useCallback(() => {
        if (typeof window === 'undefined') return true;
        if (typeof localStorage === 'undefined' || typeof localStorage.getItem !== 'function') return true;
        try {
            return localStorage.getItem(STORAGE_KEY) === '1';
        } catch {
            return true;
        }
    }, []);
    const getServerSnapshot = useCallback(() => true, []); // hide on SSR
    return useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);
}

export function ComparisonHint() {
    const { lang } = useLang();
    const dismissed = useIsDismissed();
    const [hidden, setHidden] = useState(false);

    const dismiss = () => {
        setHidden(true);
        try {
            if (typeof localStorage !== 'undefined' && typeof localStorage.setItem === 'function') {
                localStorage.setItem(STORAGE_KEY, '1');
            }
        } catch {
            // localStorage unavailable
        }
    };

    const show = !dismissed && !hidden;

    if (!show) return null;

    return (
        <div className="absolute -top-10 left-1/2 -translate-x-1/2 z-20 whitespace-nowrap animate-fade-in">
            <div className="relative bg-primary text-primary-foreground text-xs px-3 py-1.5 rounded-md shadow-lg">
                {labels[lang]}
                <button onClick={dismiss} className="ml-2 opacity-70 hover:opacity-100" aria-label="Cerrar">
                    <X className="h-3 w-3 inline" />
                </button>
                {/* Arrow pointing down */}
                <div className="absolute top-full left-1/2 -translate-x-1/2 w-0 h-0 border-x-[6px] border-x-transparent border-t-[6px] border-t-primary" />
            </div>
        </div>
    );
}
