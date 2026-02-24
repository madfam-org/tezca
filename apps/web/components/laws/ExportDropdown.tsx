'use client';

import { useState, useRef, useEffect } from 'react';
import { Download, FileText, FileDown, Code, BookOpen, Braces, FileSpreadsheet, Loader2, Lock } from 'lucide-react';
import { useLang } from '@/components/providers/LanguageContext';
import { useAuth, type UserTier } from '@/components/providers/AuthContext';
import { API_BASE_URL } from '@/lib/config';

type ExportFormat = 'txt' | 'pdf' | 'latex' | 'docx' | 'epub' | 'json';

const FORMAT_TIERS: Record<ExportFormat, UserTier> = {
    txt: 'anon',
    pdf: 'free',
    latex: 'premium',
    docx: 'premium',
    epub: 'premium',
    json: 'premium',
};

const TIER_RANK: Record<UserTier, number> = { anon: 0, free: 1, premium: 2 };

const content = {
    es: {
        download: 'Descargar',
        downloading: 'Descargando...',
        error: 'Error al descargar',
        loginRequired: 'Inicia sesión para descargar en este formato',
        premiumRequired: 'Formato Premium — Actualiza tu cuenta',
        rateLimited: 'Has alcanzado el límite. Intenta de nuevo en',
        minutes: 'minutos',
        accountBadge: 'Cuenta',
        premiumBadge: 'Premium',
        formats: {
            txt: { label: 'Descargar TXT', desc: 'Texto plano' },
            pdf: { label: 'Descargar PDF', desc: 'Documento formateado' },
            latex: { label: 'Descargar LaTeX', desc: 'Documento .tex compilable' },
            docx: { label: 'Descargar DOCX', desc: 'Documento Word' },
            epub: { label: 'Descargar EPUB', desc: 'Libro electrónico' },
            json: { label: 'Descargar JSON', desc: 'Datos estructurados' },
        },
    },
    en: {
        download: 'Download',
        downloading: 'Downloading...',
        error: 'Download error',
        loginRequired: 'Sign in to download in this format',
        premiumRequired: 'Premium format — Upgrade your account',
        rateLimited: 'Rate limit reached. Try again in',
        minutes: 'minutes',
        accountBadge: 'Account',
        premiumBadge: 'Premium',
        formats: {
            txt: { label: 'Download TXT', desc: 'Plain text' },
            pdf: { label: 'Download PDF', desc: 'Formatted document' },
            latex: { label: 'Download LaTeX', desc: 'Compilable .tex file' },
            docx: { label: 'Download DOCX', desc: 'Word document' },
            epub: { label: 'Download EPUB', desc: 'E-book' },
            json: { label: 'Download JSON', desc: 'Structured data' },
        },
    },
    nah: {
        download: 'Xictēmōhui',
        downloading: 'Motēmoa...',
        error: 'Tlahtlacōlli',
        loginRequired: 'Xicalaqui ic tictēmōz inin tlahtōlli',
        premiumRequired: 'Premium tlahtōlli — Xiccuēpa mocuenta',
        rateLimited: 'Otitlāmic in tlanāhuatīlli. Xicchiya',
        minutes: 'minutos',
        accountBadge: 'Cuenta',
        premiumBadge: 'Premium',
        formats: {
            txt: { label: 'Xictēmōhui TXT', desc: 'Āmatl zan tlahtolli' },
            pdf: { label: 'Xictēmōhui PDF', desc: 'Āmatl tlachīhualli' },
            latex: { label: 'Xictēmōhui LaTeX', desc: 'Āmatl .tex' },
            docx: { label: 'Xictēmōhui DOCX', desc: 'Āmatl Word' },
            epub: { label: 'Xictēmōhui EPUB', desc: 'Āmoxtli digital' },
            json: { label: 'Xictēmōhui JSON', desc: 'Tlahtōlli tlanahuatīlli' },
        },
    },
};

interface FormatConfig {
    format: ExportFormat;
    icon: React.ReactNode;
    tierBadge: 'account' | 'premium' | null;
}

const FORMAT_LIST: FormatConfig[] = [
    { format: 'txt', icon: <FileText className="h-4 w-4 text-blue-500" />, tierBadge: null },
    { format: 'pdf', icon: <FileDown className="h-4 w-4 text-red-500" />, tierBadge: 'account' },
    { format: 'latex', icon: <Code className="h-4 w-4 text-purple-500" />, tierBadge: 'premium' },
    { format: 'docx', icon: <FileSpreadsheet className="h-4 w-4 text-green-500" />, tierBadge: 'premium' },
    { format: 'epub', icon: <BookOpen className="h-4 w-4 text-orange-500" />, tierBadge: 'premium' },
    { format: 'json', icon: <Braces className="h-4 w-4 text-gray-500" />, tierBadge: 'premium' },
];

interface ExportDropdownProps {
    lawId: string;
}

