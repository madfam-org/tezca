import { LawDetail } from '@/components/laws/LawDetail';
import { Metadata } from 'next';

/**
 * Generate dynamic metadata for law pages with Open Graph support.
 * Enables rich previews when sharing law/article links on social media.
 */
export async function generateMetadata({
    params,
}: {
    params: { id: string }
    searchParams: { [key: string]: string | string[] | undefined }
}): Promise<Metadata> {
    const lawId = decodeURIComponent(params.id);
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

    try {
        // Fetch law metadata
        const lawRes = await fetch(`${apiUrl}/laws/${lawId}/`, {
            next: { revalidate: 3600 } // Cache for 1 hour
        });
        
        if (!lawRes.ok) {
            return {
                title: 'Ley no encontrada',
                description: 'La ley solicitada no está disponible.'
            };
        }
        
        const lawData = await lawRes.json();
        const law = lawData.law || lawData;
        
        // Base metadata for law page
        const baseMetadata: Metadata = {
            title: law.name || law.official_id,
            description: `${law.tier || 'Ley'} - ${law.category || 'Legislación mexicana'}`,
            openGraph: {
                title: law.name || law.official_id,
                description: `${law.tier || 'Ley'} - ${law.category || 'Legislación mexicana'}`,
                type: 'article',
                url: `https://leyesmx.com/laws/${lawId}`,
                siteName: 'Leyes MX',
            },
            twitter: {
                card: 'summary_large_image',
                title: law.name || law.official_id,
                description: `${law.tier || 'Ley'} - ${law.category || 'Legislación mexicana'}`,
            }
        };
        
        // Check if there's an article hash in the URL (from searchParams or future enhancement)
        // For now, we return base metadata - article-specific metadata can be enhanced later
        // when we have article data available at metadata generation time
        
        return baseMetadata;
        
    } catch (error) {
        console.error('Failed to generate metadata:', error);
        return {
            title: 'Leyes MX',
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

    return <LawDetail lawId={decodedId} />;
}
