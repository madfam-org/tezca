import Link from 'next/link';
import { notFound } from 'next/navigation';
import { Card, CardContent, Badge } from '@tezca/ui';
import type { Metadata } from 'next';
import { API_BASE_URL } from '@/lib/config';

/* ------------------------------------------------------------------ */
/*  Category metadata                                                  */
/* ------------------------------------------------------------------ */

type CategoryKey =
  | 'civil'
  | 'penal'
  | 'mercantil'
  | 'fiscal'
  | 'laboral'
  | 'administrativo'
  | 'constitucional';

interface CategoryMeta {
  es: string;
  en: string;
  nah: string;
  icon: string;
  desc_es: string;
  desc_en: string;
  desc_nah: string;
}

const CATEGORIES: Record<CategoryKey, CategoryMeta> = {
  civil: {
    es: 'Civil',
    en: 'Civil',
    nah: 'Civil',
    icon: '\u2696\uFE0F',
    desc_es: 'Derecho civil y familiar',
    desc_en: 'Civil and family law',
    desc_nah: 'Tenahuatilli civil',
  },
  penal: {
    es: 'Penal',
    en: 'Criminal',
    nah: 'Te\u012Bxnamiquiliztli',
    icon: '\uD83D\uDD12',
    desc_es: 'Derecho penal y procesal penal',
    desc_en: 'Criminal and procedural criminal law',
    desc_nah: 'Tenahuatilli te\u012Bxnamiquiliztli',
  },
  mercantil: {
    es: 'Mercantil',
    en: 'Commercial',
    nah: 'Tlanamacaliztli',
    icon: '\uD83D\uDCBC',
    desc_es: 'Derecho mercantil y comercial',
    desc_en: 'Commercial and business law',
    desc_nah: 'Tenahuatilli tlanamacaliztli',
  },
  fiscal: {
    es: 'Fiscal',
    en: 'Tax',
    nah: 'Tequitl',
    icon: '\uD83D\uDCB0',
    desc_es: 'Derecho fiscal y tributario',
    desc_en: 'Tax and fiscal law',
    desc_nah: 'Tenahuatilli tequitl',
  },
  laboral: {
    es: 'Laboral',
    en: 'Labor',
    nah: 'Tequipanoliztli',
    icon: '\uD83D\uDC77',
    desc_es: 'Derecho laboral y seguridad social',
    desc_en: 'Labor and social security law',
    desc_nah: 'Tenahuatilli tequipanoliztli',
  },
  administrativo: {
    es: 'Administrativo',
    en: 'Administrative',
    nah: 'Teuctlahtoani',
    icon: '\uD83C\uDFDB\uFE0F',
    desc_es: 'Derecho administrativo y regulatorio',
    desc_en: 'Administrative and regulatory law',
    desc_nah: 'Tenahuatilli teuctlahtoani',
  },
  constitucional: {
    es: 'Constitucional',
    en: 'Constitutional',
    nah: 'Tenahuatilli',
    icon: '\uD83D\uDCDC',
    desc_es: 'Derecho constitucional',
    desc_en: 'Constitutional law',
    desc_nah: 'Tenahuatilli hueyi',
  },
};

const VALID_CATEGORIES = new Set<string>(Object.keys(CATEGORIES));

function isValidCategory(value: string): value is CategoryKey {
  return VALID_CATEGORIES.has(value);
}

/* ------------------------------------------------------------------ */
/*  Trilingual content strings                                         */
/* ------------------------------------------------------------------ */

