'use client';

import { useState, useEffect, useCallback } from 'react';
import { Card } from '@tezca/ui';
import { MessageSquare, Trash2, ExternalLink } from 'lucide-react';
import { api, type AnnotationData } from '@/lib/api';
import { useAuth } from '@/components/providers/AuthContext';
import { useLang } from '@/components/providers/LanguageContext';
import Link from 'next/link';

const content = {
    es: {
        title: 'Mis notas',
        subtitle: 'Todas tus anotaciones en leyes y artículos.',
        empty: 'Aún no tienes notas. Agrega una desde cualquier ley.',
        delete: 'Eliminar',
        article: 'Artículo',
        loading: 'Cargando notas...',
        viewLaw: 'Ver ley',
    },
    en: {
        title: 'My notes',
        subtitle: 'All your annotations on laws and articles.',
        empty: 'No notes yet. Add one from any law.',
        delete: 'Delete',
        article: 'Article',
        loading: 'Loading notes...',
        viewLaw: 'View law',
    },
    nah: {
        title: 'Notlahcuilōlhuān',
        subtitle: 'Mochi motlahcuilōlhuān ipan tenahuatīlmeh.',
        empty: 'Ahmo oncah tlahcuilōlmeh. Xictlālia cē.',
        delete: 'Xicpoloa',
        article: 'Tlanahuatilli',
        loading: 'Motēmoa tlahcuilōlmeh...',
        viewLaw: 'Xictta tenahuatilli',
    },
};

const COLOR_MAP: Record<string, string> = {
    yellow: 'border-l-yellow-400',
    green: 'border-l-green-400',
    blue: 'border-l-blue-400',
    pink: 'border-l-pink-400',
};

export default function NotasPage() {
    const { lang } = useLang();
    const t = content[lang];
    const { isAuthenticated } = useAuth();
    const [annotations, setAnnotations] = useState<AnnotationData[]>([]);
    const [loading, setLoading] = useState(true);

    const getToken = useCallback((): string | null => {
        if (typeof document !== 'undefined') {
            const match = document.cookie.match(/(?:^|;\s*)janua_token=([^;]*)/);
            if (match) return decodeURIComponent(match[1]);
        }
        if (typeof localStorage !== 'undefined') {
            return localStorage.getItem('janua_token');
        }
        return null;
    }, []);

    useEffect(() => {
        async function fetch() {
            const token = getToken();
            if (!token) {
                setLoading(false);
                return;
            }
            try {
                const res = await api.getAnnotations(token);
                setAnnotations(res.annotations);
            } catch {
                // silent
            } finally {
                setLoading(false);
            }
        }
        if (isAuthenticated) fetch();
        else setLoading(false);
    }, [isAuthenticated, getToken]);

    const handleDelete = async (id: number) => {
        const token = getToken();
        if (!token) return;
        try {
            await api.deleteAnnotation(token, id);
            setAnnotations((prev) => prev.filter((a) => a.id !== id));
        } catch {
            // silent
        }
    };

    // Group by law_id
    const grouped = annotations.reduce<Record<string, AnnotationData[]>>((acc, a) => {
        (acc[a.law_id] ??= []).push(a);
        return acc;
    }, {});

    return (
        <div className="max-w-3xl mx-auto">
            <div className="flex items-center gap-3 mb-6">
                <MessageSquare className="h-6 w-6 text-primary" />
                <div>
                    <h1 className="text-2xl font-bold text-foreground">{t.title}</h1>
                    <p className="text-sm text-muted-foreground">{t.subtitle}</p>
                </div>
            </div>

            {loading ? (
                <p className="text-sm text-muted-foreground text-center py-12">{t.loading}</p>
            ) : annotations.length === 0 ? (
                <Card className="p-12 text-center text-muted-foreground">{t.empty}</Card>
            ) : (
                <div className="space-y-6">
                    {Object.entries(grouped).map(([lawId, notes]) => (
                        <div key={lawId}>
                            <div className="flex items-center gap-2 mb-2">
                                <h2 className="text-sm font-semibold text-foreground truncate">{lawId}</h2>
                                <Link
                                    href={`/leyes/${encodeURIComponent(lawId)}`}
                                    className="text-xs text-primary hover:underline flex items-center gap-0.5"
                                >
                                    <ExternalLink className="h-3 w-3" />
                                    {t.viewLaw}
                                </Link>
                            </div>
                            <div className="space-y-2">
                                {notes.map((note) => (
                                    <Card
                                        key={note.id}
                                        className={`p-3 border-l-4 ${COLOR_MAP[note.color] || COLOR_MAP.yellow}`}
                                    >
                                        <div className="flex items-start justify-between gap-2">
                                            <div className="min-w-0">
                                                <p className="text-xs text-muted-foreground mb-1">
                                                    {t.article} {note.article_id}
                                                </p>
                                                <p className="text-sm text-foreground whitespace-pre-wrap">{note.text}</p>
                                            </div>
                                            <button
                                                onClick={() => handleDelete(note.id)}
                                                className="p-1 rounded hover:bg-destructive/10 text-destructive flex-shrink-0"
                                                aria-label={t.delete}
                                            >
                                                <Trash2 className="h-3.5 w-3.5" />
                                            </button>
                                        </div>
                                        <p className="text-xs text-muted-foreground mt-2">
                                            {new Date(note.created_at).toLocaleDateString()}
                                        </p>
                                    </Card>
                                ))}
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}
