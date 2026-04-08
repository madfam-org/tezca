'use client';

import { useState, useEffect } from 'react';
import { Bell, X, Check, Loader2 } from 'lucide-react';
import { Button, Badge, Card, CardContent } from '@tezca/ui';
import { useLang } from '@/components/providers/LanguageContext';
import { useAuth } from '@/components/providers/AuthContext';
import { API_BASE_URL } from '@/lib/config';
import { getFeatureLabel } from '@/lib/feature-labels';
import { trackEvent } from '@/lib/analytics/posthog';

type InterestGateVariant = 'inline' | 'overlay' | 'card' | 'toast';

const content = {
    es: {
        comingSoon: 'Disponible pronto',
        notifyMe: 'Avísame cuando esté listo',
        submit: 'Notificarme',
        success: '¡Listo! Te avisaremos.',
        alreadyRegistered: 'Ya te notificaremos.',
        error: 'Error al registrar. Intenta de nuevo.',
        emailPlaceholder: 'tu@correo.com',
        dismiss: 'Cerrar',
        useCaseLabel: '¿Para qué lo usarías?',
        useCases: {
            research: 'Investigación',
            work: 'Trabajo',
            personal: 'Personal',
            government: 'Gobierno',
            education: 'Educación',
        },
        wishlistLabel: '¿Qué necesitas de Tezca?',
        wishlistPlaceholder: 'Las funciones que más te importan...',
        tellMore: 'Cuéntanos más',
        tellMorePrompt: '¿Cómo usarías Tezca en tu trabajo diario?',
        tellMoreSubmit: 'Enviar',
        tellMoreSuccess: '¡Gracias por tus comentarios!',
    },
    en: {
        comingSoon: 'Coming soon',
        notifyMe: 'Notify me when it\'s ready',
        submit: 'Notify me',
        success: 'Done! We\'ll let you know.',
        alreadyRegistered: 'You\'re already on the list.',
        error: 'Error registering. Please try again.',
        emailPlaceholder: 'you@email.com',
        dismiss: 'Dismiss',
        useCaseLabel: 'What would you use it for?',
        useCases: {
            research: 'Research',
            work: 'Work',
            personal: 'Personal',
            government: 'Government',
            education: 'Education',
        },
        wishlistLabel: 'What do you need from Tezca?',
        wishlistPlaceholder: 'The features that matter most to you...',
        tellMore: 'Tell us more',
        tellMorePrompt: 'How would you use Tezca in your daily workflow?',
        tellMoreSubmit: 'Submit',
        tellMoreSuccess: 'Thanks for your feedback!',
    },
    nah: {
        comingSoon: 'Hualaz niman',
        notifyMe: 'Xinechtlanonotza',
        submit: 'Xinechtlanonotza',
        success: 'Ōmochiuh! Timitznonotzazqueh.',
        alreadyRegistered: 'Ye timotocāyōtia.',
        error: 'Tlahtlacōlli. Xicyeyeco ōccēppa.',
        emailPlaceholder: 'tehuatl@correo.com',
        dismiss: 'Xictlātia',
        useCaseLabel: 'Tlein ic ticchīhuaz?',
        useCases: {
            research: 'Tlatemoliztli',
            work: 'Tequitl',
            personal: 'Tēhuatl',
            government: 'Tlatocayotl',
            education: 'Tlamachtiliztli',
        },
        wishlistLabel: 'Tlein ticnequi?',
        wishlistPlaceholder: 'In tlamantli tlen ohcuēli mitzpactia...',
        tellMore: 'Xitech ilhui occequi',
        tellMorePrompt: 'Quēnin ticchīhuaz Tezca mo tequitl?',
        tellMoreSubmit: 'Xictitlani',
        tellMoreSuccess: 'Tlazohcāmati!',
    },
};

type SubmitState = 'idle' | 'submitting' | 'success' | 'error' | 'already_registered';

interface InterestGateProps {
    variant: InterestGateVariant;
    featureKey: string;
    featureLabel?: string;
    showUseCase?: boolean;
    showWishlist?: boolean;
    sourcePage?: string;
    benefits?: string[];
    onDismiss?: () => void;
    onSubmitted?: () => void;
    onTellMore?: () => void;
    className?: string;
}

