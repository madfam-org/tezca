'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { Badge } from '@tezca/ui';
import { useLang } from '@/components/providers/LanguageContext';
import { API_BASE_URL } from '@/lib/config';

const content = {
    es: {
        title: 'Leyes Populares',
        subtitle: 'Acceso rápido a las leyes más consultadas',
    },
    en: {
        title: 'Popular Laws',
        subtitle: 'Quick access to the most consulted laws',
    },
    nah: {
        title: 'Tenahuatilli Tlahtōltin',
        subtitle: 'Īciuhca tlaixmatiliztli in tenahuatilli achi tlahtōltin',
    },
};

const popularLaws = [
    { id: 'cpeum', name: 'Constitución', href: '/leyes/cpeum' },
    { id: 'ccf', name: 'Código Civil Federal', href: '/leyes/ccf' },
    { id: 'cpf', name: 'Código Penal Federal', href: '/leyes/cpf' },
    { id: 'lisr', name: 'ISR', href: '/leyes/lisr' },
    { id: 'liva', name: 'IVA', href: '/leyes/liva' },
    { id: 'lft', name: 'Ley Federal del Trabajo', href: '/leyes/lft' },
    { id: 'lss', name: 'Seguro Social', href: '/leyes/lss' },
    { id: 'amparo', name: 'Amparo', href: '/leyes/amparo' },
];

export function PopularLaws() {
    const { lang } = useLang();
    const t = content[lang];
    const [availableLaws, setAvailableLaws] = useState(popularLaws);

    useEffect(() => {
        const ids = popularLaws.map((l) => l.id).join(',');
        fetch(`${API_BASE_URL}/laws/exists/?ids=${ids}`)
            .then((res) => (res.ok ? res.json() : Promise.reject(res)))
            .then((data: { existing: string[] }) => {
                const existingSet = new Set(data.existing);
                const filtered = popularLaws.filter((l) => existingSet.has(l.id));
                if (filtered.length > 0) {
                    setAvailableLaws(filtered);
                }
                // If 0 exist, keep all badges (graceful degradation)
            })
            .catch(() => {
                // API unreachable — keep all badges as fallback
            });
    }, []);

    if (availableLaws.length === 0) {
        return null;
    }

    return (
        <div className="mx-auto max-w-7xl px-4 sm:px-6 py-10 sm:py-16">
            <div className="mb-8 text-center">
                <h2 className="font-display text-2xl font-bold text-foreground sm:text-3xl">
                    {t.title}
                </h2>
                <p className="mt-2 text-muted-foreground">
                    {t.subtitle}
                </p>
            </div>

            <div className="flex flex-wrap justify-center gap-3">
                {availableLaws.map((law) => (
                    <Link key={law.id} href={law.href}>
                        <Badge
                            variant="secondary"
                            className="cursor-pointer px-6 py-3 text-base font-medium transition-all hover:scale-105 hover:bg-primary-100 hover:text-primary-700 dark:hover:bg-primary-900"
                        >
                            {law.name}
                        </Badge>
                    </Link>
                ))}
            </div>
        </div>
    );
}
