'use client';

import { useSyncExternalStore, useCallback } from 'react';
import Link from 'next/link';
import { Clock, ChevronRight } from 'lucide-react';
import { Badge, Card } from '@tezca/ui';
import { useLang } from '@/components/providers/LanguageContext';

const STORAGE_KEY = 'recently-viewed-laws';
const MAX_ITEMS = 10;

export interface RecentLawEntry {
    id: string;
    name: string;
    tier: string;
    viewedAt: string;
}

const content = {
    es: {
        title: 'Consultadas recientemente',
        empty: 'Aún no has consultado leyes.',
        viewAll: 'Ver todo',
    },
    en: {
        title: 'Recently viewed',
        empty: 'You haven\'t viewed any laws yet.',
        viewAll: 'View all',
    },
    nah: {
        title: 'Yancuīc tlachiyaliztli',
        empty: 'Ayāmo ticpiya tenahuatilli tlachiyaliztli.',
        viewAll: 'Xiquitta mochi',
    },
};

/** Call on law detail mount to record a visit */
export function recordLawView(entry: Omit<RecentLawEntry, 'viewedAt'>) {
    if (typeof window === 'undefined') return;
    try {
        const raw = localStorage.getItem(STORAGE_KEY);
        let items: RecentLawEntry[] = raw ? JSON.parse(raw) : [];
        items = items.filter((i) => i.id !== entry.id);
        items.unshift({ ...entry, viewedAt: new Date().toISOString() });
        if (items.length > MAX_ITEMS) items = items.slice(0, MAX_ITEMS);
        localStorage.setItem(STORAGE_KEY, JSON.stringify(items));
    } catch {
        // localStorage unavailable
    }
}

function getSnapshot(): string {
    try {
        return localStorage.getItem(STORAGE_KEY) || '[]';
    } catch {
        return '[]';
    }
}

function getServerSnapshot(): string {
    return '[]';
}

function subscribe(callback: () => void): () => void {
    const handler = (e: StorageEvent) => {
        if (e.key === STORAGE_KEY) callback();
    };
    window.addEventListener('storage', handler);
    return () => window.removeEventListener('storage', handler);
}

export function RecentlyViewed() {
    const { lang } = useLang();
    const t = content[lang];
    const raw = useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);
    const items: RecentLawEntry[] = JSON.parse(raw);

    const tierLabel = useCallback((tier: string) => {
        const tierLabels: Record<string, Record<string, string>> = {
            federal: { es: 'Federal', en: 'Federal', nah: 'Federal' },
            state: { es: 'Estatal', en: 'State', nah: 'Altepetl' },
            municipal: { es: 'Municipal', en: 'Municipal', nah: 'Calpulli' },
        };
        return tierLabels[tier]?.[lang] ?? tier;
    }, [lang]);

    if (items.length === 0) return null;

    return (
        <section>
            <div className="flex items-center gap-2 mb-4">
                <Clock className="h-5 w-5 text-muted-foreground" />
                <h2 className="text-xl sm:text-2xl font-bold tracking-tight">{t.title}</h2>
            </div>
            <div className="flex gap-3 overflow-x-auto pb-2 scrollbar-thin">
                {items.slice(0, 6).map((item) => (
                    <Link key={item.id} href={`/leyes/${item.id}`} className="flex-shrink-0 w-56">
                        <Card className="p-3 h-full hover:shadow-md hover:border-primary/30 transition-all">
                            <Badge variant="outline" className="text-xs mb-1.5">
                                {tierLabel(item.tier)}
                            </Badge>
                            <p className="text-sm font-medium line-clamp-2 text-foreground">
                                {item.name}
                            </p>
                            <div className="mt-2 flex items-center text-xs text-muted-foreground">
                                <ChevronRight className="h-3 w-3" />
                            </div>
                        </Card>
                    </Link>
                ))}
            </div>
        </section>
    );
}
