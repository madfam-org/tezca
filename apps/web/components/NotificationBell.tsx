'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import { Bell } from 'lucide-react';
import { cn } from '@tezca/lib';
import { api, type NotificationData } from '@/lib/api';
import { useAuth } from '@/components/providers/AuthContext';
import { useLang } from '@/components/providers/LanguageContext';

const content = {
    es: {
        title: 'Notificaciones',
        empty: 'No hay notificaciones.',
        markAllRead: 'Marcar todo como leído',
        notifications: 'Notificaciones',
    },
    en: {
        title: 'Notifications',
        empty: 'No notifications.',
        markAllRead: 'Mark all as read',
        notifications: 'Notifications',
    },
    nah: {
        title: 'Tēnahuatīlmeh',
        empty: 'Ahmo oncah tēnahuatīlmeh.',
        markAllRead: 'Xicpōhua mochi',
        notifications: 'Tēnahuatīlmeh',
    },
};

export function NotificationBell() {
    const { lang } = useLang();
    const t = content[lang];
    const { isAuthenticated } = useAuth();
    const [open, setOpen] = useState(false);
    const [notifications, setNotifications] = useState<NotificationData[]>([]);
    const [unread, setUnread] = useState(0);
    const dropdownRef = useRef<HTMLDivElement>(null);

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

    const fetchNotifications = useCallback(async () => {
        const token = getToken();
        if (!token) return;
        try {
            const res = await api.getNotifications(token);
            setNotifications(res.notifications);
            setUnread(res.unread);
        } catch {
            // silent
        }
    }, [getToken]);

    useEffect(() => {
        if (isAuthenticated) {
            fetchNotifications();
            // Poll every 60s
            const interval = setInterval(fetchNotifications, 60_000);
            return () => clearInterval(interval);
        }
    }, [isAuthenticated, fetchNotifications]);

    // Close dropdown on outside click
    useEffect(() => {
        function handleClick(e: MouseEvent) {
            if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
                setOpen(false);
            }
        }
        if (open) document.addEventListener('mousedown', handleClick);
        return () => document.removeEventListener('mousedown', handleClick);
    }, [open]);

    const handleMarkAllRead = async () => {
        const token = getToken();
        if (!token) return;
        try {
            await api.markNotificationsRead(token);
            setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })));
            setUnread(0);
        } catch {
            // silent
        }
    };

    if (!isAuthenticated) return null;

    return (
        <div className="relative" ref={dropdownRef}>
            <button
                onClick={() => setOpen(!open)}
                className="relative p-2 rounded-md text-muted-foreground hover:text-foreground hover:bg-muted/50 transition-colors"
                aria-label={t.notifications}
            >
                <Bell className="h-4 w-4" />
                {unread > 0 && (
                    <span className="absolute -top-0.5 -right-0.5 flex h-4 w-4 items-center justify-center rounded-full bg-destructive text-destructive-foreground text-[10px] font-bold">
                        {unread > 9 ? '9+' : unread}
                    </span>
                )}
            </button>

            {open && (
                <div className="absolute right-0 top-full mt-2 w-80 bg-background border rounded-lg shadow-lg z-50 overflow-hidden">
                    <div className="flex items-center justify-between px-4 py-2.5 border-b">
                        <h3 className="text-sm font-semibold">{t.title}</h3>
                        {unread > 0 && (
                            <button
                                onClick={handleMarkAllRead}
                                className="text-xs text-primary hover:underline"
                            >
                                {t.markAllRead}
                            </button>
                        )}
                    </div>
                    <div className="max-h-80 overflow-y-auto">
                        {notifications.length === 0 ? (
                            <p className="text-sm text-muted-foreground text-center py-6">{t.empty}</p>
                        ) : (
                            notifications.slice(0, 10).map((n) => (
                                <a
                                    key={n.id}
                                    href={n.link || '#'}
                                    className={cn(
                                        'block px-4 py-3 border-b last:border-0 hover:bg-muted/50 transition-colors',
                                        !n.is_read && 'bg-primary/5',
                                    )}
                                    onClick={() => setOpen(false)}
                                >
                                    <p className={cn('text-sm', !n.is_read && 'font-medium')}>{n.title}</p>
                                    <p className="text-xs text-muted-foreground mt-0.5 line-clamp-2">{n.body}</p>
                                    <p className="text-xs text-muted-foreground mt-1">
                                        {new Date(n.created_at).toLocaleDateString()}
                                    </p>
                                </a>
                            ))
                        )}
                    </div>
                </div>
            )}
        </div>
    );
}
