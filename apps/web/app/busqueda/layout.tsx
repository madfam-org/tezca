import type { Metadata } from 'next';
import { JsonLd } from '@/components/JsonLd';

export const metadata: Metadata = {
    title: 'Buscar Leyes — Tezca',
    description: 'Busca entre 11,900+ leyes mexicanas federales, estatales y municipales. Resultados con texto resaltado y filtros por jurisdiccion, categoria y estado.',
    openGraph: {
        title: 'Buscador de Legislacion Mexicana — Tezca',
        description: 'Busqueda avanzada en el marco juridico mexicano digitalizado.',
        type: 'website',
        siteName: 'Tezca',
    },
};

const siteUrl = process.env.NEXT_PUBLIC_SITE_URL || 'https://tezca.mx';

export default function SearchLayout({ children }: { children: React.ReactNode }) {
    return (
        <>
            <JsonLd data={{
                '@context': 'https://schema.org',
                '@type': 'BreadcrumbList',
                itemListElement: [
                    { '@type': 'ListItem', position: 1, name: 'Inicio', item: `${siteUrl}/` },
                    { '@type': 'ListItem', position: 2, name: 'Busqueda', item: `${siteUrl}/busqueda` },
                ],
            }} />
            {children}
        </>
    );
}