export function InterestGate({
    variant,
    featureKey,
    featureLabel,
    showUseCase = false,
    showWishlist = false,
    sourcePage = '',
    benefits,
    onDismiss,
    onSubmitted,
    onTellMore,
    className = '',
}: InterestGateProps) {
    const { lang } = useLang();
    const { email: userEmail, userId, isAuthenticated } = useAuth();
    const t = content[lang];

    const [email, setEmail] = useState(userEmail ?? '');
    const [useCase, setUseCase] = useState('');
    const [wishlist, setWishlist] = useState('');
    const [state, setState] = useState<SubmitState>('idle');
    const [dismissed, setDismissed] = useState(false);
    const [tellMoreOpen, setTellMoreOpen] = useState(false);
    const [tellMoreText, setTellMoreText] = useState('');
    const [tellMoreState, setTellMoreState] = useState<'idle' | 'submitting' | 'success'>('idle');

    const label = featureLabel ?? getFeatureLabel(featureKey, lang);

    useEffect(() => {
        trackEvent('interest_gate.shown', { variant, feature_key: featureKey });
    // eslint-disable-next-line react-hooks/exhaustive-deps -- track once on mount
    }, []);

    // Sync email from auth
    useEffect(() => {
        if (userEmail && !email) setEmail(userEmail);
    }, [userEmail, email]);

    if (dismissed) return null;

    const handleDismiss = () => {
        setDismissed(true);
        trackEvent('interest_gate.dismissed', { variant, feature_key: featureKey });
        onDismiss?.();
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!email || state === 'submitting') return;

        setState('submitting');
        trackEvent('interest_gate.submitted', {
            variant,
            feature_key: featureKey,
            source_page: sourcePage,
            use_case: useCase,
        });

        const res = await fetch(`${API_BASE_URL}/interest/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                email,
                feature_key: featureKey,
                use_case: useCase,
                wishlist,
                janua_user_id: userId ?? '',
                source_page: sourcePage,
            }),
        }).catch(() => null);

        if (!res) {
            setState('error');
            return;
        }

        if (res.status === 201) {
            setState('success');
            if (featureKey === 'early_access') {
                trackEvent('funnel.premium_interest', { source_page: sourcePage });
            }
            onSubmitted?.();
        } else if (res.status === 200) {
            setState('already_registered');
            onSubmitted?.();
        } else {
            setState('error');
        }
    };

    const successMessage = state === 'already_registered' ? t.alreadyRegistered : t.success;
    const isComplete = state === 'success' || state === 'already_registered';

    // --- Shared form elements ---
    const emailInput = (
        <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder={t.emailPlaceholder}
            required
            className="flex-1 min-w-0 rounded-md border border-input bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/30"
        />
    );

    const useCaseSelect = showUseCase ? (
        <select
            value={useCase}
            onChange={(e) => setUseCase(e.target.value)}
            className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm text-muted-foreground"
        >
            <option value="">{t.useCaseLabel}</option>
            {Object.entries(t.useCases).map(([key, label]) => (
                <option key={key} value={key}>{label}</option>
            ))}
        </select>
    ) : null;

    const wishlistTextarea = showWishlist && (variant === 'card' || variant === 'overlay') ? (
        <textarea
            value={wishlist}
            onChange={(e) => setWishlist(e.target.value)}
            placeholder={t.wishlistPlaceholder}
            maxLength={2000}
            rows={2}
            className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm placeholder:text-muted-foreground resize-none focus:outline-none focus:ring-2 focus:ring-primary/30"
            aria-label={t.wishlistLabel}
        />
    ) : null;

    const handleTellMore = () => {
        trackEvent('interest_gate.tell_more_clicked', { feature_key: featureKey });
        if (onTellMore) {
            onTellMore();
            return;
        }
        setTellMoreOpen(true);
    };

    const handleTellMoreSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!tellMoreText.trim() || tellMoreState === 'submitting') return;
        setTellMoreState('submitting');

        const res = await fetch(`${API_BASE_URL}/interest/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                email,
                feature_key: featureKey,
                wishlist: tellMoreText.trim(),
                janua_user_id: userId ?? '',
                source_page: sourcePage,
            }),
        }).catch(() => null);

        if (res && res.status <= 201) {
            setTellMoreState('success');
            trackEvent('interest_gate.wishlist_submitted', {
                feature_key: featureKey,
                wishlist_length: tellMoreText.trim().length,
            });
        } else {
            setTellMoreState('idle');
        }
    };

    const tellMoreSection = isComplete && (variant === 'card' || variant === 'overlay') ? (
        <div className="mt-3">
            {tellMoreState === 'success' ? (
                <p className="text-sm text-primary">{t.tellMoreSuccess}</p>
            ) : tellMoreOpen ? (
                <form onSubmit={handleTellMoreSubmit} className="space-y-2">
                    <textarea
                        value={tellMoreText}
                        onChange={(e) => setTellMoreText(e.target.value)}
                        placeholder={t.tellMorePrompt}
                        maxLength={2000}
                        rows={3}
                        className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm placeholder:text-muted-foreground resize-none focus:outline-none focus:ring-2 focus:ring-primary/30"
                    />
                    <Button type="submit" size="sm" disabled={tellMoreState === 'submitting' || !tellMoreText.trim()}>
                        {tellMoreState === 'submitting' ? (
                            <Loader2 className="h-3 w-3 animate-spin" />
                        ) : null}
                        {t.tellMoreSubmit}
                    </Button>
                </form>
            ) : (
                <button
                    onClick={handleTellMore}
                    className="text-sm text-primary hover:text-primary/80 underline underline-offset-2 transition-colors"
                >
                    {t.tellMore}
                </button>
            )}
        </div>
    ) : null;

    const submitButton = (
        <Button type="submit" size="sm" disabled={state === 'submitting' || !email} className="gap-1 shrink-0">
            {state === 'submitting' ? (
                <Loader2 className="h-3 w-3 animate-spin" />
            ) : (
                <Bell className="h-3 w-3" />
            )}
            {t.submit}
        </Button>
    );

    // --- Variants ---

    if (variant === 'toast') {
        return (
            <div className={`fixed bottom-4 right-4 z-50 max-w-[min(24rem,calc(100vw-2rem))] animate-in slide-in-from-bottom-5 fade-in duration-300 ${className}`}>
                <Card className="border-primary/20 shadow-lg">
                    <CardContent className="p-4">
                        <div className="flex items-start gap-3">
                            <div className="rounded-full bg-primary/10 p-2 shrink-0">
                                <Bell className="h-4 w-4 text-primary" />
                            </div>
                            <div className="flex-1 min-w-0">
                                <div className="flex items-center gap-2 mb-1">
                                    <Badge variant="outline" className="text-xs">{t.comingSoon}</Badge>
                                </div>
                                <p className="text-sm font-medium mb-2">{label}</p>
                                {isComplete ? (
                                    <div className="flex items-center gap-1.5 text-sm text-primary">
                                        <Check className="h-3.5 w-3.5" />
                                        {successMessage}
                                    </div>
                                ) : (
                                    <form onSubmit={handleSubmit} className="flex gap-2">
                                        {emailInput}
                                        {submitButton}
                                    </form>
                                )}
                                {state === 'error' && (
                                    <p className="text-xs text-destructive mt-1">{t.error}</p>
                                )}
                            </div>
                            <button
                                onClick={handleDismiss}
                                className="text-muted-foreground hover:text-foreground shrink-0 p-1.5"
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
                <div className="flex items-center gap-2 mb-2">
                    <Bell className="h-4 w-4 text-primary shrink-0" />
                    <Badge variant="outline" className="text-xs">{t.comingSoon}</Badge>
                    <span className="text-sm font-medium">{label}</span>
                </div>
                {isComplete ? (
                    <div className="flex items-center gap-1.5 text-sm text-primary">
                        <Check className="h-3.5 w-3.5" />
                        {successMessage}
                    </div>
                ) : (
                    <form onSubmit={handleSubmit} className="flex flex-col sm:flex-row gap-2">
                        {emailInput}
                        {submitButton}
                    </form>
                )}
                {state === 'error' && (
                    <p className="text-xs text-destructive mt-1">{t.error}</p>
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
                        <Bell className="h-6 w-6 text-primary" />
                    </div>
                    <Badge variant="outline" className="text-xs mb-3">{t.comingSoon}</Badge>
                    <h3 className="text-lg font-bold mb-2">{label}</h3>
                    <p className="text-sm text-muted-foreground mb-4 max-w-md mx-auto">
                        {t.notifyMe}
                    </p>

                    {benefits && benefits.length > 0 && (
                        <ul className="text-sm text-left max-w-xs mx-auto space-y-1.5 mb-5">
                            {benefits.map((b, i) => (
                                <li key={i} className="flex items-start gap-2">
                                    <span className="text-primary mt-0.5">&#10003;</span>
                                    <span className="text-muted-foreground">{b}</span>
                                </li>
                            ))}
                        </ul>
                    )}

                    {isComplete ? (
                        <div>
                            <div className="flex items-center justify-center gap-1.5 text-sm text-primary">
                                <Check className="h-4 w-4" />
                                {successMessage}
                            </div>
                            {tellMoreSection}
                        </div>
                    ) : (
                        <form onSubmit={handleSubmit} className="max-w-sm mx-auto space-y-3">
                            {emailInput}
                            {useCaseSelect}
                            {wishlistTextarea}
                            {submitButton}
                        </form>
                    )}
                    {state === 'error' && (
                        <p className="text-xs text-destructive mt-2">{t.error}</p>
                    )}
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
                        <Bell className="h-5 w-5 text-primary" />
                    </div>
                    <Badge variant="outline" className="text-xs mb-2">{t.comingSoon}</Badge>
                    <h3 className="text-base font-bold mb-1">{label}</h3>
                    <p className="text-sm text-muted-foreground mb-4">
                        {t.notifyMe}
                    </p>
                    {isComplete ? (
                        <div>
                            <div className="flex items-center justify-center gap-1.5 text-sm text-primary">
                                <Check className="h-4 w-4" />
                                {successMessage}
                            </div>
                            {tellMoreSection}
                        </div>
                    ) : (
                        <form onSubmit={handleSubmit} className="space-y-2">
                            {emailInput}
                            {wishlistTextarea}
                            {submitButton}
                        </form>
                    )}
                    {state === 'error' && (
                        <p className="text-xs text-destructive mt-1">{t.error}</p>
                    )}
                </div>
            </div>
        </div>
    );
}