export function ExportDropdown({ lawId }: ExportDropdownProps) {
    const { lang } = useLang();
    const { isAuthenticated, tier, loginUrl } = useAuth();
    const t = content[lang];
    const [open, setOpen] = useState(false);
    const [loading, setLoading] = useState<ExportFormat | null>(null);
    const [message, setMessage] = useState<string | null>(null);
    const dropdownRef = useRef<HTMLDivElement>(null);

    // Close on click outside
    useEffect(() => {
        function handleClickOutside(e: MouseEvent) {
            if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
                setOpen(false);
                setMessage(null);
            }
        }
        if (open) {
            document.addEventListener('mousedown', handleClickOutside);
            return () => document.removeEventListener('mousedown', handleClickOutside);
        }
    }, [open]);

    const canAccess = (format: ExportFormat): boolean => {
        const requiredTier = FORMAT_TIERS[format];
        return TIER_RANK[tier] >= TIER_RANK[requiredTier];
    };

    const handleClick = async (format: ExportFormat) => {
        setMessage(null);

        // Check tier access on client side
        if (!canAccess(format)) {
            if (!isAuthenticated) {
                setMessage(t.loginRequired);
            } else {
                setMessage(t.premiumRequired);
            }
            return;
        }

        setLoading(format);
        const headers: Record<string, string> = {};

        // Include JWT if available
        const token = typeof document !== 'undefined'
            ? document.cookie.match(/(?:^|;\s*)janua_token=([^;]*)/)?.[1]
            : null;
        if (token) {
            headers['Authorization'] = `Bearer ${decodeURIComponent(token)}`;
        } else if (typeof localStorage !== 'undefined') {
            const lsToken = localStorage.getItem('janua_token');
            if (lsToken) headers['Authorization'] = `Bearer ${lsToken}`;
        }

        try {
            const url = `${API_BASE_URL}/laws/${lawId}/export/${format}/`;
            const res = await fetch(url, { headers });

            if (res.status === 429) {
                const data = await res.json().catch(() => ({ retry_after: 300 }));
                const mins = Math.ceil((data.retry_after || 300) / 60);
                setMessage(`${t.rateLimited} ${mins} ${t.minutes}`);
                return;
            }
            if (res.status === 403) {
                const data = await res.json().catch(() => ({}));
                if (data.required_tier === 'free' || !isAuthenticated) {
                    setMessage(t.loginRequired);
                } else {
                    setMessage(t.premiumRequired);
                }
                return;
            }
            if (!res.ok) throw new Error(`HTTP ${res.status}`);

            const blob = await res.blob();
            const downloadUrl = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = downloadUrl;
            const ext = format === 'latex' ? 'tex' : format;
            a.download = `${lawId.replace(/\//g, '_')}.${ext}`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(downloadUrl);
            setOpen(false);
            setMessage(null);
        } catch (err) {
            console.error(`Export ${format} failed:`, err);
            setMessage(t.error);
        } finally {
            setLoading(null);
        }
    };

    return (
        <div className="relative" ref={dropdownRef}>
            <button
                onClick={() => { setOpen(!open); setMessage(null); }}
                className="inline-flex items-center gap-2 rounded-md border border-input bg-background px-4 py-2 text-sm font-medium hover:bg-accent hover:text-accent-foreground transition-colors print:hidden"
                aria-expanded={open}
                aria-haspopup="true"
            >
                <Download className="h-4 w-4" aria-hidden="true" />
                <span className="hidden sm:inline">{t.download}</span>
            </button>

            {open && (
                <div className="absolute right-0 top-full mt-1 w-56 max-w-[calc(100vw-2rem)] rounded-md border bg-popover shadow-md z-50">
                    <div className="p-1">
                        {FORMAT_LIST.map(({ format, icon, tierBadge }) => {
                            const accessible = canAccess(format);
                            const fmtContent = t.formats[format];
                            return (
                                <button
                                    key={format}
                                    onClick={() => handleClick(format)}
                                    disabled={loading !== null}
                                    className="flex w-full items-center gap-3 rounded-sm px-3 py-2 text-sm hover:bg-accent transition-colors disabled:opacity-50"
                                >
                                    {loading === format ? (
                                        <Loader2 className="h-4 w-4 animate-spin" />
                                    ) : !accessible ? (
                                        <Lock className="h-4 w-4 text-muted-foreground" />
                                    ) : (
                                        icon
                                    )}
                                    <div className="text-left flex-1">
                                        <div className="font-medium flex items-center gap-2">
                                            {fmtContent.label}
                                            {tierBadge === 'account' && (
                                                <span className="text-xs leading-none bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300 px-1.5 py-0.5 rounded">
                                                    {t.accountBadge}
                                                </span>
                                            )}
                                            {tierBadge === 'premium' && (
                                                <span className="text-xs leading-none bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300 px-1.5 py-0.5 rounded">
                                                    {t.premiumBadge}
                                                </span>
                                            )}
                                        </div>
                                        <div className="text-xs text-muted-foreground">{fmtContent.desc}</div>
                                    </div>
                                </button>
                            );
                        })}
                    </div>

                    {/* Inline message for auth/rate-limit feedback */}
                    {message && (
                        <div className="border-t px-3 py-2 text-xs text-muted-foreground">
                            <p>{message}</p>
                            {!isAuthenticated && message === t.loginRequired && (
                                <a
                                    href={loginUrl}
                                    className="text-primary underline hover:no-underline mt-1 inline-block"
                                >
                                    {lang === 'en' ? 'Sign in' : lang === 'nah' ? 'Xicalaqui' : 'Iniciar sesión'}
                                </a>
                            )}
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}
