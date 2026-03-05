'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { Lock, ArrowRight, Clock, Sparkles, X } from 'lucide-react';
import { Button, Badge, Card, CardContent } from '@tezca/ui';
import { useLang } from '@/components/providers/LanguageContext';
import { useAuth, type UserTier } from '@/components/providers/AuthContext';
import { getCheckoutUrl } from '@/lib/billing';

type TierGateVariant = 'inline' | 'overlay' | 'card' | 'toast';
type RequiredTier = 'essentials' | 'community' | 'pro';

const content = {
    es: {
        unlockTitle: {
            essentials: 'Crea tu cuenta gratuita',
            community: 'Desbloquea más con Community',
            pro: 'Desbloquea todo con Tezca Pro',
        },
        unlockSubtitle: {
            essentials: 'Accede a más formatos de descarga y funciones avanzadas',
            community: 'Búsqueda avanzada, acceso a API y descargas masivas',
            pro: 'Todos los formatos, análisis avanzado y soporte prioritario',
        },
        cta: {
            essentials: 'Empieza gratis',
            community: 'Mejora tu plan',
            pro: 'Mejora a Pro',
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
            essentials: 'Create your free account',
            community: 'Unlock more with Community',
            pro: 'Unlock everything with Tezca Pro',
        },
        unlockSubtitle: {
            essentials: 'Access more download formats and advanced features',
            community: 'Advanced search, API access, and bulk downloads',
            pro: 'All formats, advanced analytics, and priority support',
        },
        cta: {
            essentials: 'Start free',
            community: 'Upgrade plan',
            pro: 'Upgrade to Pro',
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
            essentials: 'Xictlālia mocuenta',
            community: 'Xictlapo achi ica Community',
            pro: 'Xictlapo mochi ica Tezca Pro',
        },
        unlockSubtitle: {
            essentials: 'Xicāci achi tēmōhuiliztli ihuan tlachīhualiztli',
            community: 'Tlatemoliztli huēyi, API, ihuan mīec tēmōhuiliztli',
            pro: 'Mochi tlahtōlli, tlanextīliztli ihuan tēpalēhuiliztli',
        },
        cta: {
            essentials: 'Xipēhua',
            community: 'Xicmelahua mocuenta',
            pro: 'Xicmelahua ic Pro',
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
    essentials: 'Essentials',
    community: 'Community',
    pro: 'Pro',
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

    const targetTier = !isAuthenticated ? 'essentials' : requiredTier;
    const checkoutUrl = isAuthenticated
        ? getCheckoutUrl(requiredTier === 'essentials' ? 'community' : requiredTier, userId ?? undefined, typeof window !== 'undefined' ? window.location.href : undefined)
        : '/login';
    const ctaLabel = t.cta[targetTier as keyof typeof t.cta] ?? t.cta.pro;
    const title = t.unlockTitle[targetTier as keyof typeof t.unlockTitle] ?? t.unlockTitle.pro;
    const subtitle = t.unlockSubtitle[targetTier as keyof typeof t.unlockSubtitle] ?? t.unlockSubtitle.pro;

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
