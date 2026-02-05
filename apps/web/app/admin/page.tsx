'use client';

import { SystemMetrics } from '@/components/admin/SystemMetrics';
import { JobQueue } from '@/components/admin/JobQueue';
import { Button } from '@leyesmx/ui';
import { Settings, RefreshCw } from 'lucide-react';
import Link from 'next/link';
import { useState } from 'react';

export default function AdminDashboard() {
    const [refreshKey, setRefreshKey] = useState(0);

    const handleRefresh = () => {
        setRefreshKey(prev => prev + 1);
    };

    return (
        <div className="min-h-screen bg-background">
            {/* Header */}
            <div className="border-b bg-card">
                <div className="container mx-auto px-4 sm:px-6 py-4 sm:py-6">
                    <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
                        <div>
                            <h1 className="text-2xl sm:text-3xl font-bold text-foreground flex items-center gap-2">
                                <Settings className="h-6 w-6 sm:h-7 sm:w-7 text-primary" />
                                Panel de Administración
                            </h1>
                            <p className="text-sm sm:text-base text-muted-foreground mt-1">
                                Monitor del sistema y estadísticas
                            </p>
                        </div>
                        <div className="flex gap-2 w-full sm:w-auto">
                            <Button 
                                variant="outline" 
                                size="sm" 
                                onClick={handleRefresh}
                                className="flex-1 sm:flex-none"
                            >
                                <RefreshCw className="h-4 w-4 mr-2" />
                                <span className="sm:inline">Actualizar</span>
                            </Button>
                            <Button 
                                asChild 
                                size="sm"
                                className="flex-1 sm:flex-none"
                            >
                                <Link href="/">
                                    Ir a Inicio
                                </Link>
                            </Button>
                        </div>
                    </div>
                </div>
            </div>

            {/* Main Content */}
            <div className="container mx-auto px-4 sm:px-6 py-6 sm:py-8">
                <div className="space-y-6 sm:space-y-8">
                    {/* System Metrics */}
                    <section>
                        <h2 className="text-lg sm:text-xl font-semibold mb-4 sm:mb-6">
                            Métricas del Sistema
                        </h2>
                        <SystemMetrics key={refreshKey} />
                    </section>

                    {/* Job Queue Section (Placeholder for future) */}
                    <section>
                        <h2 className="text-lg sm:text-xl font-semibold mb-4">
                            Trabajos Recientes
                        </h2>
                        <JobQueue />
                    </section>
                </div>
            </div>
        </div>
    );
}
