'use client';

import { useState, useEffect, useCallback } from 'react';
import { Card } from '@tezca/ui';
import { Bell, Trash2, Plus } from 'lucide-react';
import { api, type AlertData } from '@/lib/api';
import { useAuth } from '@/components/providers/AuthContext';
import { useLang } from '@/components/providers/LanguageContext';

const content = {
    es: {
        title: 'Mis alertas',
        subtitle: 'Recibe notificaciones cuando cambien las leyes que sigues.',
        empty: 'No tienes alertas activas. Sigue una ley para recibir notificaciones.',
        delete: 'Eliminar',
        loading: 'Cargando alertas...',
        alertTypes: { law_updated: 'Ley actualizada', new_version: 'Nueva versión', new_law: 'Nueva ley' } as Record<string, string>,
        delivery: { in_app: 'En la app', email: 'Correo' } as Record<string, string>,
        law: 'Ley',
        category: 'Categoría',
        state: 'Estado',
        type: 'Tipo',
        addAlert: 'Agregar alerta',
        newAlertType: 'Tipo de alerta',
        lawId: 'ID de ley (opcional)',
        save: 'Guardar',
        cancel: 'Cancelar',
    },
    en: {
        title: 'My alerts',
        subtitle: 'Get notified when the laws you follow change.',
        empty: 'No active alerts. Watch a law to get notifications.',
        delete: 'Delete',
        loading: 'Loading alerts...',
        alertTypes: { law_updated: 'Law updated', new_version: 'New version', new_law: 'New law' } as Record<string, string>,
        delivery: { in_app: 'In-app', email: 'Email' } as Record<string, string>,
        law: 'Law',
        category: 'Category',
        state: 'State',
        type: 'Type',
        addAlert: 'Add alert',
        newAlertType: 'Alert type',
        lawId: 'Law ID (optional)',
        save: 'Save',
        cancel: 'Cancel',
    },
    nah: {
        title: 'Notēnahuatīlhuān',
        subtitle: 'Xicceliz tēnahuatīlmeh ihcuāc mopatlaz tenahuatīlmeh.',
        empty: 'Ahmo oncah tēnahuatīlmeh. Xictlachili cē tenahuatilli.',
        delete: 'Xicpoloa',
        loading: 'Motēmoa tēnahuatīlmeh...',
        alertTypes: { law_updated: 'Ōmopatlac', new_version: 'Yancuīc', new_law: 'Yancuīc tenahuatilli' } as Record<string, string>,
        delivery: { in_app: 'Nican', email: 'Correo' } as Record<string, string>,
        law: 'Tenahuatilli',
        category: 'Tlamantli',
        state: 'Altepetl',
        type: 'Tlamantli',
        addAlert: 'Xictlālia tēnahuatīlli',
        newAlertType: 'Tlamantli',
        lawId: 'Tenahuatilli ID',
        save: 'Xicpiya',
        cancel: 'Xictlacahua',
    },
};

