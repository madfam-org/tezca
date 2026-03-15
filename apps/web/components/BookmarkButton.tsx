'use client';

import { Heart } from 'lucide-react';
import { useBookmarks } from '@/components/providers/BookmarksContext';
import { useLang } from '@/components/providers/LanguageContext';
import { trackEvent } from '@/lib/analytics/posthog';

const labels = {
    es: { add: 'Agregar a favoritos', remove: 'Quitar de favoritos' },
    en: { add: 'Add to favorites', remove: 'Remove from favorites' },
    nah: { add: 'Xictlālia tlapepenilistli', remove: 'Xicquīxtia tlapepenilistli' },
};

interface BookmarkButtonProps {
    lawId: string;
    lawName: string;
}

export function BookmarkButton({ lawId, lawName }: BookmarkButtonProps) {
    const { lang } = useLang();
    const t = labels[lang];
    const { isBookmarked, toggleBookmark } = useBookmarks();
    const active = isBookmarked(lawId);

    return (
        <button
            onClick={() => { toggleBookmark(lawId, lawName); trackEvent('bookmark.toggled', { law_id: lawId, action: active ? 'remove' : 'add' }); }}
            className={`inline-flex items-center gap-2 rounded-md border px-4 py-2 text-sm font-medium transition-colors print:hidden ${
                active
                    ? 'border-red-300 bg-red-50 text-red-600 hover:bg-red-100 dark:border-red-800 dark:bg-red-950 dark:text-red-400'
                    : 'border-input bg-background hover:bg-accent hover:text-accent-foreground'
            }`}
            title={active ? t.remove : t.add}
            aria-pressed={active}
        >
            <Heart className={`h-4 w-4 ${active ? 'fill-current' : ''}`} aria-hidden="true" />
            <span className="hidden sm:inline">
                {active ? t.remove : t.add}
            </span>
        </button>
    );
}
