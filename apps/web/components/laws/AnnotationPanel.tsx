'use client';

import { useState, useEffect, useCallback } from 'react';
import { X, Plus, Trash2, Pencil, Check, MessageSquare } from 'lucide-react';
import { Card } from '@tezca/ui';
import { cn } from '@tezca/lib';
import { api, type AnnotationData } from '@/lib/api';
import { useAuth } from '@/components/providers/AuthContext';
import { useLang } from '@/components/providers/LanguageContext';

const content = {
    es: {
        title: 'Notas y anotaciones',
        noNotes: 'No hay notas para esta ley.',
        addNote: 'Agregar nota',
        save: 'Guardar',
        cancel: 'Cancelar',
        delete: 'Eliminar',
        edit: 'Editar',
        close: 'Cerrar panel',
        placeholder: 'Escribe tu nota...',
        articleLabel: 'Artículo',
        loginRequired: 'Inicia sesión para guardar notas.',
        color: 'Color',
        confirmDelete: 'Eliminar esta nota?',
    },
    en: {
        title: 'Notes & annotations',
        noNotes: 'No notes for this law.',
        addNote: 'Add note',
        save: 'Save',
        cancel: 'Cancel',
        delete: 'Delete',
        edit: 'Edit',
        close: 'Close panel',
        placeholder: 'Write your note...',
        articleLabel: 'Article',
        loginRequired: 'Sign in to save notes.',
        color: 'Color',
        confirmDelete: 'Delete this note?',
    },
    nah: {
        title: 'Tlahcuilōlmeh',
        noNotes: 'Ahmo oncah tlahcuilōlmeh.',
        addNote: 'Xictlālia tlahcuilōlli',
        save: 'Xicpiya',
        cancel: 'Xictlacahua',
        delete: 'Xicpoloa',
        edit: 'Xicpatla',
        close: 'Xictlatzacua',
        placeholder: 'Xicihcuiloa...',
        articleLabel: 'Tlanahuatilli',
        loginRequired: 'Xicalaqui ic ticpiyaz.',
        color: 'Tlapalli',
        confirmDelete: 'Ticpoloaz in tlahcuilōlli?',
    },
};

const COLORS = ['yellow', 'green', 'blue', 'pink'] as const;
const COLOR_MAP: Record<string, string> = {
    yellow: 'bg-yellow-200 dark:bg-yellow-900/40',
    green: 'bg-green-200 dark:bg-green-900/40',
    blue: 'bg-blue-200 dark:bg-blue-900/40',
    pink: 'bg-pink-200 dark:bg-pink-900/40',
};

interface AnnotationPanelProps {
    lawId: string;
    open: boolean;
    onClose: () => void;
    focusArticleId?: string | null;
}

