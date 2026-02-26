'use client';

import { useState } from 'react';
import { Mail } from 'lucide-react';
import { useLang } from '@/components/providers/LanguageContext';

const content = {
    es: {
        title: 'Suscríbete al boletín',
        description: 'Recibe actualizaciones sobre nuevas leyes y cambios legislativos.',
        placeholder: 'tu@correo.com',
        subscribe: 'Suscribirse',
        success: 'Suscripción exitosa.',
        alreadySubscribed: 'Ya estás suscrito.',
        error: 'Error al suscribirse. Intenta de nuevo.',
    },
    en: {
        title: 'Subscribe to our newsletter',
        description: 'Get updates on new laws and legislative changes.',
        placeholder: 'you@email.com',
        subscribe: 'Subscribe',
        success: 'Successfully subscribed!',
        alreadySubscribed: "You're already subscribed.",
        error: 'Subscription failed. Please try again.',
    },
    nah: {
        title: 'Ximomachiyoti ipan amatlahcuilōlli',
        description: 'Xicseliti tlanāhuatilli yancuic.',
        placeholder: 'tehuatl@amatlahcuilōlli.com',
        subscribe: 'Ximomachiyoti',
        success: 'Cualli omochīuh.',
        alreadySubscribed: 'Ye timomachiyōtia.',
        error: 'Ahmo omochīuh. Xicyēyeco ōccepa.',
    },
};

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

export function NewsletterSignup() {
    const { lang } = useLang();
    const t = content[lang];
    const [email, setEmail] = useState('');
    const [status, setStatus] = useState<'idle' | 'loading' | 'success' | 'already' | 'error'>('idle');

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!email.trim()) return;

        setStatus('loading');
        try {
            const res = await fetch(`${API_BASE}/newsletter/subscribe/`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email: email.trim() }),
            });
            const data = await res.json();
            if (data.status === 'already_subscribed') {
                setStatus('already');
            } else if (res.ok) {
                setStatus('success');
                setEmail('');
            } else {
                setStatus('error');
            }
        } catch {
            setStatus('error');
        }
    };

    const message =
        status === 'success' ? t.success :
        status === 'already' ? t.alreadySubscribed :
        status === 'error' ? t.error : null;

    return (
        <div className="rounded-lg border border-border bg-muted/30 p-6">
            <div className="flex items-center gap-2 mb-2">
                <Mail className="h-5 w-5 text-primary" aria-hidden="true" />
                <h3 className="font-semibold">{t.title}</h3>
            </div>
            <p className="text-sm text-muted-foreground mb-4">{t.description}</p>

            <form onSubmit={handleSubmit} className="flex gap-2">
                <input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder={t.placeholder}
                    required
                    className="flex-1 rounded-md border border-border bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/50"
                    aria-label="Email"
                />
                <button
                    type="submit"
                    disabled={status === 'loading'}
                    className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50 transition-colors"
                >
                    {t.subscribe}
                </button>
            </form>

            {message && (
                <p
                    className={`mt-2 text-sm ${
                        status === 'error' ? 'text-destructive' : 'text-muted-foreground'
                    }`}
                    role="status"
                    aria-live="polite"
                >
                    {message}
                </p>
            )}
        </div>
    );
}
