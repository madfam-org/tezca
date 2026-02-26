'use client';

import { BookmarkCheck, Clock, LogOut, MessageSquare, Bell } from 'lucide-react';
import { useAuth } from '@/components/providers/AuthContext';
import { useLang } from '@/components/providers/LanguageContext';

const content = {
    es: {
        title: 'Mi cuenta',
        email: 'Correo electrónico',
        tier: 'Plan',
        tierLabels: { anon: 'Anónimo', free: 'Gratuito', premium: 'Premium' },
        bookmarks: 'Favoritos guardados',
        recentlyViewed: 'Vistos recientemente',
        notes: 'Mis notas',
        alerts: 'Mis alertas',
        preferences: 'Preferencias',
        signOut: 'Cerrar sesión',
        greeting: 'Bienvenido',
    },
    en: {
        title: 'My Account',
        email: 'Email',
        tier: 'Plan',
        tierLabels: { anon: 'Anonymous', free: 'Free', premium: 'Premium' },
        bookmarks: 'Saved Bookmarks',
        recentlyViewed: 'Recently Viewed',
        notes: 'My Notes',
        alerts: 'My Alerts',
        preferences: 'Preferences',
        signOut: 'Sign Out',
        greeting: 'Welcome',
    },
    nah: {
        title: 'Notocaitl',
        email: 'Amatlahcuilōlli',
        tier: 'Tlaxtlahuīlli',
        tierLabels: { anon: 'Ahmo machtīlli', free: 'Tlanāhuatīlli', premium: 'Premium' },
        bookmarks: 'Tlapepenilistli',
        recentlyViewed: 'Ōquittac achto',
        notes: 'Notlahcuilōlhuān',
        alerts: 'Notēnahuatīlhuān',
        preferences: 'Tlanequiliztli',
        signOut: 'Xiquīza',
        greeting: 'Ximopanōlti',
    },
};

const TIER_COLORS: Record<string, string> = {
    anon: 'bg-muted text-muted-foreground',
    free: 'bg-primary/10 text-primary',
    premium: 'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300',
};

export default function CuentaPage() {
    const { lang } = useLang();
    const t = content[lang];
    const { name, email, tier, signOut } = useAuth();

    const displayName = name || email || t.greeting;
    const tierLabel = t.tierLabels[tier] || tier;

    return (
        <main className="mx-auto max-w-3xl px-4 py-10 sm:px-6">
            <h1 className="text-2xl font-bold mb-8">{t.title}</h1>

            {/* Profile card */}
            <div className="rounded-lg border border-border bg-background p-6 mb-6">
                <div className="flex items-center gap-4 mb-4">
                    <div className="h-12 w-12 rounded-full bg-primary/10 flex items-center justify-center text-primary font-bold text-lg">
                        {(name || email || '?')[0].toUpperCase()}
                    </div>
                    <div>
                        <p className="font-semibold text-lg">{displayName}</p>
                        {email && <p className="text-sm text-muted-foreground">{email}</p>}
                    </div>
                </div>

                <div className="flex items-center gap-2">
                    <span className="text-sm text-muted-foreground">{t.tier}:</span>
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${TIER_COLORS[tier] || TIER_COLORS.free}`}>
                        {tierLabel}
                    </span>
                </div>
            </div>

            {/* Quick links */}
            <div className="grid gap-4 sm:grid-cols-2">
                <QuickLinkCard
                    href="/favoritos"
                    icon={<BookmarkCheck className="h-5 w-5" />}
                    label={t.bookmarks}
                />
                <QuickLinkCard
                    href="/leyes"
                    icon={<Clock className="h-5 w-5" />}
                    label={t.recentlyViewed}
                />
                <QuickLinkCard
                    href="/cuenta/notas"
                    icon={<MessageSquare className="h-5 w-5" />}
                    label={t.notes}
                />
                <QuickLinkCard
                    href="/cuenta/alertas"
                    icon={<Bell className="h-5 w-5" />}
                    label={t.alerts}
                />
            </div>

            {/* Sign out */}
            <div className="mt-8">
                <button
                    onClick={signOut}
                    className="flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium text-destructive hover:bg-destructive/10 transition-colors"
                >
                    <LogOut className="h-4 w-4" aria-hidden="true" />
                    {t.signOut}
                </button>
            </div>
        </main>
    );
}

function QuickLinkCard({ href, icon, label }: { href: string; icon: React.ReactNode; label: string }) {
    return (
        <a
            href={href}
            className="flex items-center gap-3 rounded-lg border border-border p-4 hover:bg-muted/50 transition-colors"
        >
            <div className="text-muted-foreground">{icon}</div>
            <span className="text-sm font-medium">{label}</span>
        </a>
    );
}