const content = {
  es: {
    home: 'Inicio',
    categories: 'Categorias',
    lawsFound: 'leyes encontradas',
    noLaws: 'No se encontraron leyes en esta categoria.',
    noLawsSub: 'Intenta explorar otras categorias o vuelve al inicio.',
    tier: 'Nivel',
    type: 'Tipo',
    viewLaw: 'Ver ley',
    page: 'Pagina',
    of: 'de',
    previous: 'Anterior',
    next: 'Siguiente',
    errorTitle: 'Error al cargar las leyes',
    errorBody: 'No se pudieron obtener las leyes de esta categoria. Intenta de nuevo mas tarde.',
    backToCategories: 'Volver a categorias',
  },
  en: {
    home: 'Home',
    categories: 'Categories',
    lawsFound: 'laws found',
    noLaws: 'No laws found in this category.',
    noLawsSub: 'Try exploring other categories or go back to home.',
    tier: 'Tier',
    type: 'Type',
    viewLaw: 'View law',
    page: 'Page',
    of: 'of',
    previous: 'Previous',
    next: 'Next',
    errorTitle: 'Error loading laws',
    errorBody: 'Could not fetch laws for this category. Please try again later.',
    backToCategories: 'Back to categories',
  },
  nah: {
    home: 'Caltenco',
    categories: 'Tlamantli',
    lawsFound: 'tenahuatilli onextiloc',
    noLaws: 'Ahmo oncah tenahuatilli ipan inin tlamantli.',
    noLawsSub: 'Xicyeyecolti occe tlamantli ahnozo ximocuepa caltenco.',
    tier: 'Tlanextiliztli',
    type: 'Tlamantli',
    viewLaw: 'Xicnextia tenahuatilli',
    page: 'Amoxihuitl',
    of: 'ic',
    previous: 'Achtopa',
    next: 'Niman',
    errorTitle: 'Tlahtlacolli ic motemohua tenahuatilli',
    errorBody: 'Ahmo hueliz moquixtia tenahuatilli. Xicyeyecolti occeppa.',
    backToCategories: 'Ximocuepa tlamantli',
  },
};

/* ------------------------------------------------------------------ */
/*  API types                                                          */
/* ------------------------------------------------------------------ */

interface LawResult {
  id: string;
  name: string;
  tier: string;
  law_type: string;
  category: string;
  status: string;
  versions?: number;
}

interface LawsApiResponse {
  count: number;
  next: string | null;
  previous: string | null;
  results: LawResult[];
}

/* ------------------------------------------------------------------ */
/*  Data fetching                                                      */
/* ------------------------------------------------------------------ */

const PAGE_SIZE = 50;

async function fetchLawsByCategory(
  category: string,
  page: number,
): Promise<LawsApiResponse | null> {
  try {
    const res = await fetch(
      `${API_BASE_URL}/laws/?category=${encodeURIComponent(category)}&page=${page}&page_size=${PAGE_SIZE}`,
      { next: { revalidate: 3600 } },
    );

    if (!res.ok) return null;
    return (await res.json()) as LawsApiResponse;
  } catch {
    return null;
  }
}

/* ------------------------------------------------------------------ */
/*  Metadata                                                           */
/* ------------------------------------------------------------------ */

export async function generateMetadata({
  params,
}: {
  params: Promise<{ category: string }>;
}): Promise<Metadata> {
  const { category } = await params;
  const siteUrl = process.env.NEXT_PUBLIC_SITE_URL || 'https://tezca.mx';

  if (!isValidCategory(category)) {
    return {
      title: 'Categoria no encontrada — Tezca',
      description: 'La categoria solicitada no existe.',
    };
  }

  const cat = CATEGORIES[category];
  const description = `${cat.desc_es}. Consulta todas las leyes de derecho ${cat.es.toLowerCase()} en Tezca.`;

  return {
    title: `${cat.es} — Categorias — Tezca`,
    description,
    openGraph: {
      title: `${cat.es} — Tezca`,
      description,
      type: 'website',
      url: `${siteUrl}/categorias/${category}`,
      siteName: 'Tezca',
    },
    other: {
      'script:ld+json': JSON.stringify({
        '@context': 'https://schema.org',
        '@type': 'BreadcrumbList',
        itemListElement: [
          {
            '@type': 'ListItem',
            position: 1,
            name: 'Inicio',
            item: siteUrl + '/',
          },
          {
            '@type': 'ListItem',
            position: 2,
            name: 'Categorias',
            item: siteUrl + '/categorias',
          },
          {
            '@type': 'ListItem',
            position: 3,
            name: cat.es,
            item: `${siteUrl}/categorias/${category}`,
          },
        ],
      }),
    },
  };
}

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

