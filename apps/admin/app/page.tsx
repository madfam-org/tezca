import Link from 'next/link';
import { Database, Settings } from 'lucide-react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@leyesmx/ui";

export default function Home() {
    return (
        <div className="px-4 py-6 sm:px-0">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">

                {/* Ingestion Card */}
                <Link href="/ingestion" className="block transition-transform hover:scale-105">
                    <Card className="h-full hover:shadow-md transition-shadow cursor-pointer border-blue-200 dark:border-blue-900">
                        <CardHeader className="flex flex-row items-center space-y-0 pb-2">
                            <div className="p-2 bg-blue-100 dark:bg-blue-900 rounded-full mr-4">
                                <Database className="w-6 h-6 text-blue-600 dark:text-blue-300" />
                            </div>
                            <div className="flex flex-col">
                                <CardTitle className="text-lg">Ingestion & Scraping</CardTitle>
                            </div>
                        </CardHeader>
                        <CardContent>
                            <CardDescription>
                                Manage data sources, trigger indexing, and monitor scraping jobs.
                            </CardDescription>
                        </CardContent>
                    </Card>
                </Link>

                {/* Placeholder for other admin tasks */}
                <Card className="h-full opacity-60">
                    <CardHeader className="flex flex-row items-center space-y-0 pb-2">
                        <div className="p-2 bg-muted rounded-full mr-4">
                            <Settings className="w-6 h-6 text-muted-foreground" />
                        </div>
                        <div className="flex flex-col">
                            <CardTitle className="text-lg">Settings</CardTitle>
                        </div>
                    </CardHeader>
                    <CardContent>
                        <CardDescription>
                            System configuration and user management (Coming soon).
                        </CardDescription>
                    </CardContent>
                </Card>

            </div>
        </div>
    );
}