export function AnnotationPanel({ lawId, open, onClose, focusArticleId }: AnnotationPanelProps) {
    const { lang } = useLang();
    const t = content[lang];
    const { isAuthenticated } = useAuth();
    const [annotations, setAnnotations] = useState<AnnotationData[]>([]);
    const [loading, setLoading] = useState(false);
    const [adding, setAdding] = useState(false);
    const [editingId, setEditingId] = useState<number | null>(null);
    const [newText, setNewText] = useState('');
    const [newColor, setNewColor] = useState<string>('yellow');
    const [newArticleId, setNewArticleId] = useState('');
    const [editText, setEditText] = useState('');
    const [editColor, setEditColor] = useState('yellow');

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

    const fetchAnnotations = useCallback(async () => {
        const token = getToken();
        if (!token) return;
        setLoading(true);
        try {
            const res = await api.getAnnotations(token, lawId);
            setAnnotations(res.annotations);
        } catch {
            // silent
        } finally {
            setLoading(false);
        }
    }, [lawId, getToken]);

    useEffect(() => {
        if (open && isAuthenticated) {
            fetchAnnotations();
        }
    }, [open, isAuthenticated, fetchAnnotations]);

    useEffect(() => {
        if (focusArticleId) {
            setNewArticleId(focusArticleId);
        }
    }, [focusArticleId]);

    const handleCreate = async () => {
        const token = getToken();
        if (!token || !newText.trim() || !newArticleId.trim()) return;
        try {
            const annotation = await api.createAnnotation(token, {
                law_id: lawId,
                article_id: newArticleId,
                text: newText,
                color: newColor,
            });
            setAnnotations((prev) => [...prev, annotation]);
            setNewText('');
            setAdding(false);
        } catch {
            // silent
        }
    };

    const handleUpdate = async (id: number) => {
        const token = getToken();
        if (!token) return;
        try {
            const updated = await api.updateAnnotation(token, id, {
                text: editText,
                color: editColor,
            });
            setAnnotations((prev) => prev.map((a) => (a.id === id ? updated : a)));
            setEditingId(null);
        } catch {
            // silent
        }
    };

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

    if (!open) return null;

    const filtered = focusArticleId
        ? annotations.filter((a) => a.article_id === focusArticleId)
        : annotations;

    // Group by article
    const grouped = filtered.reduce<Record<string, AnnotationData[]>>((acc, a) => {
        (acc[a.article_id] ??= []).push(a);
        return acc;
    }, {});

    return (
        <div className="fixed inset-y-0 right-0 z-50 w-full sm:w-96 bg-background border-l shadow-xl flex flex-col animate-slide-in-right">
            {/* Header */}
            <div className="flex items-center justify-between px-4 py-3 border-b">
                <div className="flex items-center gap-2">
                    <MessageSquare className="h-5 w-5 text-primary" />
                    <h2 className="font-semibold text-foreground">{t.title}</h2>
                </div>
                <button onClick={onClose} className="p-1.5 rounded-md hover:bg-muted" aria-label={t.close}>
                    <X className="h-4 w-4" />
                </button>
            </div>

            {/* Body */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4">
                {!isAuthenticated ? (
                    <p className="text-sm text-muted-foreground text-center py-8">{t.loginRequired}</p>
                ) : loading ? (
                    <div className="flex justify-center py-8">
                        <div className="h-6 w-6 border-2 border-primary border-t-transparent rounded-full animate-spin" />
                    </div>
                ) : Object.keys(grouped).length === 0 && !adding ? (
                    <p className="text-sm text-muted-foreground text-center py-8">{t.noNotes}</p>
                ) : (
                    Object.entries(grouped).map(([articleId, notes]) => (
                        <div key={articleId}>
                            <h3 className="text-xs font-medium text-muted-foreground mb-2">
                                {t.articleLabel} {articleId}
                            </h3>
                            <div className="space-y-2">
                                {notes.map((note) =>
                                    editingId === note.id ? (
                                        <Card key={note.id} className="p-3 space-y-2">
                                            <textarea
                                                value={editText}
                                                onChange={(e) => setEditText(e.target.value)}
                                                className="w-full text-sm bg-transparent border rounded-md p-2 resize-none"
                                                rows={3}
                                            />
                                            <div className="flex items-center gap-1">
                                                {COLORS.map((c) => (
                                                    <button
                                                        key={c}
                                                        onClick={() => setEditColor(c)}
                                                        className={cn(
                                                            'w-5 h-5 rounded-full border-2',
                                                            COLOR_MAP[c],
                                                            editColor === c ? 'border-foreground' : 'border-transparent',
                                                        )}
                                                        aria-label={c}
                                                    />
                                                ))}
                                            </div>
                                            <div className="flex gap-2">
                                                <button
                                                    onClick={() => handleUpdate(note.id)}
                                                    className="flex items-center gap-1 text-xs px-2 py-1 bg-primary text-primary-foreground rounded-md"
                                                >
                                                    <Check className="h-3 w-3" /> {t.save}
                                                </button>
                                                <button
                                                    onClick={() => setEditingId(null)}
                                                    className="text-xs px-2 py-1 text-muted-foreground hover:text-foreground"
                                                >
                                                    {t.cancel}
                                                </button>
                                            </div>
                                        </Card>
                                    ) : (
                                        <Card key={note.id} className={cn('p-3 border-l-4', COLOR_MAP[note.color] || COLOR_MAP.yellow)}>
                                            <p className="text-sm text-foreground whitespace-pre-wrap">{note.text}</p>
                                            <div className="flex items-center justify-between mt-2">
                                                <span className="text-xs text-muted-foreground">
                                                    {new Date(note.created_at).toLocaleDateString()}
                                                </span>
                                                <div className="flex gap-1">
                                                    <button
                                                        onClick={() => {
                                                            setEditingId(note.id);
                                                            setEditText(note.text);
                                                            setEditColor(note.color);
                                                        }}
                                                        className="p-1 rounded hover:bg-muted"
                                                        aria-label={t.edit}
                                                    >
                                                        <Pencil className="h-3 w-3" />
                                                    </button>
                                                    <button
                                                        onClick={() => handleDelete(note.id)}
                                                        className="p-1 rounded hover:bg-destructive/10 text-destructive"
                                                        aria-label={t.delete}
                                                    >
                                                        <Trash2 className="h-3 w-3" />
                                                    </button>
                                                </div>
                                            </div>
                                        </Card>
                                    ),
                                )}
                            </div>
                        </div>
                    ))
                )}

                {/* New annotation form */}
                {adding && isAuthenticated && (
                    <Card className="p-3 space-y-2">
                        <input
                            type="text"
                            value={newArticleId}
                            onChange={(e) => setNewArticleId(e.target.value)}
                            placeholder={t.articleLabel}
                            className="w-full text-sm bg-transparent border rounded-md p-2"
                        />
                        <textarea
                            value={newText}
                            onChange={(e) => setNewText(e.target.value)}
                            placeholder={t.placeholder}
                            className="w-full text-sm bg-transparent border rounded-md p-2 resize-none"
                            rows={3}
                            autoFocus
                        />
                        <div className="flex items-center gap-1">
                            <span className="text-xs text-muted-foreground mr-1">{t.color}:</span>
                            {COLORS.map((c) => (
                                <button
                                    key={c}
                                    onClick={() => setNewColor(c)}
                                    className={cn(
                                        'w-5 h-5 rounded-full border-2',
                                        COLOR_MAP[c],
                                        newColor === c ? 'border-foreground' : 'border-transparent',
                                    )}
                                    aria-label={c}
                                />
                            ))}
                        </div>
                        <div className="flex gap-2">
                            <button
                                onClick={handleCreate}
                                disabled={!newText.trim() || !newArticleId.trim()}
                                className="flex items-center gap-1 text-xs px-2 py-1 bg-primary text-primary-foreground rounded-md disabled:opacity-50"
                            >
                                <Check className="h-3 w-3" /> {t.save}
                            </button>
                            <button
                                onClick={() => {
                                    setAdding(false);
                                    setNewText('');
                                }}
                                className="text-xs px-2 py-1 text-muted-foreground hover:text-foreground"
                            >
                                {t.cancel}
                            </button>
                        </div>
                    </Card>
                )}
            </div>

            {/* Footer add button */}
            {isAuthenticated && !adding && (
                <div className="border-t px-4 py-3">
                    <button
                        onClick={() => setAdding(true)}
                        className="flex items-center gap-2 w-full justify-center text-sm px-3 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 transition-colors"
                    >
                        <Plus className="h-4 w-4" /> {t.addNote}
                    </button>
                </div>
            )}
        </div>
    );
}
