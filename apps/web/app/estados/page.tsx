import { Metadata } from 'next';
import { StatesGrid } from './StatesGrid';

export const metadata: Metadata = {
    title: 'Estados \u2014 Tezca',
    description:
        'Explora la legislaci\u00f3n mexicana por estado. Browse Mexican laws by state. Xictlaixmati tenahuatilli ic altepetl.',
};

/**
 * BreadcrumbList JSON-LD for SEO: Home > Estados
 */
function BreadcrumbJsonLd() {
    const siteUrl = process.env.NEXT_PUBLIC_SITE_URL || 'https://tezca.mx';
    const jsonLd = {
        '@context': 'https://schema.org',
        '@type': 'BreadcrumbList',
        itemListElement: [
            {
                '@type': 'ListItem',
                position: 1,
                name: 'Inicio',
                item: siteUrl,
            },
            {
                '@type': 'ListItem',
                position: 2,
                name: 'Estados',
                item: `${siteUrl}/estados`,
            },
        ],
    };

    return (
        <script
            type="application/ld+json"
            dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
        />
    );
}

export default function EstadosPage() {
    return (
        <>
            <BreadcrumbJsonLd />
            <StatesGrid />
        </>
    );
}
