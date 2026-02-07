import type { Metadata } from 'next';

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

export default function SearchLayout({ children }: { children: React.ReactNode }) {
    return children;
}
