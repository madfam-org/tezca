'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { Protect } from '@janua/nextjs';
import { CreditCard, ExternalLink, Receipt, Settings } from 'lucide-react';
import { Button } from '@tezca/ui';
import { useAuth } from '@/components/providers/AuthContext';
import { useLang } from '@/components/providers/LanguageContext';
import { MONETIZATION_ENABLED } from '@/lib/config';
import { getCheckoutUrl, hasPaidAccess } from '@/lib/billing';
import { InterestGate } from '@/components/InterestGate';
import { TierComparison } from '@/components/TierComparison';

/**
 * /cuenta/billing — subscription + payment history.
 *
 * Track 4 of FEATURE_PARITY_PLAN_2026-04-27 §3.3. Tezca calls Dhanam for
 * everything billing-related — never holds Stripe keys, never minted
 * subscriptions itself. The Tezca side of this is purely the customer-
 * facing surface that links into Dhanam's checkout + customer portal.
 *
 * Two display modes:
 *   1. MONETIZATION_ENABLED=false (default) — Show "billing not yet active"
 *      InterestGate. Customers can register interest; no checkout link.
 *   2. MONETIZATION_ENABLED=true — Show current plan, customer-portal link,
 *      and (when paid) recent invoices fetched from Dhanam.
 */

const content = {
    es: {
        title: 'Facturación',
        currentPlan: 'Plan actual',
        upgrade: 'Cambiar de plan',
        managePayment: 'Administrar pago en Dhanam',
        billingPortal: 'Abrir portal de cliente',
        invoices: 'Historial de facturas',
        invoicesDesc: 'Tus últimos pagos y facturas CFDI 4.0',
        loadingInvoices: 'Cargando facturas...',
        noInvoices: 'Sin facturas aún. Cuando contrates un plan aparecerán aquí.',
        invoiceDate: 'Fecha',
        invoiceAmount: 'Monto',
        invoiceStatus: 'Estado',
        invoiceDownload: 'Descargar',
        cfdiBadge: 'CFDI 4.0',
        statusPaid: 'Pagado',
        statusPending: 'Pendiente',
        statusFailed: 'Fallido',
        notActiveTitle: 'La facturación aún no está activa',
        notActiveBody: 'Estamos preparando los planes pagados. Regístrate para enterarte cuando estén disponibles.',
        notActiveFeatureKey: 'billing',
        helpText: '¿Preguntas sobre facturación? Escríbenos a',
        helpEmail: 'soporte@tezca.mx',
    },
    en: {
        title: 'Billing',
        currentPlan: 'Current plan',
        upgrade: 'Change plan',
        managePayment: 'Manage payment in Dhanam',
        billingPortal: 'Open customer portal',
        invoices: 'Invoice history',
        invoicesDesc: 'Your recent payments and CFDI 4.0 invoices',
        loadingInvoices: 'Loading invoices...',
        noInvoices: 'No invoices yet. They will appear here once you start a paid plan.',
        invoiceDate: 'Date',
        invoiceAmount: 'Amount',
        invoiceStatus: 'Status',
        invoiceDownload: 'Download',
        cfdiBadge: 'CFDI 4.0',
        statusPaid: 'Paid',
        statusPending: 'Pending',
        statusFailed: 'Failed',
        notActiveTitle: 'Billing is not yet active',
        notActiveBody: 'Paid plans are coming soon. Register to be notified when they go live.',
        notActiveFeatureKey: 'billing',
        helpText: 'Questions about billing? Email us at',
        helpEmail: 'soporte@tezca.mx',
    },
    nah: {
        title: 'Tlatlaxtlahuīliztli',
        currentPlan: 'Notlaxtlahuīl ic axcān',
        upgrade: 'Xicpatla notlaxtlahuīl',
        managePayment: 'Xicyectlali tlaxtlahuīliztli ic Dhanam',
        billingPortal: 'Xictlapo notlatequi',
        invoices: 'Notlatlaxtlahuīlhuān',
        invoicesDesc: 'Mochi tlin oticxtlahui',
        loadingInvoices: 'Tētēmoa tlatlaxtlahuīlli...',
        noInvoices: 'Ahmo oncah tlatlaxtlahuīlli. Quema tic tlatlaxtlahuīz cualli mocahuaz nican.',
        invoiceDate: 'Tonalli',
        invoiceAmount: 'Quēxquich',
        invoiceStatus: 'Quēn cah',
        invoiceDownload: 'Xictemo',
        cfdiBadge: 'CFDI 4.0',
        statusPaid: 'Otlatlaxtlahuīloc',
        statusPending: 'Mochiyaz',
        statusFailed: 'Ahmo otlatlaxtlahuīloc',
        notActiveTitle: 'Tlatlaxtlahuīliztli ahmocān',
        notActiveBody: 'Tic chiuhtihuitz tlaxtlahuīlmeh. Xicalaqui ic tic mati quēman.',
        notActiveFeatureKey: 'billing',
        helpText: '¿Tlein ticnequi? Xitech ilhui',
        helpEmail: 'soporte@tezca.mx',
    },
};

