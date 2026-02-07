'use client';

import Link from 'next/link';
import { Heart, Trash2, BookOpen } from 'lucide-react';
import { useBookmarks } from '@/components/providers/BookmarksContext';
import { useLang, LOCALE_MAP } from '@/components/providers/LanguageContext';
import { Card, CardContent } from '@tezca/ui';

const content = {
    es: {
        title: 'Favoritos',
        description: 'Leyes que has guardado para acceso rápido',
        empty: 'No tienes leyes guardadas',
        emptyHint: 'Usa el botón de corazón en cualquier ley para agregarla aquí',
        browse: 'Explorar leyes',
        remove: 'Quitar',
        saved: 'Guardado',
    },
    en: {
        title: 'Favorites',
        description: 'Laws you saved for quick access',
        empty: 'You have no saved laws',
        emptyHint: 'Use the heart button on any law to add it here',
        browse: 'Browse laws',
        remove: 'Remove',
        saved: 'Saved',
    },
    nah: {
        title: 'Tlapepenilistli',
        description: 'Tenahuatilli ōticpix ic īciuhca tlaixmatiliztli',
        empty: 'Ahmo ticpiya tenahuatilli tlapiyaliztli',
        emptyHint: 'Xictēqui in yōllōtl ic tenahuatilli xicpiya nicān',
        browse: 'Xictlaixmati tenahuatilli',
        remove: 'Xicpōhua',
        saved: 'Ōmopix',
    },
};

export default function FavoritosPage() {
    const { lang } = useLang();
    const t = content[lang];
    const { bookmarks, removeBookmark } = useBookmarks();

    return (
        <div className="min-h-screen bg-background">
            <div className="border-b bg-card">
                <div className="mx-auto max-w-4xl px-4 sm:px-6 py-8">
                    <div className="flex items-center gap-3 mb-2">
                        <Heart className="h-6 w-6 text-red-500" />
                        <h1 className="font-display text-2xl sm:text-3xl font-bold">{t.title}</h1>
                    </div>
                    <p className="text-muted-foreground">{t.description}</p>
                </div>
            </div>

            <div className="mx-auto max-w-4xl px-4 sm:px-6 py-8">
                {bookmarks.length === 0 ? (
                    <div className="py-16 text-center">
                        <BookOpen className="h-12 w-12 mx-auto mb-4 text-muted-foreground/50" />
                        <p className="text-lg text-muted-foreground">{t.empty}</p>
                        <p className="mt-2 text-sm text-muted-foreground">{t.emptyHint}</p>
                        <Link
                            href="/busqueda"
                            className="mt-6 inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors"
                        >
                            {t.browse}
                        </Link>
                    </div>
                ) : (
                    <div className="space-y-3">
                        {bookmarks.map((bm) => (
                            <Card key={bm.id} className="transition-all hover:shadow-md">
                                <CardContent className="flex items-center justify-between p-4">
                                    <Link href={`/leyes/${bm.id}`} className="flex-1 min-w-0">
                                        <h3 className="font-medium truncate hover:text-primary transition-colors">
                                            {bm.name}
                                        </h3>
                                        <p className="text-xs text-muted-foreground mt-1">
                                            {t.saved}: {new Date(bm.bookmarkedAt).toLocaleDateString(LOCALE_MAP[lang])}
                                        </p>
                                    </Link>
                                    <button
                                        onClick={() => removeBookmark(bm.id)}
                                        className="ml-4 p-2 rounded-md text-muted-foreground hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-950 transition-colors"
                                        title={t.remove}
                                    >
                                        <Trash2 className="h-4 w-4" />
                                    </button>
                                </CardContent>
                            </Card>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
}
