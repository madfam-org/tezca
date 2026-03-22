'use client';

import { useState, useEffect } from 'react';
import { Card } from '@tezca/ui';
import { Key, Plus, Copy, Trash2, Check, AlertTriangle } from 'lucide-react';
import { api, type ApiKeyData } from '@/lib/api';
import { useAuth } from '@/components/providers/AuthContext';
import { useLang } from '@/components/providers/LanguageContext';
import { getAuthToken } from '@/lib/auth-token';
import { InterestGate } from '@/components/InterestGate';
import { trackEvent } from '@/lib/analytics/posthog';

const content = {
    es: {
        title: 'Llaves de API',
        subtitle: 'Administra tus llaves de acceso a la API de Tezca.',
        empty: 'No tienes llaves de API. Crea una para comenzar.',
        loading: 'Cargando llaves...',
        create: 'Crear llave',
        nameLabel: 'Nombre de la llave',
        namePlaceholder: 'e.g. Mi aplicación',
        save: 'Crear',
        cancel: 'Cancelar',
        revoke: 'Revocar',
        revoked: 'Revocada',
        active: 'Activa',
        secretWarning: 'Guarda esta llave — no se mostrará de nuevo.',
        copied: 'Copiada',
        copy: 'Copiar',
        tier: 'Plan',
        scopes: 'Permisos',
        created: 'Creada',
        lastUsed: 'Último uso',
        never: 'Nunca',
        maxKeys: 'Has alcanzado el máximo de llaves activas.',
        errorCreate: 'No se pudo crear la llave.',
        errorLoad: 'No se pudieron cargar las llaves.',
        gateFeature: 'Llaves de API',
    },
    en: {
        title: 'API Keys',
        subtitle: 'Manage your Tezca API access keys.',
        empty: 'No API keys yet. Create one to get started.',
        loading: 'Loading keys...',
        create: 'Create key',
        nameLabel: 'Key name',
        namePlaceholder: 'e.g. My application',
        save: 'Create',
        cancel: 'Cancel',
        revoke: 'Revoke',
        revoked: 'Revoked',
        active: 'Active',
        secretWarning: 'Save this key — it will not be shown again.',
        copied: 'Copied',
        copy: 'Copy',
        tier: 'Tier',
        scopes: 'Scopes',
        created: 'Created',
        lastUsed: 'Last used',
        never: 'Never',
        maxKeys: 'You have reached the maximum number of active keys.',
        errorCreate: 'Could not create the key.',
        errorLoad: 'Could not load keys.',
        gateFeature: 'API Keys',
    },
    nah: {
        title: 'API tlaneltōquiliztli',
        subtitle: 'Xicnahuati motlaneltōquiliztli API Tezca.',
        empty: 'Ahmo oncah tlaneltōquiliztli. Xictlālia cē.',
        loading: 'Motēmoa tlaneltōquiliztli...',
        create: 'Xictlālia tlaneltōquiliztli',
        nameLabel: 'Tōcāitl',
        namePlaceholder: 'e.g. Notlatequipanōliz',
        save: 'Xictlālia',
        cancel: 'Xictlacahua',
        revoke: 'Xicpoloa',
        revoked: 'Ōpolōc',
        active: 'Mochihua',
        secretWarning: 'Xicpiya inīn — ahmo occeppa monēxtīz.',
        copied: 'Ōmocopi',
        copy: 'Xiccopīna',
        tier: 'Tlaxtlahuīlli',
        scopes: 'Tlanāhuatīlli',
        created: 'Ōmochīuh',
        lastUsed: 'Tlamatlāc',
        never: 'Ahmo',
        maxKeys: 'Ōticcauh in tlaneltōquiliztli.',
        errorCreate: 'Ahmo huelītic.',
        errorLoad: 'Ahmo huelītic in tlaneltōquiliztli.',
        gateFeature: 'API tlaneltōquiliztli',
    },
};

