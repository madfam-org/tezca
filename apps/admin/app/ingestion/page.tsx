import JobMonitor from '@/components/JobMonitor';
import IngestionControl from '@/components/IngestionControl';
import Link from 'next/link';
import { Button } from "@tezca/ui";
import { ArrowLeft } from 'lucide-react';

export default function IngestionPage() {
    return (
        <div className="space-y-6">
            <div className="flex items-center gap-4">
                <Button asChild variant="ghost" size="sm">
                    <Link href="/">
                        <ArrowLeft className="w-4 h-4 mr-2" />
                        Volver
                    </Link>
                </Button>
                <h1 className="text-3xl font-bold tracking-tight">Panel de Ingestión</h1>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div className="md:col-span-1">
                    <IngestionControl />
                </div>
                <div className="md:col-span-2">
                    <JobMonitor />
                </div>
            </div>
        </div>
    );
}
