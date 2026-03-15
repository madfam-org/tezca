import type { Metadata } from 'next';

export const metadata: Metadata = {
    title: 'Planes y Precios — Tezca',
    description:
        'Elige el plan ideal para acceder a la legislacion mexicana. Prueba gratis por 3 dias. Planes desde MXN$31/mes.',
    openGraph: {
        title: 'Planes y Precios — Tezca',
        description: 'Accede a 30,000+ leyes mexicanas con el plan ideal para ti.',
        type: 'website',
        siteName: 'Tezca',
    },
};

export default function PreciosLayout({ children }: { children: React.ReactNode }) {
    return children;
}
