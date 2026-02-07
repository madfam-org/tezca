import { LawDetail } from '@/components/laws/LawDetail';
import { Metadata } from 'next';
import { API_BASE_URL } from '@/lib/config';

/**
 * Build JSON-LD structured data for a law page.
 * Uses schema.org Legislation type for Google Scholar / legal search visibility.
 */
function buildJsonLd(law: Record<string, string>, siteUrl: string, lawId: string) {
    const tierLabel = law.tier === 'state' ? 'Estatal' : law.tier === 'municipal' ? 'Municipal' : 'Federal';
    const jurisdiction = law.state
        ? `${law.state}, México`
        : 'Estados Unidos Mexicanos';

    return {
        '@context': 'https://schema.org',
        '@type': 'Legislation',
        name: law.name || law.official_id,
        alternateName: law.short_name || undefined,
        legislationType: law.category || tierLabel,
        jurisdiction: {
            '@type': 'AdministrativeArea',
            name: jurisdiction,
        },
        inLanguage: 'es',
        url: `${siteUrl}/laws/${lawId}`,
        isPartOf: {
            '@type': 'WebSite',
            name: 'Tezca',
            url: siteUrl,
        },
        publisher: {
            '@type': 'Organization',
            name: 'Tezca — El Espejo de la Ley',
            url: siteUrl,
        },
        ...(law.source_url ? { legislationIdentifier: law.source_url } : {}),
        ...(law.status ? { legislationLegalValue: law.status } : {}),
    };
}

/**
 * Generate dynamic metadata for law pages with Open Graph + JSON-LD support.
 * Enables rich previews when sharing law/article links on social media
 * and structured data for Google Scholar / legal search engines.
 */
export async function generateMetadata({
    params,
}: {
    params: Promise<{ id: string }>
}): Promise<Metadata> {
    const { id } = await params;
    const lawId = decodeURIComponent(id);
    const apiUrl = API_BASE_URL;
    const siteUrl = process.env.NEXT_PUBLIC_SITE_URL || 'https://tezca.mx';

    try {
        const lawRes = await fetch(`${apiUrl}/laws/${lawId}/`, {
            next: { revalidate: 3600 }
        });

        if (!lawRes.ok) {
            return {
                title: 'Ley no encontrada — Tezca',
                description: 'La ley solicitada no está disponible.'
            };
        }

        const lawData = await lawRes.json();
        const law = lawData.law || lawData;

        const tierLabel = law.tier === 'state' ? 'Estatal' : law.tier === 'municipal' ? 'Municipal' : 'Federal';
        const description = `${law.name} — ${tierLabel}${law.category ? ` · ${law.category}` : ''}. Texto completo en formato digital.`;

        return {
            title: `${law.name || law.official_id} — Tezca`,
            description,
            openGraph: {
                title: law.name || law.official_id,
                description,
                type: 'article',
                url: `${siteUrl}/laws/${lawId}`,
                siteName: 'Tezca',
            },
            twitter: {
                card: 'summary_large_image',
                title: law.name || law.official_id,
                description,
            },
            other: {
                'script:ld+json': JSON.stringify(buildJsonLd(law, siteUrl, lawId)),
            },
        };

    } catch (error) {
        console.error('Failed to generate metadata:', error);
        return {
            title: 'Tezca — El Espejo de la Ley',
            description: 'Legislación mexicana digitalizada y accesible'
        };
    }
}

export default async function LawDetailPage({
    params
}: {
    params: Promise<{ id: string }>
}) {
    // Decode ID in case it comes encoded
    const { id } = await params;
    const decodedId = decodeURIComponent(id);

    return (
        <>
            <JsonLdScript lawId={decodedId} />
            <LawDetail lawId={decodedId} />
        </>
    );
}

/**
 * Server component that fetches law data and renders JSON-LD script tag.
 * This is the proper way to inject JSON-LD in Next.js App Router.
 */
async function JsonLdScript({ lawId }: { lawId: string }) {
    const apiUrl = API_BASE_URL;
    const siteUrl = process.env.NEXT_PUBLIC_SITE_URL || 'https://tezca.mx';

    try {
        const lawRes = await fetch(`${apiUrl}/laws/${lawId}/`, {
            next: { revalidate: 3600 }
        });

        if (!lawRes.ok) return null;

        const lawData = await lawRes.json();
        const law = lawData.law || lawData;
        const jsonLd = buildJsonLd(law, siteUrl, lawId);

        return (
            <script
                type="application/ld+json"
                dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
            />
        );
    } catch {
        return null;
    }
}
