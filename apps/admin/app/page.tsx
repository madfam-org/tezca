import Link from 'next/link';
import { Database, Settings } from 'lucide-react';

export default function Home() {
    return (
        <div className="px-4 py-6 sm:px-0">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">

                {/* Ingestion Card */}
                <Link href="/ingestion" className="block p-6 bg-white dark:bg-gray-800 rounded-lg shadow hover:shadow-md transition-shadow">
                    <div className="flex items-center space-x-4">
                        <div className="p-3 bg-blue-100 dark:bg-blue-900 rounded-full">
                            <Database className="w-6 h-6 text-blue-600 dark:text-blue-300" />
                        </div>
                        <div>
                            <h3 className="text-lg font-medium text-gray-900 dark:text-white">Ingestion & Scraping</h3>
                            <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">Manage data sources, trigger indexing.</p>
                        </div>
                    </div>
                </Link>

                {/* Placeholder for other admin tasks */}
                <div className="block p-6 bg-white dark:bg-gray-800 rounded-lg shadow opacity-50">
                    <div className="flex items-center space-x-4">
                        <div className="p-3 bg-gray-100 rounded-full">
                            <Settings className="w-6 h-6 text-gray-600" />
                        </div>
                        <div>
                            <h3 className="text-lg font-medium text-gray-900 dark:text-white">Settings</h3>
                            <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">System configuration (Coming soon).</p>
                        </div>
                    </div>
                </div>

            </div>
        </div>
    );
}
