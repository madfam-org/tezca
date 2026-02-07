'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { api, type SystemConfig, type HealthCheck } from '@/lib/api';
import { Button, Card, CardHeader, CardTitle, CardContent, Badge } from "@tezca/ui";
import { ArrowLeft, Database, Globe, Server, HardDrive, RefreshCw } from 'lucide-react';

export default function SettingsPage() {
    const [config, setConfig] = useState<SystemConfig | null>(null);
    const [health, setHealth] = useState<HealthCheck | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const fetchData = async () => {
        setLoading(true);
        setError(null);
        try {
            const [configData, healthData] = await Promise.all([
                api.getConfig(),
                api.getHealth(),
            ]);
            setConfig(configData);
            setHealth(healthData);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Error al cargar configuración');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => { fetchData(); }, []);

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                    <Button asChild variant="ghost" size="sm">
                        <Link href="/">
                            <ArrowLeft className="w-4 h-4 mr-2" />
                            Volver
                        </Link>
                    </Button>
                    <h1 className="text-3xl font-bold tracking-tight">Configuración del Sistema</h1>
                </div>
                <Button variant="outline" size="sm" onClick={fetchData} disabled={loading}>
                    <RefreshCw className={`w-4 h-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
                    Actualizar
                </Button>
            </div>

            {error && (
                <div className="p-4 bg-error-50 text-error-700 rounded-lg border border-error-500/20">
                    {error}
                </div>
            )}

            {loading && !config ? (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    {[1, 2, 3, 4].map(i => (
                        <Card key={i} className="animate-pulse">
                            <CardHeader><div className="h-5 bg-muted rounded w-1/3" /></CardHeader>
                            <CardContent><div className="h-20 bg-muted rounded" /></CardContent>
                        </Card>
                    ))}
                </div>
            ) : config && (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    {/* Health Status */}
                    <Card>
                        <CardHeader className="flex flex-row items-center gap-3 pb-3">
                            <Server className="w-5 h-5 text-primary-500" />
                            <CardTitle className="text-lg">Estado del Servicio</CardTitle>
                            <Badge variant={health?.status === 'healthy' ? 'default' : 'destructive'} className="ml-auto">
                                {health?.status === 'healthy' ? 'Saludable' : 'Error'}
                            </Badge>
                        </CardHeader>
                        <CardContent>
                            <dl className="space-y-3 text-sm">
                                <div className="flex justify-between">
                                    <dt className="text-muted-foreground">Base de datos</dt>
                                    <dd className="font-medium">{health?.database}</dd>
                                </div>
                                <div className="flex justify-between">
                                    <dt className="text-muted-foreground">Modo debug</dt>
                                    <dd>
                                        <Badge variant={config.environment.debug ? 'destructive' : 'secondary'}>
                                            {config.environment.debug ? 'Activo' : 'Inactivo'}
                                        </Badge>
                                    </dd>
                                </div>
                                <div className="flex justify-between">
                                    <dt className="text-muted-foreground">Hosts permitidos</dt>
                                    <dd className="font-mono text-xs">{config.environment.allowed_hosts.join(', ')}</dd>
                                </div>
                            </dl>
                        </CardContent>
                    </Card>

                    {/* Database */}
                    <Card>
                        <CardHeader className="flex flex-row items-center gap-3 pb-3">
                            <Database className="w-5 h-5 text-primary-500" />
                            <CardTitle className="text-lg">Base de Datos</CardTitle>
                            <Badge variant={config.database.status === 'connected' ? 'default' : 'destructive'} className="ml-auto">
                                {config.database.status === 'connected' ? 'Conectada' : 'Error'}
                            </Badge>
                        </CardHeader>
                        <CardContent>
                            <dl className="space-y-3 text-sm">
                                <div className="flex justify-between">
                                    <dt className="text-muted-foreground">Motor</dt>
                                    <dd className="font-medium capitalize">{config.database.engine}</dd>
                                </div>
                                <div className="flex justify-between">
                                    <dt className="text-muted-foreground">Nombre</dt>
                                    <dd className="font-mono text-xs truncate max-w-48">{String(config.database.name)}</dd>
                                </div>
                            </dl>
                        </CardContent>
                    </Card>

                    {/* Elasticsearch */}
                    <Card>
                        <CardHeader className="flex flex-row items-center gap-3 pb-3">
                            <Globe className="w-5 h-5 text-primary-500" />
                            <CardTitle className="text-lg">Elasticsearch</CardTitle>
                            <Badge variant={config.elasticsearch.status === 'connected' ? 'default' : 'secondary'} className="ml-auto">
                                {config.elasticsearch.status === 'connected' ? 'Conectado' : config.elasticsearch.status}
                            </Badge>
                        </CardHeader>
                        <CardContent>
                            <dl className="space-y-3 text-sm">
                                <div className="flex justify-between">
                                    <dt className="text-muted-foreground">Host</dt>
                                    <dd className="font-mono text-xs">{config.elasticsearch.host}</dd>
                                </div>
                            </dl>
                        </CardContent>
                    </Card>

                    {/* Data Summary */}
                    <Card>
                        <CardHeader className="flex flex-row items-center gap-3 pb-3">
                            <HardDrive className="w-5 h-5 text-primary-500" />
                            <CardTitle className="text-lg">Datos</CardTitle>
                        </CardHeader>
                        <CardContent>
                            <dl className="space-y-3 text-sm">
                                <div className="flex justify-between">
                                    <dt className="text-muted-foreground">Total de leyes</dt>
                                    <dd className="font-bold text-lg">{config.data.total_laws.toLocaleString()}</dd>
                                </div>
                                <div className="flex justify-between">
                                    <dt className="text-muted-foreground">Total de versiones</dt>
                                    <dd className="font-medium">{config.data.total_versions.toLocaleString()}</dd>
                                </div>
                                <div className="flex justify-between">
                                    <dt className="text-muted-foreground">Publicación más reciente</dt>
                                    <dd className="font-medium">{config.data.latest_publication || 'N/A'}</dd>
                                </div>
                            </dl>
                        </CardContent>
                    </Card>

                    {/* Environment */}
                    <Card className="md:col-span-2">
                        <CardHeader className="flex flex-row items-center gap-3 pb-3">
                            <Globe className="w-5 h-5 text-primary-500" />
                            <CardTitle className="text-lg">Entorno</CardTitle>
                        </CardHeader>
                        <CardContent>
                            <dl className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                                <div>
                                    <dt className="text-muted-foreground">Idioma</dt>
                                    <dd className="font-medium">{config.environment.language}</dd>
                                </div>
                                <div>
                                    <dt className="text-muted-foreground">Zona horaria</dt>
                                    <dd className="font-medium">{config.environment.timezone}</dd>
                                </div>
                            </dl>
                        </CardContent>
                    </Card>
                </div>
            )}
        </div>
    );
}
