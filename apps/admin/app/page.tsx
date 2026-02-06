import Link from 'next/link';
import { Database, Settings, BarChart3, Activity } from 'lucide-react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@leyesmx/ui";

export default function Home() {
    return (
        <div className="px-4 py-6 sm:px-0">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">

                {/* Ingestion Card */}
                <Link href="/ingestion" className="block transition-transform hover:scale-105">
                    <Card className="h-full hover:shadow-md transition-shadow cursor-pointer border-primary-200 dark:border-primary-900">
                        <CardHeader className="flex flex-row items-center space-y-0 pb-2">
                            <div className="p-2 bg-primary-100 dark:bg-primary-900 rounded-full mr-4">
                                <Database className="w-6 h-6 text-primary-600 dark:text-primary-300" />
                            </div>
                            <div className="flex flex-col">
                                <CardTitle className="text-lg">Ingestión y Scraping</CardTitle>
                            </div>
                        </CardHeader>
                        <CardContent>
                            <CardDescription>
                                Gestionar fuentes de datos, disparar indexación y monitorear trabajos de scraping.
                            </CardDescription>
                        </CardContent>
                    </Card>
                </Link>

                {/* Metrics Card */}
                <Link href="/metrics" className="block transition-transform hover:scale-105">
                    <Card className="h-full hover:shadow-md transition-shadow cursor-pointer border-secondary-200 dark:border-secondary-900">
                        <CardHeader className="flex flex-row items-center space-y-0 pb-2">
                            <div className="p-2 bg-secondary-100 dark:bg-secondary-900 rounded-full mr-4">
                                <BarChart3 className="w-6 h-6 text-secondary-600 dark:text-secondary-300" />
                            </div>
                            <div className="flex flex-col">
                                <CardTitle className="text-lg">Métricas</CardTitle>
                            </div>
                        </CardHeader>
                        <CardContent>
                            <CardDescription>
                                Estadísticas del sistema, distribución por jurisdicción y categorías.
                            </CardDescription>
                        </CardContent>
                    </Card>
                </Link>

                {/* DataOps Card */}
                <Link href="/dataops" className="block transition-transform hover:scale-105">
                    <Card className="h-full hover:shadow-md transition-shadow cursor-pointer border-green-200 dark:border-green-900">
                        <CardHeader className="flex flex-row items-center space-y-0 pb-2">
                            <div className="p-2 bg-green-100 dark:bg-green-900 rounded-full mr-4">
                                <Activity className="w-6 h-6 text-green-600 dark:text-green-300" />
                            </div>
                            <div className="flex flex-col">
                                <CardTitle className="text-lg">DataOps</CardTitle>
                            </div>
                        </CardHeader>
                        <CardContent>
                            <CardDescription>
                                Cobertura de datos, salud de fuentes, y brechas de adquisición.
                            </CardDescription>
                        </CardContent>
                    </Card>
                </Link>

                {/* Settings Card */}
                <Link href="/settings" className="block transition-transform hover:scale-105">
                    <Card className="h-full hover:shadow-md transition-shadow cursor-pointer border-accent-200 dark:border-accent-900">
                        <CardHeader className="flex flex-row items-center space-y-0 pb-2">
                            <div className="p-2 bg-accent-100 dark:bg-accent-900 rounded-full mr-4">
                                <Settings className="w-6 h-6 text-accent-600 dark:text-accent-300" />
                            </div>
                            <div className="flex flex-col">
                                <CardTitle className="text-lg">Configuración</CardTitle>
                            </div>
                        </CardHeader>
                        <CardContent>
                            <CardDescription>
                                Estado de servicios, base de datos, Elasticsearch y configuración del entorno.
                            </CardDescription>
                        </CardContent>
                    </Card>
                </Link>

            </div>
        </div>
    );
}
