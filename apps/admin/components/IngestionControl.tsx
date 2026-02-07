'use client';

import { useState } from 'react';
import { api } from '@/lib/api';
import { Button, Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from "@tezca/ui";
import { Play } from 'lucide-react';

export default function IngestionControl() {
    const [loading, setLoading] = useState(false);
    const [mode, setMode] = useState('all');

    const handleStart = async () => {
        try {
            setLoading(true);
            await api.startIngestion({ mode });
            alert("Trabajo de ingestión iniciado");
        } catch (error) {
            alert(error instanceof Error ? error.message : "Error al iniciar ingestión");
        } finally {
            setLoading(false);
        }
    };

    return (
        <Card className="h-full">
            <CardHeader>
                <CardTitle>Control de Procesos</CardTitle>
                <CardDescription>Iniciar pipelines de ingestión manualmente</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
                <div className="space-y-2">
                    <label className="text-sm font-medium">Modo de Ingestión</label>
                    <select
                        className="flex h-10 w-full items-center justify-between rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                        value={mode}
                        onChange={(e) => setMode(e.target.value)}
                    >
                        <option value="all">Todo (Sincronización Completa)</option>
                        <option value="priority">Prioridad Alta (Federal)</option>
                    </select>
                </div>
            </CardContent>
            <CardFooter>
                <Button onClick={handleStart} disabled={loading} className="w-full">
                    {loading ? (
                        "Iniciando..."
                    ) : (
                        <>
                            <Play className="w-4 h-4 mr-2" /> Iniciar Proceso
                        </>
                    )}
                </Button>
            </CardFooter>
        </Card>
    );
}
