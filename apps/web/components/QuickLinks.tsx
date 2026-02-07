'use client';

import Link from 'next/link';
import { Layers, MapPin, Scale, Search } from 'lucide-react';
import { useLang } from '@/components/providers/LanguageContext';

const content = {
    es: {
        title: 'Explora la legislación',
        categories: 'Por Categoría',
        categoriesDesc: 'Civil, penal, mercantil, fiscal...',
        states: 'Por Estado',
        statesDesc: '32 entidades federativas',
        browse: 'Catálogo Completo',
        browseDesc: 'Todas las leyes indexadas',
        search: 'Búsqueda Avanzada',
        searchDesc: 'Filtros, facetas y texto completo',
    },
    en: {
        title: 'Explore legislation',
        categories: 'By Category',
        categoriesDesc: 'Civil, criminal, commercial, fiscal...',
        states: 'By State',
        statesDesc: '32 federal entities',
        browse: 'Full Catalog',
        browseDesc: 'All indexed laws',
        search: 'Advanced Search',
        searchDesc: 'Filters, facets, and full text',
    },
    nah: {
        title: 'Xictlachiya tenahuatilli',
        categories: 'Ic Tlamantli',
        categoriesDesc: 'Civil, penal, mercantil, fiscal...',
        states: 'Ic Altepetl',
        statesDesc: '32 altepetl',
        browse: 'Mochi Amatlapalōlli',
        browseDesc: 'Mochi tenahuatilli',
        search: 'Tlatemoliztli Tlamatiliztli',
        searchDesc: 'Tlanōnōtzaliztli ihuan mochi tlahcuilōlli',
    },
};

const links = [
    { href: '/categorias', icon: Layers, key: 'categories' as const, descKey: 'categoriesDesc' as const },
    { href: '/estados', icon: MapPin, key: 'states' as const, descKey: 'statesDesc' as const },
    { href: '/leyes', icon: Scale, key: 'browse' as const, descKey: 'browseDesc' as const },
    { href: '/busqueda', icon: Search, key: 'search' as const, descKey: 'searchDesc' as const },
];

export function QuickLinks() {
    const { lang } = useLang();
    const t = content[lang];

    return (
        <section>
            <h2 className="text-xl sm:text-2xl font-bold tracking-tight mb-4 sm:mb-6">{t.title}</h2>
            <div className="grid grid-cols-2 gap-3 sm:gap-4 md:grid-cols-4">
                {links.map(({ href, icon: Icon, key, descKey }) => (
                    <Link
                        key={href}
                        href={href}
                        className="group flex flex-col items-center gap-2 rounded-xl border border-border bg-card p-4 sm:p-5 text-center transition-all hover:border-primary/50 hover:shadow-md"
                    >
                        <div className="rounded-lg bg-primary/10 p-2.5 transition-colors group-hover:bg-primary/20">
                            <Icon className="h-5 w-5 text-primary" />
                        </div>
                        <span className="font-medium text-sm">{t[key]}</span>
                        <span className="text-xs text-muted-foreground leading-tight">{t[descKey]}</span>
                    </Link>
                ))}
            </div>
        </section>
    );
}
