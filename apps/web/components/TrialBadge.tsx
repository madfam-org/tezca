'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { Clock } from 'lucide-react';
import { useAuth } from '@/components/providers/AuthContext';
import { useLang } from '@/components/providers/LanguageContext';

const content = {
    es: { trial: 'Prueba' },
    en: { trial: 'Trial' },
    nah: { trial: 'Yeyecoliztli' },
};

export function TrialBadge() {
    const { isOnTrial, trialEndsAt } = useAuth();
    const { lang } = useLang();
    const t = content[lang];
    const [now, setNow] = useState(() => new Date());

    useEffect(() => {
        if (!isOnTrial) return;
        const interval = setInterval(() => setNow(new Date()), 60_000);
        return () => clearInterval(interval);
    }, [isOnTrial]);

    if (!isOnTrial || !trialEndsAt) return null;

    const diffMs = trialEndsAt.getTime() - now.getTime();
    if (diffMs <= 0) return null;

    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
    const diffDays = Math.floor(diffHours / 24);
    const remainingHours = diffHours % 24;

    const timeStr = diffDays > 0 ? `${diffDays}d ${remainingHours}h` : `${diffHours}h`;
    const isUrgent = diffHours < 24;

    return (
        <Link
            href="/precios"
            className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium transition-colors ${
                isUrgent
                    ? 'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300 animate-pulse'
                    : 'bg-amber-50 text-amber-700 dark:bg-amber-900/20 dark:text-amber-400'
            }`}
        >
            <Clock className="h-3 w-3" />
            <span>{t.trial}: {timeStr}</span>
        </Link>
    );
}
