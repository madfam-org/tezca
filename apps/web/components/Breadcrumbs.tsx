'use client';

import Link from 'next/link';
import { ChevronRight } from 'lucide-react';
import { useLang } from '@/components/providers/LanguageContext';

interface BreadcrumbItem {
    label: string;
    href?: string;
}

const labels = {
    es: { home: 'Inicio', explore: 'Explorar' },
    en: { home: 'Home', explore: 'Explore' },
    nah: { home: 'Caltenco', explore: 'Tlaixmatiliztli' },
};

interface BreadcrumbsProps {
    lawName?: string;
}

export function Breadcrumbs({ lawName }: BreadcrumbsProps) {
    const { lang } = useLang();
    const t = labels[lang];

    const items: BreadcrumbItem[] = [
        { label: t.home, href: '/' },
        { label: t.explore, href: '/laws' },
    ];
    if (lawName) {
        items.push({ label: lawName });
    }

    return (
        <nav aria-label="Breadcrumb" className="mb-4">
            <ol className="flex items-center gap-1 text-sm text-muted-foreground flex-wrap">
                {items.map((item, i) => (
                    <li key={i} className="flex items-center gap-1">
                        {i > 0 && <ChevronRight className="h-3.5 w-3.5 flex-shrink-0" aria-hidden="true" />}
                        {item.href ? (
                            <Link href={item.href} className="hover:text-foreground transition-colors">
                                {item.label}
                            </Link>
                        ) : (
                            <span className="text-foreground font-medium truncate max-w-[min(300px,60vw)]" aria-current="page">
                                {item.label}
                            </span>
                        )}
                    </li>
                ))}
            </ol>
        </nav>
    );
}
