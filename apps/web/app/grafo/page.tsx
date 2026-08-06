import { Metadata } from 'next';
import { GraphTierMessage } from '@/components/graph/GraphTierMessage';
import { LawGraphClient } from '@/components/graph/LawGraphClient';
import { JsonLd } from '@/components/JsonLd';

export const metadata: Metadata = {
    title: 'Grafo de Leyes | Tezca',
    description: 'Red interactiva de referencias cruzadas entre leyes mexicanas.',
};

const siteUrl = process.env.NEXT_PUBLIC_SITE_URL || 'https://tezca.mx';

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
            <LawGraphClient mode="fullscreen" />
        </>
    );
}
