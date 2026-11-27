import type { MetadataRoute } from 'next';
import { INTERNAL_API_URL } from '@/lib/config';
import { STATE_SLUGS } from '@/lib/states';
import { assertSitemapSize, getLawIds } from '@/lib/sitemap-laws';

// Rendered per request, not prerendered at build: the image build cannot rely
// on reaching the API, and a build-time failure used to bake a sitemap with no
// law pages into the image. The law inventory is cached in memory for 24 h by
// getLawIds, which also keeps the last complete copy when a refresh fails.
export const dynamic = 'force-dynamic';

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

  // Dynamic law routes. getLawIds retries, and throws when no complete
  // inventory is available, so this request answers 5xx instead of
  // publishing a sitemap with the law pages silently missing.
  const lawIds = await getLawIds(INTERNAL_API_URL);
  const lawRoutes: MetadataRoute.Sitemap = lawIds.map((id) => ({
    url: `${BASE_URL}/leyes/${encodeURIComponent(id)}`,
    lastModified: new Date(),
    changeFrequency: 'monthly' as const,
    priority: 0.7,
  }));

  const entries = [...staticRoutes, ...contentRoutes, ...browseRoutes, ...lawRoutes];
  assertSitemapSize(entries.length);
  return entries;
}
