'use client';

import { useState, useEffect } from 'react';
import { ArrowUp } from 'lucide-react';

export function BackToTop() {
    const [visible, setVisible] = useState(false);

    useEffect(() => {
        const handleScroll = () => setVisible(window.scrollY > 400);
        window.addEventListener('scroll', handleScroll, { passive: true });
        return () => window.removeEventListener('scroll', handleScroll);
    }, []);

    if (!visible) return null;

    return (
        <button
            onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}
            className="fixed bottom-6 right-6 z-40 rounded-full bg-primary p-3 min-h-[44px] min-w-[44px] inline-flex items-center justify-center text-primary-foreground shadow-lg transition-all hover:bg-primary/90 hover:shadow-xl animate-fade-in print:hidden"
            aria-label="Volver arriba"
        >
            <ArrowUp className="h-5 w-5" />
        </button>
    );
}
