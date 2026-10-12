import type { Metadata } from 'next';
import { getStateSeo } from '@/lib/states';

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL || 'https://tezca.mx';

/**
 * The state page itself is a client component, so its per-state `<title>` and
 * meta description come from this server layout. Without it every
 * `/estados/<slug>` page inherited the root title «Tezca — El Espejo de la Ley».
 */
export async function generateMetadata({
    params,
}: {
    params: Promise<{ state: string }>;
}): Promise<Metadata> {
    const { state } = await params;
    const slug = decodeURIComponent(state);
    const { title, description } = getStateSeo(slug);
    const url = `${SITE_URL}/estados/${encodeURIComponent(slug)}`;

    return {
        title,
        description,
        alternates: {
            canonical: url,
            languages: {
                es: url,
                en: `${url}?lang=en`,
                'x-default': url,
            },
        },
        openGraph: {
            title,
            description,
            type: 'website',
            url,
            siteName: 'Tezca',
        },
    };
}

export default function StateLayout({ children }: { children: React.ReactNode }) {
    return children;
}
