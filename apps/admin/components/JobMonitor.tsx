'use client';

import { useEffect, useState, useRef } from 'react';
import { api } from '@/lib/api';
import { Card, CardHeader, CardTitle, CardContent, Badge } from "@leyesmx/ui";
import { Loader2 } from 'lucide-react';

export default function JobMonitor() {
    const [status, setStatus] = useState<any>(null);
    const [loading, setLoading] = useState(true);
    const pollRef = useRef<NodeJS.Timeout | null>(null);

    const fetchStatus = async () => {
        try {
            const data = await api.getIngestionStatus();
            setStatus(data);
        } catch (error) {
            console.error(error);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchStatus();
        pollRef.current = setInterval(fetchStatus, 2000); // Poll every 2s

        return () => {
            if (pollRef.current) clearInterval(pollRef.current);
        };
    }, []);

    if (loading && !status) return <div>Cargando monitor...</div>;

    const isRunning = status?.status === 'running';

    return (
        <Card className="h-full">
            <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-lg font-medium">Estado de Ingestión</CardTitle>
                <Badge variant={isRunning ? "default" : status?.status === 'completed' ? "secondary" : "error"}>
                    {isRunning ? (
                        <span className="flex items-center gap-1">
                            <Loader2 className="w-3 h-3 animate-spin" /> Ejecutando
                        </span>
                    ) : status?.status === 'completed' ? 'Inactivo' : 'Error'}
                </Badge>
            </CardHeader>
            <CardContent>
                <div className="space-y-4">
                    <div className="flex items-center justify-between text-sm">
                        <span className="text-muted-foreground">Último Mensaje:</span>
                        <span className="font-mono text-xs text-muted-foreground">{status?.timestamp}</span>
                    </div>

                    <div className="p-3 bg-muted rounded-md font-mono text-xs overflow-x-auto whitespace-pre-wrap max-h-[200px] min-h-[100px]">
                        {status?.message || "No hay actividad reciente"}
                    </div>

                    {isRunning && (
                        <div className="space-y-1">
                            <div className="flex justify-between text-xs text-muted-foreground">
                                <span>Progreso estimado</span>
                                <span>{status?.progress || 0}%</span>
                            </div>
                            <div className="h-2 w-full bg-secondary rounded-full overflow-hidden">
                                <div
                                    className="h-full bg-primary transition-all duration-500 ease-in-out"
                                    style={{ width: `${status?.progress || 0}%` }}
                                />
                            </div>
                        </div>
                    )}
                </div>
            </CardContent>
        </Card>
    );
}