function tierLabel(tier: string, lang: 'es' | 'en' | 'nah'): string {
  const map: Record<string, Record<string, string>> = {
    federal: { es: 'Federal', en: 'Federal', nah: 'Hueyaltepetl' },
    state: { es: 'Estatal', en: 'State', nah: 'Altepetl' },
    municipal: { es: 'Municipal', en: 'Municipal', nah: 'Calpulli' },
  };
  return map[tier]?.[lang] ?? tier;
}

function tierVariant(
  tier: string,
): 'default' | 'secondary' | 'outline' | 'destructive' {
  if (tier === 'federal') return 'default';
  if (tier === 'state') return 'secondary';
  return 'outline';
}

/* ------------------------------------------------------------------ */
/*  Page component                                                     */
/* ------------------------------------------------------------------ */

export default async function CategoryDetailPage({
  params,
  searchParams,
}: {
  params: Promise<{ category: string }>;
  searchParams: Promise<{ page?: string }>;
}) {
  const { category } = await params;
  const { page: pageParam } = await searchParams;

  if (!isValidCategory(category)) {
    notFound();
  }

  const cat = CATEGORIES[category];
  const lang = 'es' as const;
  const t = content[lang];

  const currentPage = Math.max(1, parseInt(pageParam || '1', 10) || 1);
  const data = await fetchLawsByCategory(category, currentPage);
  const siteUrl = process.env.NEXT_PUBLIC_SITE_URL || 'https://tezca.mx';

  const totalPages = data ? Math.ceil(data.count / PAGE_SIZE) : 0;

  return (
    <div className="min-h-screen bg-background">
      {/* JSON-LD BreadcrumbList */}
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{
          __html: JSON.stringify({
            '@context': 'https://schema.org',
            '@type': 'BreadcrumbList',
            itemListElement: [
              {
                '@type': 'ListItem',
                position: 1,
                name: 'Inicio',
                item: siteUrl + '/',
              },
              {
                '@type': 'ListItem',
                position: 2,
                name: 'Categorias',
                item: siteUrl + '/categorias',
              },
              {
                '@type': 'ListItem',
                position: 3,
                name: cat.es,
                item: `${siteUrl}/categorias/${category}`,
              },
            ],
          }),
        }}
      />

      {/* Hero section */}
      <div className="bg-primary text-primary-foreground">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12 sm:py-16">
          {/* Breadcrumb */}
          <nav className="mb-6 text-sm" aria-label="Breadcrumb">
            <ol className="flex items-center gap-1.5">
              <li>
                <Link
                  href="/"
                  className="text-primary-foreground/70 hover:text-primary-foreground transition-colors"
                >
                  {t.home}
                </Link>
              </li>
              <li className="text-primary-foreground/40" aria-hidden="true">
                /
              </li>
              <li>
                <Link
                  href="/categorias"
                  className="text-primary-foreground/70 hover:text-primary-foreground transition-colors"
                >
                  {t.categories}
                </Link>
              </li>
              <li className="text-primary-foreground/40" aria-hidden="true">
                /
              </li>
              <li className="text-primary-foreground font-medium" aria-current="page">
                {cat.es}
              </li>
            </ol>
          </nav>

          <div className="flex items-center gap-4">
            <span
              className="text-4xl sm:text-5xl select-none"
              role="img"
              aria-hidden="true"
            >
              {cat.icon}
            </span>
            <div>
              <h1 className="text-3xl sm:text-4xl font-bold tracking-tight">
                {cat[lang]}
              </h1>
              <p className="mt-1 text-lg text-primary-foreground/80">
                {cat.desc_es}
              </p>
            </div>
          </div>

          {/* Count badge */}
          {data && (
            <div className="mt-6">
              <span className="inline-flex items-center gap-2 rounded-full bg-primary-foreground/10 px-4 py-1.5 text-sm font-medium">
                {data.count.toLocaleString()} {t.lawsFound}
              </span>
            </div>
          )}
        </div>
      </div>

      {/* Main content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10 sm:py-14">
        {/* Error state */}
        {!data && (
          <div className="text-center py-16">
            <div className="mx-auto max-w-md rounded-lg bg-destructive/10 p-8">
              <h2 className="text-lg font-semibold text-destructive mb-2">
                {t.errorTitle}
              </h2>
              <p className="text-sm text-destructive/80 mb-6">
                {t.errorBody}
              </p>
              <Link
                href="/categorias"
                className="inline-flex items-center justify-center rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors"
              >
                {t.backToCategories}
              </Link>
            </div>
          </div>
        )}

        {/* Empty state */}
        {data && data.results.length === 0 && (
          <div className="text-center py-16">
            <p className="text-lg text-muted-foreground">{t.noLaws}</p>
            <p className="mt-2 text-sm text-muted-foreground">
              {t.noLawsSub}
            </p>
            <Link
              href="/categorias"
              className="mt-6 inline-flex items-center justify-center rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors"
            >
              {t.backToCategories}
            </Link>
          </div>
        )}

        {/* Law list */}
        {data && data.results.length > 0 && (
          <>
            <div className="space-y-4">
              {data.results.map((law) => (
                <Link
                  key={law.id}
                  href={`/laws/${law.id}`}
                  className="block group focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 rounded-xl"
                >
                  <Card className="transition-all duration-200 hover:shadow-lg hover:border-primary/30 border border-border">
                    <CardContent className="p-4 sm:p-6">
                      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
                        {/* Law info */}
                        <div className="flex-1 min-w-0">
                          <h2 className="text-base sm:text-lg font-semibold text-foreground group-hover:text-primary transition-colors truncate">
                            {law.name}
                          </h2>
                          <div className="mt-2 flex flex-wrap items-center gap-2">
                            <Badge variant={tierVariant(law.tier)} className="text-xs capitalize">
                              {tierLabel(law.tier, lang)}
                            </Badge>
                            {law.law_type && (
                              <Badge variant="outline" className="text-xs capitalize">
                                {law.law_type.replace(/_/g, ' ')}
                              </Badge>
                            )}
                            {law.status && law.status !== 'vigente' && (
                              <Badge
                                variant="secondary"
                                className="text-xs bg-muted text-muted-foreground"
                              >
                                {law.status}
                              </Badge>
                            )}
                          </div>
                        </div>

                        {/* Action hint */}
                        <span className="hidden sm:inline-flex items-center text-sm font-medium text-primary opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0">
                          {t.viewLaw} &rarr;
                        </span>
                      </div>
                    </CardContent>
                  </Card>
                </Link>
              ))}
            </div>

            {/* Pagination */}
            {totalPages > 1 && (
              <nav
                className="mt-10 flex items-center justify-center gap-2"
                aria-label="Pagination"
              >
                {currentPage > 1 && (
                  <Link
                    href={`/categorias/${category}?page=${currentPage - 1}`}
                    className="inline-flex items-center justify-center rounded-lg border border-border bg-background px-4 py-2 text-sm font-medium text-foreground hover:bg-muted transition-colors"
                  >
                    &larr; {t.previous}
                  </Link>
                )}

                <span className="text-sm text-muted-foreground px-3">
                  {t.page} {currentPage} {t.of} {totalPages}
                </span>

                {currentPage < totalPages && (
                  <Link
                    href={`/categorias/${category}?page=${currentPage + 1}`}
                    className="inline-flex items-center justify-center rounded-lg border border-border bg-background px-4 py-2 text-sm font-medium text-foreground hover:bg-muted transition-colors"
                  >
                    {t.next} &rarr;
                  </Link>
                )}
              </nav>
            )}
          </>
        )}
      </div>
    </div>
  );
}
