'use client';

import { createContext, useContext, useCallback, useSyncExternalStore } from 'react';

interface Bookmark {
    id: string;
    name: string;
    bookmarkedAt: string;
}

interface BookmarksContextType {
    bookmarks: Bookmark[];
    isBookmarked: (id: string) => boolean;
    toggleBookmark: (id: string, name: string) => void;
    removeBookmark: (id: string) => void;
}

const BookmarksContext = createContext<BookmarksContextType | undefined>(undefined);
const STORAGE_KEY = 'bookmarks';

// Cached snapshot — only re-parse when raw string changes
let cachedRaw: string | null = null;
let cachedBookmarks: Bookmark[] = [];
const EMPTY: Bookmark[] = [];

// Subscribers for useSyncExternalStore
let listeners: (() => void)[] = [];
function emitChange() {
    listeners.forEach((l) => l());
}

function getSnapshot(): Bookmark[] {
    if (typeof window === 'undefined') return EMPTY;
    if (typeof localStorage === 'undefined' || typeof localStorage.getItem !== 'function') return EMPTY;
    try {
        const raw = localStorage.getItem(STORAGE_KEY);
        if (raw !== cachedRaw) {
            cachedRaw = raw;
            cachedBookmarks = raw ? JSON.parse(raw) : [];
        }
        return cachedBookmarks;
    } catch {
        return EMPTY;
    }
}

function getServerSnapshot(): Bookmark[] {
    return EMPTY;
}

export function BookmarksProvider({ children }: { children: React.ReactNode }) {
    const subscribe = useCallback((listener: () => void) => {
        listeners = [...listeners, listener];
        return () => {
            listeners = listeners.filter((l) => l !== listener);
        };
    }, []);

    const bookmarks = useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);

    const persist = useCallback((next: Bookmark[]) => {
        const raw = JSON.stringify(next);
        try {
            if (typeof localStorage !== 'undefined' && typeof localStorage.setItem === 'function') {
                localStorage.setItem(STORAGE_KEY, raw);
            }
        } catch {
            // localStorage unavailable
        }
        // Update cache immediately so getSnapshot returns stable reference
        cachedRaw = raw;
        cachedBookmarks = next;
        emitChange();
    }, []);

    const isBookmarked = useCallback((id: string) => bookmarks.some((b) => b.id === id), [bookmarks]);

    const toggleBookmark = useCallback(
        (id: string, name: string) => {
            if (isBookmarked(id)) {
                persist(bookmarks.filter((b) => b.id !== id));
            } else {
                persist([...bookmarks, { id, name, bookmarkedAt: new Date().toISOString() }]);
            }
        },
        [bookmarks, isBookmarked, persist]
    );

    const removeBookmark = useCallback(
        (id: string) => persist(bookmarks.filter((b) => b.id !== id)),
        [bookmarks, persist]
    );

    return (
        <BookmarksContext.Provider value={{ bookmarks, isBookmarked, toggleBookmark, removeBookmark }}>
            {children}
        </BookmarksContext.Provider>
    );
}

export function useBookmarks() {
    const ctx = useContext(BookmarksContext);
    if (!ctx) throw new Error('useBookmarks must be used within BookmarksProvider');
    return ctx;
}