interface DhanamInvoice {
    id: string;
    issued_at: string;        // ISO 8601
    amount_mxn: number;
    status: 'paid' | 'pending' | 'failed';
    pdf_url?: string;
    cfdi_xml_url?: string;
}

const DHANAM_API_BASE =
    process.env.NEXT_PUBLIC_DHANAM_API_URL || 'https://api.dhan.am';

export default function BillingPage() {
    const { lang } = useLang();
    const t = content[lang];

    return (
        <Protect redirectTo="/login">
            <main className="mx-auto max-w-3xl px-4 py-10 sm:px-6">
                <h1 className="text-2xl font-bold mb-8">{t.title}</h1>
                {MONETIZATION_ENABLED ? <ActiveBilling t={t} lang={lang} /> : <InactiveBilling t={t} />}

                <div className="mt-10 text-sm text-muted-foreground">
                    {t.helpText}{' '}
                    <a href={`mailto:${t.helpEmail}`} className="text-primary hover:underline">
                        {t.helpEmail}
                    </a>
                </div>
            </main>
        </Protect>
    );
}

// ── Active billing surface ──────────────────────────────────────────────

function ActiveBilling({ t, lang }: { t: typeof content.es; lang: string }) {
    const { tier, userId } = useAuth();
    const isPaid = hasPaidAccess(tier);
    const portalUrl =
        userId && isPaid
            ? `${DHANAM_API_BASE}/v1/portal?product=tezca&user_id=${encodeURIComponent(userId)}`
            : null;

    return (
        <>
            <CurrentPlanCard t={t} />

            {/* Manage payment — Dhanam-hosted portal */}
            {portalUrl && (
                <div className="rounded-lg border border-border bg-background p-6 mb-6">
                    <div className="flex items-start gap-3">
                        <div className="rounded-full bg-primary/10 p-2 shrink-0">
                            <Settings className="h-5 w-5 text-primary" />
                        </div>
                        <div className="flex-1">
                            <p className="font-semibold mb-1">{t.managePayment}</p>
                            <p className="text-sm text-muted-foreground mb-3">
                                Update payment method, cancel subscription, or download invoices.
                            </p>
                            <a href={portalUrl} target="_blank" rel="noopener noreferrer">
                                <Button variant="outline" size="sm" className="gap-2">
                                    {t.billingPortal}
                                    <ExternalLink className="h-3.5 w-3.5" />
                                </Button>
                            </a>
                        </div>
                    </div>
                </div>
            )}

            {/* Upgrade prompt for unpaid */}
            {!isPaid && (
                <div className="mb-8">
                    <h2 className="text-lg font-bold mb-4">{t.upgrade}</h2>
                    <TierComparison />
                </div>
            )}

            {/* Invoices */}
            {isPaid && <InvoicesSection t={t} lang={lang} userId={userId} />}
        </>
    );
}

function CurrentPlanCard({ t }: { t: typeof content.es }) {
    const { tier } = useAuth();
    return (
        <div className="rounded-lg border border-border bg-background p-6 mb-6">
            <div className="flex items-start justify-between gap-4">
                <div>
                    <p className="text-sm text-muted-foreground mb-1">{t.currentPlan}</p>
                    <p className="text-xl font-semibold capitalize">{tier}</p>
                </div>
                <Link href="/precios">
                    <Button variant="outline" size="sm" className="gap-2">
                        <CreditCard className="h-4 w-4" />
                        {t.upgrade}
                    </Button>
                </Link>
            </div>
        </div>
    );
}

