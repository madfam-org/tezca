'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { Lock, ArrowRight, Clock, Sparkles, X } from 'lucide-react';
import { Button, Badge, Card, CardContent } from '@tezca/ui';
import { useLang } from '@/components/providers/LanguageContext';
import { useAuth, type UserTier } from '@/components/providers/AuthContext';
import { getCheckoutUrl } from '@/lib/billing';

type TierGateVariant = 'inline' | 'overlay' | 'card' | 'toast';
type RequiredTier = 'community' | 'essentials' | 'academic' | 'institutional';

const content = {
    es: {
        unlockTitle: {
            community: 'Crea tu cuenta gratuita',
            essentials: 'Desbloquea más con Essentials',
            academic: 'Desbloquea todo con Academic',
            institutional: 'Acceso completo con Institutional',
        },
        unlockSubtitle: {
            community: 'Accede a PDF, JSON y funciones básicas',
            essentials: 'Búsqueda avanzada, más formatos de descarga',
            academic: 'LaTeX, análisis avanzado y descarga masiva',
            institutional: 'Todos los formatos, webhooks y API de grafo',
        },
        cta: {
            community: 'Empieza gratis',
            essentials: 'Mejora a Essentials',
            academic: 'Mejora a Academic',
            institutional: 'Mejora a Institutional',
        },
        rateLimited: 'Tus consultas se renuevan en',
        minutes: 'min',
        seconds: 'seg',
        currentPlan: 'Tu plan actual',
        feature: 'Esta función requiere',
        dismiss: 'Cerrar',
        learnMore: 'Ver planes',
    },
    en: {
        unlockTitle: {
            community: 'Create your free account',
            essentials: 'Unlock more with Essentials',
            academic: 'Unlock everything with Academic',
            institutional: 'Full access with Institutional',
        },
        unlockSubtitle: {
            community: 'Access PDF, JSON, and basic features',
            essentials: 'Advanced search and more download formats',
            academic: 'LaTeX, advanced analytics, and bulk downloads',
            institutional: 'All formats, webhooks, and graph API',
        },
        cta: {
            community: 'Start free',
            essentials: 'Upgrade to Essentials',
            academic: 'Upgrade to Academic',
            institutional: 'Upgrade to Institutional',
        },
        rateLimited: 'Your requests renew in',
        minutes: 'min',
        seconds: 'sec',
        currentPlan: 'Your current plan',
        feature: 'This feature requires',
        dismiss: 'Dismiss',
        learnMore: 'View plans',
    },
    nah: {
        unlockTitle: {
            community: 'Xictlālia mocuenta',
            essentials: 'Xictlapo achi ica Essentials',
            academic: 'Xictlapo mochi ica Academic',
            institutional: 'Mochi ica Institutional',
        },
        unlockSubtitle: {
            community: 'Xicāci PDF, JSON ihuan tlachīhualiztli',
            essentials: 'Tlatemoliztli huēyi ihuan achi tēmōhuiliztli',
            academic: 'LaTeX, tlanextīliztli ihuan mīec tēmōhuiliztli',
            institutional: 'Mochi tlahtōlli, webhooks ihuan tlanextīliztli',
        },
        cta: {
            community: 'Xipēhua',
            essentials: 'Xicmelahua ic Essentials',
            academic: 'Xicmelahua ic Academic',
            institutional: 'Xicmelahua ic Institutional',
        },
        rateLimited: 'Motlatemoliztli mopātia ic',
        minutes: 'min',
        seconds: 'seg',
        currentPlan: 'Mocuenta',
        feature: 'Inīn monequi',
        dismiss: 'Xictlātia',
        learnMore: 'Xiquitta tlaxtlahuīlli',
    },
};

const TIER_DISPLAY: Record<string, string> = {
    anon: 'Anónimo',
    community: 'Community',
    essentials: 'Essentials',
    academic: 'Academic',
    institutional: 'Institutional',
    madfam: 'MADFAM',
};

interface TierGateProps {
    variant: TierGateVariant;
    requiredTier: RequiredTier;
    feature?: string;
    benefits?: string[];
    showCountdown?: boolean;
    retryAfterSeconds?: number;
    onDismiss?: () => void;
    className?: string;
}

