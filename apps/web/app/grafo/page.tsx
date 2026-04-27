import { Metadata } from 'next';
import dynamic from 'next/dynamic';
import { GraphTierMessage } from '@/components/graph/GraphTierMessage';
import { JsonLd } from '@/components/JsonLd';

export const metadata: Metadata = {
    title: 'Grafo de Leyes | Tezca',
    description: 'Red interactiva de referencias cruzadas entre leyes mexicanas.',
};

const siteUrl = process.env.NEXT_PUBLIC_SITE_URL || 'https://tezca.mx';

// LawGraphContainer pulls in Sigma + graphology + force-atlas-2 worker.
// Client-only (DOM-bound canvas) and never needed for SSR — defer the
// JS chunk until the browser actually reaches /grafo.
const LawGraphContainer = dynamic(
    () => import('@/components/graph/LawGraphContainer').then(m => ({ default: m.LawGraphContainer })),
    { ssr: false },
);

export default function GrafoPage() {
    return (
        <>
            <JsonLd data={{
                '@context': 'https://schema.org',
                '@type': 'BreadcrumbList',
                itemListElement: [
                    { '@type': 'ListItem', position: 1, name: 'Inicio', item: `${siteUrl}/` },
                    { '@type': 'ListItem', position: 2, name: 'Grafo', item: `${siteUrl}/grafo` },
                ],
            }} />
            <GraphTierMessage />
            <LawGraphContainer mode="fullscreen" />
        </>
    );
}
