import { Suspense } from 'react';
import type { Metadata } from 'next';
import ComparisonView from '@/components/ComparisonView';

export const dynamic = 'force-dynamic';

export const metadata: Metadata = {
    title: 'Comparación Estructural — Tezca',
    description: 'Compara la estructura y artículos de dos leyes mexicanas lado a lado con resaltado de artículos en común.',
    openGraph: {
        title: 'Comparación Estructural de Leyes',
        description: 'Herramienta de comparación lado a lado de legislación mexicana.',
        type: 'website',
        siteName: 'Tezca',
    },
};

export default async function ComparePage({
    searchParams,
}: {
    searchParams: Promise<{ [key: string]: string | string[] | undefined }>;
}) {
    const params = await searchParams;
    const lawsParam = params.laws;
    const lawIds = typeof lawsParam === 'string' ? lawsParam.split(',') : [];

    return (
        <main className="container mx-auto py-6 min-h-screen">
            <Suspense fallback={
                <div className="flex h-[80vh] items-center justify-center flex-col px-4">
                    <div className="h-8 w-8 sm:h-10 sm:w-10 animate-spin rounded-full border-4 border-primary border-t-transparent mb-4" />
                    <p className="text-lg sm:text-xl font-medium text-center text-muted-foreground" aria-live="polite">Cargando comparación...</p>

                </div>
            }>
                <ComparisonView lawIds={lawIds} />
            </Suspense>
        </main>
    );
}
