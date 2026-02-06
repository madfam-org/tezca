import { Suspense } from 'react';
import type { Metadata } from 'next';
import ComparisonView from '@/components/ComparisonView';

export const dynamic = 'force-dynamic';

export const metadata: Metadata = {
    title: 'Comparación Estructural | Leyes Como Código México',
    description: 'Compara la estructura y artículos de dos leyes mexicanas lado a lado con resaltado de artículos en común.',
    openGraph: {
        title: 'Comparación Estructural de Leyes',
        description: 'Herramienta de comparación lado a lado de legislación mexicana.',
        type: 'website',
        siteName: 'Leyes MX',
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
            <Suspense fallback={<div>Cargando...</div>}>
                <ComparisonView lawIds={lawIds} />
            </Suspense>
        </main>
    );
}
