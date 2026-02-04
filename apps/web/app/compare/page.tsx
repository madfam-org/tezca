import { Suspense } from 'react';
import ComparisonView from '@/components/ComparisonView';

export const dynamic = 'force-dynamic';

export default function ComparePage({
    searchParams,
}: {
    searchParams: { [key: string]: string | string[] | undefined };
}) {
    const lawsParam = searchParams.laws;
    const lawIds = typeof lawsParam === 'string' ? lawsParam.split(',') : [];

    return (
        <main className="container mx-auto py-6 min-h-screen">
            <Suspense fallback={<div>Cargando...</div>}>
                <ComparisonView lawIds={lawIds} />
            </Suspense>
        </main>
    );
}