export function TierGate({
    variant,
    requiredTier,
    feature,
    benefits,
    showCountdown = false,
    retryAfterSeconds,
    onDismiss,
    className = '',
}: TierGateProps) {
    const { lang } = useLang();
    const { tier, userId, isAuthenticated } = useAuth();
    const t = content[lang];

    const [countdown, setCountdown] = useState(retryAfterSeconds ?? 0);
    const [dismissed, setDismissed] = useState(false);

    useEffect(() => {
        if (!showCountdown || countdown <= 0) return;
        const interval = setInterval(() => {
            setCountdown((c) => {
                if (c <= 1) {
                    clearInterval(interval);
                    return 0;
                }
                return c - 1;
            });
        }, 1000);
        return () => clearInterval(interval);
    }, [showCountdown, countdown]);

    if (dismissed) return null;

    const handleDismiss = () => {
        setDismissed(true);
        onDismiss?.();
    };

    const targetTier = !isAuthenticated ? 'community' : requiredTier;
    const checkoutUrl = isAuthenticated
        ? getCheckoutUrl(requiredTier === 'community' ? 'essentials' : requiredTier, userId ?? undefined, typeof window !== 'undefined' ? window.location.href : undefined)
        : '/login';
    const ctaLabel = t.cta[targetTier as keyof typeof t.cta] ?? t.cta.academic;
    const title = t.unlockTitle[targetTier as keyof typeof t.unlockTitle] ?? t.unlockTitle.academic;
    const subtitle = t.unlockSubtitle[targetTier as keyof typeof t.unlockSubtitle] ?? t.unlockSubtitle.academic;

    const countdownDisplay = countdown > 0
        ? `${Math.floor(countdown / 60)}:${String(countdown % 60).padStart(2, '0')}`
        : null;

    if (variant === 'toast') {
        return (
            <div className={`fixed bottom-4 right-4 z-50 max-w-sm animate-in slide-in-from-bottom-5 fade-in duration-300 ${className}`}>
                <Card className="border-primary/20 shadow-lg">
                    <CardContent className="p-4">
                        <div className="flex items-start gap-3">
                            <div className="rounded-full bg-primary/10 p-2 shrink-0">
                                {showCountdown ? (
                                    <Clock className="h-4 w-4 text-primary" />
                                ) : (
                                    <Lock className="h-4 w-4 text-primary" />
                                )}
                            </div>
                            <div className="flex-1 min-w-0">
                                {showCountdown && countdownDisplay ? (
                                    <>
                                        <p className="text-sm font-medium">
                                            {t.rateLimited}
                                        </p>
                                        <p className="text-2xl font-bold text-primary mt-1 font-mono">
                                            {countdownDisplay}
                                        </p>
                                    </>
                                ) : (
                                    <p className="text-sm font-medium">{title}</p>
                                )}
                                <div className="flex items-center gap-2 mt-2">
                                    <Badge variant="outline" className="text-xs">
                                        {TIER_DISPLAY[tier] ?? tier}
                                    </Badge>
                                    <ArrowRight className="h-3 w-3 text-muted-foreground" />
                                    <Badge className="text-xs bg-primary text-primary-foreground">
                                        {TIER_DISPLAY[requiredTier]}
                                    </Badge>
                                </div>
                                <Link href={checkoutUrl} className="mt-3 inline-block">
                                    <Button size="sm" className="gap-1">
                                        <Sparkles className="h-3 w-3" />
                                        {ctaLabel}
                                    </Button>
                                </Link>
                            </div>
                            <button
                                onClick={handleDismiss}
                                className="text-muted-foreground hover:text-foreground shrink-0"
                                aria-label={t.dismiss}
                            >
                                <X className="h-4 w-4" />
                            </button>
                        </div>
                    </CardContent>
                </Card>
            </div>
        );
    }

    if (variant === 'inline') {
        return (
            <div className={`rounded-lg border border-primary/20 bg-gradient-to-r from-primary/5 to-primary/10 p-4 ${className}`}>
                <div className="flex flex-col sm:flex-row items-start sm:items-center gap-3">
                    <div className="flex items-center gap-3 flex-1 min-w-0">
                        <div className="rounded-full bg-primary/10 p-2 shrink-0">
                            <Lock className="h-4 w-4 text-primary" />
                        </div>
                        <div className="min-w-0">
                            <p className="text-sm font-medium">{title}</p>
                            <p className="text-xs text-muted-foreground mt-0.5 truncate">
                                {feature ?? subtitle}
                            </p>
                        </div>
                    </div>
                    <Link href={checkoutUrl} className="shrink-0">
                        <Button size="sm" className="gap-1 group">
                            <Sparkles className="h-3 w-3" />
                            {ctaLabel}
                            <ArrowRight className="h-3 w-3 transition-transform group-hover:translate-x-0.5" />
                        </Button>
                    </Link>
                </div>
                {showCountdown && countdownDisplay && (
                    <div className="mt-3 flex items-center gap-2 text-sm">
                        <Clock className="h-3.5 w-3.5 text-muted-foreground" />
                        <span className="text-muted-foreground">{t.rateLimited}</span>
                        <span className="font-mono font-bold text-primary">{countdownDisplay}</span>
                    </div>
                )}
            </div>
        );
    }

    if (variant === 'card') {
        return (
            <Card className={`border-primary/20 overflow-hidden ${className}`}>
                <div className="absolute inset-0 bg-gradient-to-br from-primary/5 via-transparent to-primary/10 pointer-events-none" />
                <CardContent className="relative p-6 sm:p-8 text-center">
                    <div className="mx-auto rounded-full bg-primary/10 p-3 w-fit mb-4">
                        <Sparkles className="h-6 w-6 text-primary" />
                    </div>
                    <h3 className="text-lg font-bold mb-2">{title}</h3>
                    <p className="text-sm text-muted-foreground mb-4 max-w-md mx-auto">
                        {feature ?? subtitle}
                    </p>

                    {/* Tier badges */}
                    <div className="flex items-center justify-center gap-2 mb-4">
                        <Badge variant="outline" className="text-xs">
                            {t.currentPlan}: {TIER_DISPLAY[tier] ?? tier}
                        </Badge>
                        <ArrowRight className="h-3 w-3 text-muted-foreground" />
                        <Badge className="text-xs bg-primary text-primary-foreground">
                            {TIER_DISPLAY[requiredTier]}
                        </Badge>
                    </div>

                    {/* Benefits list */}
                    {benefits && benefits.length > 0 && (
                        <ul className="text-sm text-left max-w-xs mx-auto space-y-1.5 mb-5">
                            {benefits.map((b, i) => (
                                <li key={i} className="flex items-start gap-2">
                                    <span className="text-primary mt-0.5">✓</span>
                                    <span className="text-muted-foreground">{b}</span>
                                </li>
                            ))}
                        </ul>
                    )}

                    {showCountdown && countdownDisplay && (
                        <div className="flex items-center justify-center gap-2 text-sm mb-4">
                            <Clock className="h-3.5 w-3.5 text-muted-foreground" />
                            <span className="text-muted-foreground">{t.rateLimited}</span>
                            <span className="font-mono font-bold text-primary">{countdownDisplay}</span>
                        </div>
                    )}

                    <Link href={checkoutUrl}>
                        <Button className="gap-2 group">
                            <Sparkles className="h-4 w-4" />
                            {ctaLabel}
                            <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
                        </Button>
                    </Link>
                </CardContent>
            </Card>
        );
    }

    // variant === 'overlay'
    return (
        <div className={`relative rounded-lg overflow-hidden ${className}`}>
            <div className="absolute inset-0 bg-background/80 backdrop-blur-sm z-10 flex items-center justify-center">
                <div className="text-center p-6 max-w-sm">
                    <div className="mx-auto rounded-full bg-primary/10 p-3 w-fit mb-3">
                        <Lock className="h-5 w-5 text-primary" />
                    </div>
                    <h3 className="text-base font-bold mb-1">{title}</h3>
                    <p className="text-sm text-muted-foreground mb-4">
                        {feature ?? subtitle}
                    </p>
                    <Link href={checkoutUrl}>
                        <Button size="sm" className="gap-1">
                            <Sparkles className="h-3 w-3" />
                            {ctaLabel}
                        </Button>
                    </Link>
                </div>
            </div>
        </div>
    );
}
