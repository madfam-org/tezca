import type { MetadataRoute } from 'next';
import { INTERNAL_API_URL } from '@/lib/config';
import { STATE_SLUGS } from '@/lib/states';

const BASE_URL = process.env.NEXT_PUBLIC_SITE_URL || 'https://tezca.mx';

// Known categories (matches API /categories/ response keys)
const CATEGORIES = [
  'Códigos',
  'Constituciones',
  'Leyes Generales',
  'Leyes Orgánicas',
  'Leyes Reglamentarias',
  'Reglamentos',
  'Otras',
];

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  // Static routes
  const staticRoutes: MetadataRoute.Sitemap = [
    {
      url: BASE_URL,
      lastModified: new Date(),
      changeFrequency: 'daily',
      priority: 1,
    },
    {
      url: `${BASE_URL}/leyes`,
      lastModified: new Date(),
      changeFrequency: 'weekly',
      priority: 0.9,
    },
    {
      url: `${BASE_URL}/busqueda`,
      lastModified: new Date(),
      changeFrequency: 'weekly',
      priority: 0.8,
    },
    {
      url: `${BASE_URL}/comparar`,
      lastModified: new Date(),
      changeFrequency: 'monthly',
      priority: 0.6,
    },
    {
      url: `${BASE_URL}/precios`,
      lastModified: new Date(),
      changeFrequency: 'monthly',
      priority: 0.8,
    },
    {
      url: `${BASE_URL}/desarrolladores`,
      lastModified: new Date(),
      changeFrequency: 'monthly',
      priority: 0.6,
    },
  ];

  // Static content pages
  const contentRoutes: MetadataRoute.Sitemap = [
    '/favoritos',
    '/acerca-de',
    '/terminos',
    '/privacidad',
    '/aviso-legal',
  ].map((path) => ({
    url: `${BASE_URL}${path}`,
    lastModified: new Date(),
    changeFrequency: 'monthly' as const,
    priority: 0.4,
  }));

  // Browse routes: /categorias and /estados index pages + individual pages
  const browseRoutes: MetadataRoute.Sitemap = [
    {
      url: `${BASE_URL}/categorias`,
      lastModified: new Date(),
      changeFrequency: 'weekly' as const,
      priority: 0.8,
    },
    ...CATEGORIES.map((cat) => ({
      url: `${BASE_URL}/categorias/${encodeURIComponent(cat)}`,
      lastModified: new Date(),
      changeFrequency: 'weekly' as const,
      priority: 0.7,
    })),
    {
      url: `${BASE_URL}/estados`,
      lastModified: new Date(),
      changeFrequency: 'weekly' as const,
      priority: 0.8,
    },
    ...STATE_SLUGS.map((state) => ({
      url: `${BASE_URL}/estados/${encodeURIComponent(state)}`,
      lastModified: new Date(),
      changeFrequency: 'weekly' as const,
      priority: 0.7,
    })),
  ];

  // Dynamic law routes — paginate through API
  const lawRoutes: MetadataRoute.Sitemap = [];
  try {
    const apiUrl = INTERNAL_API_URL;
    let nextUrl: string | null = `${apiUrl}/laws/?page_size=200`;

    while (nextUrl) {
      const res: Response = await fetch(nextUrl, { next: { revalidate: 86400 } });
      if (!res.ok) break;
      const data: { results?: Array<{ id: string }>; next?: string | null } = await res.json();
      const results: Array<{ id: string }> = data.results || [];
      lawRoutes.push(
        ...results.map((law) => ({
          url: `${BASE_URL}/leyes/${encodeURIComponent(law.id)}`,
          lastModified: new Date(),
          changeFrequency: 'monthly' as const,
          priority: 0.7,
        }))
      );
      nextUrl = data.next || null;
    }
  } catch {
    // API unavailable at build time — skip dynamic routes
  }

  return [...staticRoutes, ...contentRoutes, ...browseRoutes, ...lawRoutes];
}
