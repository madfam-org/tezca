import type { Metadata } from 'next';

export const metadata: Metadata = {
    title: 'Buscar Leyes | Leyes Como Código México',
    description: 'Busca en más de 11,000 leyes federales, estatales y municipales mexicanas con filtros avanzados por jurisdicción, categoría y estado.',
    openGraph: {
        title: 'Buscador de Legislación Mexicana',
        description: 'Búsqueda avanzada en el marco jurídico mexicano digitalizado.',
        type: 'website',
        siteName: 'Leyes MX',
    },
};

export default function SearchLayout({ children }: { children: React.ReactNode }) {
    return children;
}
