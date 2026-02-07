'use client';

import Link from 'next/link';
import { Search, Home, ArrowLeft } from 'lucide-react';
import { useLang } from '@/components/providers/LanguageContext';

const content = {
    es: {
        title: 'Página no encontrada',
        description: 'La página que buscas no existe o fue movida.',
        goHome: 'Ir al inicio',
        goSearch: 'Buscar leyes',
        goBack: 'Volver',
    },
    en: {
        title: 'Page not found',
        description: 'The page you are looking for does not exist or has been moved.',
        goHome: 'Go home',
        goSearch: 'Search laws',
        goBack: 'Go back',
    },
    nah: {
        title: 'Āmatl ahmo monextia',
        description: 'In āmatl in tictēmoa ahmo oncah.',
        goHome: 'Caltenco',
        goSearch: 'Xictlatemo tenahuatilli',
        goBack: 'Xicmocuepa',
    },
};

export default function NotFound() {
    const { lang } = useLang();
    const t = content[lang];

    return (
        <div className="flex flex-col items-center justify-center min-h-[60vh] px-4 text-center">
            <h1 className="text-7xl font-bold text-primary/20 mb-2">404</h1>
            <h2 className="text-2xl font-bold text-foreground mb-2">{t.title}</h2>
            <p className="text-muted-foreground mb-8 max-w-md">{t.description}</p>

            <div className="flex flex-wrap gap-3 justify-center">
                <Link
                    href="/"
                    className="inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors"
                >
                    <Home className="h-4 w-4" />
                    {t.goHome}
                </Link>
                <Link
                    href="/busqueda"
                    className="inline-flex items-center gap-2 rounded-md border border-input bg-background px-4 py-2 text-sm font-medium hover:bg-accent hover:text-accent-foreground transition-colors"
                >
                    <Search className="h-4 w-4" />
                    {t.goSearch}
                </Link>
                <button
                    onClick={() => window.history.back()}
                    className="inline-flex items-center gap-2 rounded-md border border-input bg-background px-4 py-2 text-sm font-medium hover:bg-accent hover:text-accent-foreground transition-colors"
                >
                    <ArrowLeft className="h-4 w-4" />
                    {t.goBack}
                </button>
            </div>
        </div>
    );
}