const TIER_COLORS: Record<string, string> = {
    free_member: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-300',
    community: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-300',
    essentials: 'bg-primary/10 text-primary',
    academic: 'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300',
    institutional: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300',
    madfam: 'bg-violet-100 text-violet-800 dark:bg-violet-900/30 dark:text-violet-300',
};

export default function ApiKeysPage() {
    const { lang } = useLang();
    const t = content[lang];
    const { isAuthenticated, tier } = useAuth();
    const [keys, setKeys] = useState<ApiKeyData[]>([]);
    const [loading, setLoading] = useState(true);
    const [adding, setAdding] = useState(false);
    const [newName, setNewName] = useState('');
    const [newSecret, setNewSecret] = useState<string | null>(null);
    const [copied, setCopied] = useState(false);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        async function load() {
            const token = getAuthToken();
            if (!token) {
                setLoading(false);
                return;
            }
            try {
                const res = await api.getUserApiKeys(token);
                setKeys(res.keys);
            } catch {
                // silent
            } finally {
                setLoading(false);
            }
        }
        if (isAuthenticated) load();
        else setLoading(false);
    }, [isAuthenticated]);

    // Feature gate for anon users
    if (tier === 'anon') {
        return (
            <div className="max-w-3xl mx-auto">
                <div className="flex items-center gap-3 mb-6">
                    <Key className="h-6 w-6 text-primary" />
                    <h1 className="text-2xl font-bold text-foreground">{t.title}</h1>
                </div>
                <InterestGate
                    variant="card"
                    featureKey="api_key_access"
                    featureLabel={t.gateFeature}
                    sourcePage="cuenta_apikeys"
                />
            </div>
        );
    }

    const handleCreate = async () => {
        const token = getAuthToken();
        if (!token || !newName.trim()) return;
        setError(null);
        try {
            const res = await api.createUserApiKey(token, { name: newName.trim() });
            setNewSecret(res.key);
            const { key: _key, ...keyData } = res;
            setKeys((prev) => [keyData, ...prev]);
            setNewName('');
            trackEvent('api_key.self_serve_created', { prefix: res.prefix });
        } catch (e: unknown) {
            const msg = e instanceof Error ? e.message : t.errorCreate;
            setError(msg);
        }
    };

    const handleRevoke = async (prefix: string) => {
        const token = getAuthToken();
        if (!token) return;
        try {
            await api.revokeUserApiKey(token, prefix);
            setKeys((prev) =>
                prev.map((k) => (k.prefix === prefix ? { ...k, is_active: false } : k))
            );
            trackEvent('api_key.self_serve_revoked', { prefix });
        } catch {
            // silent
        }
    };

    const handleCopy = async (text: string) => {
        await navigator.clipboard.writeText(text);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
    };

    return (
        <div className="max-w-3xl mx-auto">
            <div className="flex items-center justify-between mb-6">
                <div className="flex items-center gap-3">
                    <Key className="h-6 w-6 text-primary" />
                    <div>
                        <h1 className="text-2xl font-bold text-foreground">{t.title}</h1>
                        <p className="text-sm text-muted-foreground">{t.subtitle}</p>
                    </div>
                </div>
                {isAuthenticated && !adding && !newSecret && (
                    <button
                        onClick={() => { setAdding(true); setError(null); }}
                        className="flex items-center gap-1.5 px-3 py-1.5 text-sm bg-primary text-primary-foreground rounded-md hover:bg-primary/90 transition-colors"
                    >
                        <Plus className="h-4 w-4" /> {t.create}
                    </button>
                )}
            </div>

            {/* Secret display (one-time) */}
            {newSecret && (
                <Card className="p-4 mb-4 border-amber-500/30 bg-amber-50 dark:bg-amber-900/10">
                    <div className="flex items-start gap-2 mb-3">
                        <AlertTriangle className="h-5 w-5 text-amber-600 flex-shrink-0 mt-0.5" />
                        <p className="text-sm font-medium text-amber-800 dark:text-amber-300">{t.secretWarning}</p>
                    </div>
                    <div className="flex items-center gap-2">
                        <code className="flex-1 text-xs bg-background rounded-md p-2 font-mono break-all border">
                            {newSecret}
                        </code>
                        <button
                            onClick={() => handleCopy(newSecret)}
                            className="flex items-center gap-1 px-3 py-2 text-xs bg-primary text-primary-foreground rounded-md hover:bg-primary/90 flex-shrink-0"
                        >
                            {copied ? <Check className="h-3.5 w-3.5" /> : <Copy className="h-3.5 w-3.5" />}
                            {copied ? t.copied : t.copy}
                        </button>
                    </div>
                    <button
                        onClick={() => setNewSecret(null)}
                        className="mt-3 text-xs text-muted-foreground hover:text-foreground"
                    >
                        {t.cancel}
                    </button>
                </Card>
            )}

            {/* Create form */}
            {adding && !newSecret && (
                <Card className="p-4 mb-4 space-y-3">
                    <div>
                        <label className="text-xs font-medium text-muted-foreground">{t.nameLabel}</label>
                        <input
                            type="text"
                            value={newName}
                            onChange={(e) => setNewName(e.target.value)}
                            className="w-full mt-1 text-sm border rounded-md p-2 bg-transparent"
                            placeholder={t.namePlaceholder}
                            maxLength={200}
                        />
                    </div>
                    {error && (
                        <p className="text-xs text-destructive">{error}</p>
                    )}
                    <div className="flex gap-2">
                        <button
                            onClick={handleCreate}
                            disabled={!newName.trim()}
                            className="text-sm px-3 py-1.5 bg-primary text-primary-foreground rounded-md disabled:opacity-50"
                        >
                            {t.save}
                        </button>
                        <button
                            onClick={() => { setAdding(false); setError(null); }}
                            className="text-sm px-3 py-1.5 text-muted-foreground hover:text-foreground"
                        >
                            {t.cancel}
                        </button>
                    </div>
                </Card>
            )}

            {/* Key list */}
            {loading ? (
                <p className="text-sm text-muted-foreground text-center py-12">{t.loading}</p>
            ) : keys.length === 0 ? (
                <Card className="p-12 text-center text-muted-foreground">{t.empty}</Card>
            ) : (
                <div className="space-y-2">
                    {keys.map((k) => (
                        <Card key={k.prefix} className="p-4 flex items-center justify-between">
                            <div className="min-w-0">
                                <div className="flex items-center gap-2 flex-wrap">
                                    <code className="text-xs font-mono bg-muted px-1.5 py-0.5 rounded">
                                        tzk_{k.prefix}...
                                    </code>
                                    <span className="text-sm font-medium">{k.name}</span>
                                    <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                                        k.is_active
                                            ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-300'
                                            : 'bg-muted text-muted-foreground'
                                    }`}>
                                        {k.is_active ? t.active : t.revoked}
                                    </span>
                                </div>
                                <div className="flex items-center gap-3 mt-1 text-xs text-muted-foreground">
                                    <span>
                                        {t.tier}: <span className={`inline-flex items-center px-1.5 py-0.5 rounded-full text-xs font-medium ${TIER_COLORS[k.tier] || 'bg-muted text-muted-foreground'}`}>{k.tier}</span>
                                    </span>
                                    <span>{t.scopes}: {k.scopes.join(', ')}</span>
                                    <span>{t.created}: {new Date(k.created_at).toLocaleDateString()}</span>
                                    <span>{t.lastUsed}: {k.last_used_at ? new Date(k.last_used_at).toLocaleDateString() : t.never}</span>
                                </div>
                            </div>
                            {k.is_active && (
                                <button
                                    onClick={() => handleRevoke(k.prefix)}
                                    className="p-2 rounded-md hover:bg-destructive/10 text-destructive flex-shrink-0"
                                    aria-label={t.revoke}
                                >
                                    <Trash2 className="h-4 w-4" />
                                </button>
                            )}
                        </Card>
                    ))}
                </div>
            )}
        </div>
    );
}