export default function AlertasPage() {
    const { lang } = useLang();
    const t = content[lang];
    const { isAuthenticated } = useAuth();
    const [alerts, setAlerts] = useState<AlertData[]>([]);
    const [loading, setLoading] = useState(true);
    const [adding, setAdding] = useState(false);
    const [newAlertType, setNewAlertType] = useState('law_updated');
    const [newLawId, setNewLawId] = useState('');

    const getToken = useCallback((): string | null => {
        if (typeof document !== 'undefined') {
            const match = document.cookie.match(/(?:^|;\s*)janua_token=([^;]*)/);
            if (match) return decodeURIComponent(match[1]);
        }
        if (typeof localStorage !== 'undefined') {
            return localStorage.getItem('janua_token');
        }
        return null;
    }, []);

    useEffect(() => {
        async function fetch() {
            const token = getToken();
            if (!token) {
                setLoading(false);
                return;
            }
            try {
                const res = await api.getAlerts(token);
                setAlerts(res.alerts);
            } catch {
                // silent
            } finally {
                setLoading(false);
            }
        }
        if (isAuthenticated) fetch();
        else setLoading(false);
    }, [isAuthenticated, getToken]);

    const handleDelete = async (id: number) => {
        const token = getToken();
        if (!token) return;
        try {
            await api.deleteAlert(token, id);
            setAlerts((prev) => prev.filter((a) => a.id !== id));
        } catch {
            // silent
        }
    };

    const handleCreate = async () => {
        const token = getToken();
        if (!token) return;
        try {
            const alert = await api.createAlert(token, {
                alert_type: newAlertType,
                ...(newLawId && { law_id: newLawId }),
            });
            setAlerts((prev) => [...prev, alert]);
            setAdding(false);
            setNewLawId('');
        } catch {
            // silent
        }
    };

    return (
        <div className="max-w-3xl mx-auto">
            <div className="flex items-center justify-between mb-6">
                <div className="flex items-center gap-3">
                    <Bell className="h-6 w-6 text-primary" />
                    <div>
                        <h1 className="text-2xl font-bold text-foreground">{t.title}</h1>
                        <p className="text-sm text-muted-foreground">{t.subtitle}</p>
                    </div>
                </div>
                {isAuthenticated && !adding && (
                    <button
                        onClick={() => setAdding(true)}
                        className="flex items-center gap-1.5 px-3 py-1.5 text-sm bg-primary text-primary-foreground rounded-md hover:bg-primary/90 transition-colors"
                    >
                        <Plus className="h-4 w-4" /> {t.addAlert}
                    </button>
                )}
            </div>

            {adding && (
                <Card className="p-4 mb-4 space-y-3">
                    <div>
                        <label className="text-xs font-medium text-muted-foreground">{t.newAlertType}</label>
                        <select
                            value={newAlertType}
                            onChange={(e) => setNewAlertType(e.target.value)}
                            className="w-full mt-1 text-sm border rounded-md p-2 bg-transparent"
                        >
                            <option value="law_updated">{t.alertTypes.law_updated}</option>
                            <option value="new_version">{t.alertTypes.new_version}</option>
                            <option value="new_law">{t.alertTypes.new_law}</option>
                        </select>
                    </div>
                    <div>
                        <label className="text-xs font-medium text-muted-foreground">{t.lawId}</label>
                        <input
                            type="text"
                            value={newLawId}
                            onChange={(e) => setNewLawId(e.target.value)}
                            className="w-full mt-1 text-sm border rounded-md p-2 bg-transparent"
                            placeholder="e.g. cpeum"
                        />
                    </div>
                    <div className="flex gap-2">
                        <button
                            onClick={handleCreate}
                            className="text-sm px-3 py-1.5 bg-primary text-primary-foreground rounded-md"
                        >
                            {t.save}
                        </button>
                        <button
                            onClick={() => setAdding(false)}
                            className="text-sm px-3 py-1.5 text-muted-foreground hover:text-foreground"
                        >
                            {t.cancel}
                        </button>
                    </div>
                </Card>
            )}

            {loading ? (
                <p className="text-sm text-muted-foreground text-center py-12">{t.loading}</p>
            ) : alerts.length === 0 ? (
                <Card className="p-12 text-center text-muted-foreground">{t.empty}</Card>
            ) : (
                <div className="space-y-2">
                    {alerts.map((alert) => (
                        <Card key={alert.id} className="p-4 flex items-center justify-between">
                            <div className="min-w-0">
                                <div className="flex items-center gap-2 flex-wrap">
                                    <span className="text-xs px-2 py-0.5 rounded-full bg-primary/10 text-primary font-medium">
                                        {t.alertTypes[alert.alert_type] || alert.alert_type}
                                    </span>
                                    {alert.law_id && (
                                        <span className="text-xs text-muted-foreground">
                                            {t.law}: {alert.law_id}
                                        </span>
                                    )}
                                    {alert.category && (
                                        <span className="text-xs text-muted-foreground">
                                            {t.category}: {alert.category}
                                        </span>
                                    )}
                                    {alert.state && (
                                        <span className="text-xs text-muted-foreground">
                                            {t.state}: {alert.state}
                                        </span>
                                    )}
                                </div>
                                <p className="text-xs text-muted-foreground mt-1">
                                    {new Date(alert.created_at).toLocaleDateString()}
                                    {' · '}
                                    {t.delivery[alert.delivery] || alert.delivery}
                                </p>
                            </div>
                            <button
                                onClick={() => handleDelete(alert.id)}
                                className="p-2 rounded-md hover:bg-destructive/10 text-destructive flex-shrink-0"
                                aria-label={t.delete}
                            >
                                <Trash2 className="h-4 w-4" />
                            </button>
                        </Card>
                    ))}
                </div>
            )}
        </div>
    );
}
