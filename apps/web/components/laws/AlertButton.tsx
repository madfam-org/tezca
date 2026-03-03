'use client';

import { useState, useEffect } from 'react';
import { Bell, BellOff, Check } from 'lucide-react';
import { cn } from '@tezca/lib';
import { api } from '@/lib/api';
import { useAuth } from '@/components/providers/AuthContext';
import { useLang } from '@/components/providers/LanguageContext';
import { getAuthToken } from '@/lib/auth-token';

const content = {
    es: {
        watch: 'Seguir esta ley',
        watching: 'Siguiendo',
        unwatch: 'Dejar de seguir',
        loginRequired: 'Inicia sesión para recibir alertas',
        saved: 'Alerta guardada',
    },
    en: {
        watch: 'Watch this law',
        watching: 'Watching',
        unwatch: 'Unwatch',
        loginRequired: 'Sign in to receive alerts',
        saved: 'Alert saved',
    },
    nah: {
        watch: 'Xictlachili in tenahuatilli',
        watching: 'Tictlachilia',
        unwatch: 'Xictlacahua',
        loginRequired: 'Xicalaqui ic ticpiaz tēnahuatīlmeh',
        saved: 'Ōmopix',
    },
};

interface AlertButtonProps {
    lawId: string;
    className?: string;
}

export function AlertButton({ lawId, className }: AlertButtonProps) {
    const { lang } = useLang();
    const t = content[lang];
    const { isAuthenticated } = useAuth();
    const [watching, setWatching] = useState(false);
    const [justSaved, setJustSaved] = useState(false);
    const [alertId, setAlertId] = useState<number | null>(null);

    // Load existing watch state on mount
    useEffect(() => {
        if (!isAuthenticated) return;
        const token = getAuthToken();
        if (!token) return;

        api.getAlerts(token)
            .then(({ alerts }) => {
                const existing = alerts.find(a => a.law_id === lawId);
                if (existing) {
                    setWatching(true);
                    setAlertId(existing.id);
                }
            })
            .catch((err) => {
                console.error(err);
            });
    }, [isAuthenticated, lawId]);

    const handleToggle = async () => {
        const token = getAuthToken();
        if (!token) return;

        if (watching && alertId) {
            try {
                await api.deleteAlert(token, alertId);
                setWatching(false);
                setAlertId(null);
            } catch (err) {
                console.error(err);
            }
        } else {
            try {
                const alert = await api.createAlert(token, {
                    law_id: lawId,
                    alert_type: 'law_updated',
                });
                setWatching(true);
                setAlertId(alert.id);
                setJustSaved(true);
                setTimeout(() => setJustSaved(false), 2000);
            } catch (err) {
                console.error(err);
            }
        }
    };

    if (!isAuthenticated) {
        return (
            <button
                disabled
                className={cn(
                    'inline-flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-md',
                    'bg-muted text-muted-foreground cursor-not-allowed',
                    className,
                )}
                title={t.loginRequired}
            >
                <Bell className="h-4 w-4" />
                {t.watch}
            </button>
        );
    }

    return (
        <button
            onClick={handleToggle}
            className={cn(
                'inline-flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-md transition-colors',
                watching
                    ? 'bg-primary/10 text-primary hover:bg-destructive/10 hover:text-destructive'
                    : 'bg-muted text-muted-foreground hover:bg-primary/10 hover:text-primary',
                className,
            )}
        >
            {justSaved ? (
                <>
                    <Check className="h-4 w-4" />
                    {t.saved}
                </>
            ) : watching ? (
                <>
                    <BellOff className="h-4 w-4" />
                    {t.unwatch}
                </>
            ) : (
                <>
                    <Bell className="h-4 w-4" />
                    {t.watch}
                </>
            )}
        </button>
    );
}