function InvoicesSection({
    t,
    lang,
    userId,
}: {
    t: typeof content.es;
    lang: string;
    userId: string | null;
}) {
    const [invoices, setInvoices] = useState<DhanamInvoice[] | null>(null);
    const [loading, setLoading] = useState(true);
    const locale = lang === 'en' ? 'en-US' : 'es-MX';

    useEffect(() => {
        if (!userId) {
            setLoading(false);
            return;
        }
        let cancelled = false;
        const ctrl = new AbortController();
        fetch(
            `${DHANAM_API_BASE}/v1/invoices?product=tezca&user_id=${encodeURIComponent(userId)}`,
            { signal: ctrl.signal },
        )
            .then((r) => (r.ok ? r.json() : { invoices: [] }))
            .then((data) => {
                if (!cancelled) {
                    setInvoices((data?.invoices as DhanamInvoice[]) ?? []);
                    setLoading(false);
                }
            })
            .catch(() => {
                if (!cancelled) {
                    setInvoices([]);
                    setLoading(false);
                }
            });
        return () => {
            cancelled = true;
            ctrl.abort();
        };
    }, [userId]);

    return (
        <div className="rounded-lg border border-border bg-background p-6">
            <div className="flex items-center gap-2 mb-1">
                <Receipt className="h-5 w-5 text-primary" />
                <h2 className="text-lg font-bold">{t.invoices}</h2>
            </div>
            <p className="text-sm text-muted-foreground mb-4">{t.invoicesDesc}</p>

            {loading ? (
                <div className="py-8 text-center text-sm text-muted-foreground">
                    {t.loadingInvoices}
                </div>
            ) : invoices && invoices.length > 0 ? (
                <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                        <thead>
                            <tr className="border-b border-border text-left text-muted-foreground">
                                <th className="py-2 pr-4 font-medium">{t.invoiceDate}</th>
                                <th className="py-2 pr-4 font-medium">{t.invoiceAmount}</th>
                                <th className="py-2 pr-4 font-medium">{t.invoiceStatus}</th>
                                <th className="py-2 font-medium text-right">{t.invoiceDownload}</th>
                            </tr>
                        </thead>
                        <tbody>
                            {invoices.map((inv) => (
                                <tr key={inv.id} className="border-b border-border last:border-0">
                                    <td className="py-3 pr-4">
                                        {new Date(inv.issued_at).toLocaleDateString(locale, {
                                            day: '2-digit',
                                            month: 'short',
                                            year: 'numeric',
                                        })}
                                    </td>
                                    <td className="py-3 pr-4 font-medium">
                                        {inv.amount_mxn.toLocaleString(locale, {
                                            style: 'currency',
                                            currency: 'MXN',
                                        })}
                                    </td>
                                    <td className="py-3 pr-4">
                                        <StatusBadge status={inv.status} t={t} />
                                    </td>
                                    <td className="py-3 text-right">
                                        <div className="flex items-center justify-end gap-2">
                                            {inv.pdf_url && (
                                                <a
                                                    href={inv.pdf_url}
                                                    target="_blank"
                                                    rel="noopener noreferrer"
                                                    className="text-xs text-primary hover:underline"
                                                >
                                                    PDF
                                                </a>
                                            )}
                                            {inv.cfdi_xml_url && (
                                                <a
                                                    href={inv.cfdi_xml_url}
                                                    target="_blank"
                                                    rel="noopener noreferrer"
                                                    className="inline-flex items-center gap-1 text-xs text-primary hover:underline"
                                                >
                                                    {t.cfdiBadge}
                                                </a>
                                            )}
                                        </div>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            ) : (
                <p className="py-8 text-center text-sm text-muted-foreground">
                    {t.noInvoices}
                </p>
            )}
        </div>
    );
}

function StatusBadge({
    status,
    t,
}: {
    status: 'paid' | 'pending' | 'failed';
    t: typeof content.es;
}) {
    const map = {
        paid: { label: t.statusPaid, className: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-300' },
        pending: { label: t.statusPending, className: 'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300' },
        failed: { label: t.statusFailed, className: 'bg-destructive/10 text-destructive' },
    };
    const { label, className } = map[status];
    return (
        <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${className}`}>
            {label}
        </span>
    );
}

// ── Inactive billing (pre-monetization) ──────────────────────────────

function InactiveBilling({ t }: { t: typeof content.es }) {
    return (
        <div className="rounded-lg border border-border bg-background p-6">
            <h2 className="text-lg font-bold mb-2">{t.notActiveTitle}</h2>
            <p className="text-sm text-muted-foreground mb-6">{t.notActiveBody}</p>
            <InterestGate
                variant="inline"
                featureKey={t.notActiveFeatureKey}
                sourcePage="/cuenta/billing"
            />
        </div>
    );
}

// Suppress the unused-import lint warning for getCheckoutUrl during the
// scaffold phase — it'll be wired into the upgrade button once Dhanam's
// catalog has Tezca tier price IDs (Wave A operator action).
void getCheckoutUrl;
