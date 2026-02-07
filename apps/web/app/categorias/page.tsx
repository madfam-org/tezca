import Link from 'next/link';
import { Card, CardContent } from '@tezca/ui';
import type { Metadata } from 'next';

export function generateMetadata(): Metadata {
  return {
    title: 'Categorias — Tezca',
    description:
      'Explora la legislacion mexicana por categoria: civil, penal, mercantil, fiscal, laboral, administrativo, constitucional.',
    openGraph: {
      title: 'Categorias — Tezca',
      description:
        'Explora la legislacion mexicana por categoria juridica.',
      type: 'website',
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
            item:
              (process.env.NEXT_PUBLIC_SITE_URL || 'https://tezca.mx') + '/',
          },
          {
            '@type': 'ListItem',
            position: 2,
            name: 'Categorias',
            item:
              (process.env.NEXT_PUBLIC_SITE_URL || 'https://tezca.mx') +
              '/categorias',
          },
        ],
      }),
    },
  };
}

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

const content = {
  es: {
    title: 'Categorias',
    subtitle: 'Explora la legislacion mexicana por categoria juridica',
    home: 'Inicio',
    viewCategory: 'Ver leyes',
  },
  en: {
    title: 'Categories',
    subtitle: 'Explore Mexican legislation by legal category',
    home: 'Home',
    viewCategory: 'View laws',
  },
  nah: {
    title: 'Tlamantli',
    subtitle: 'Xictlachia in mexihcatl tenahuatilli ic tlamantli',
    home: 'Caltenco',
    viewCategory: 'Xicnextia tenahuatilli',
  },
};

/**
 * CategoryCard — a single category tile.
 * This is a server-only presentational component (no hooks, no handlers).
 */
function CategoryCard({
  slug,
  category,
  lang,
  viewLabel,
}: {
  slug: CategoryKey;
  category: CategoryMeta;
  lang: 'es' | 'en' | 'nah';
  viewLabel: string;
}) {
  const name = category[lang];
  const desc =
    lang === 'en'
      ? category.desc_en
      : lang === 'nah'
        ? category.desc_nah
        : category.desc_es;

  return (
    <Link
      href={`/categorias/${slug}`}
      className="group block focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 rounded-xl"
    >
      <Card className="h-full transition-all duration-200 hover:shadow-lg hover:-translate-y-1 border border-border hover:border-primary/30">
        <CardContent className="p-6 flex flex-col gap-3">
          <span
            className="text-4xl select-none"
            role="img"
            aria-hidden="true"
          >
            {category.icon}
          </span>
          <h2 className="text-xl font-bold text-foreground group-hover:text-primary transition-colors">
            {name}
          </h2>
          <p className="text-sm text-muted-foreground leading-relaxed">
            {desc}
          </p>
          <span className="mt-auto inline-flex items-center text-sm font-medium text-primary opacity-0 group-hover:opacity-100 transition-opacity">
            {viewLabel} &rarr;
          </span>
        </CardContent>
      </Card>
    </Link>
  );
}

/**
 * CategoriesIndexPage — server component listing all legal categories.
 *
 * Because this is a server component it cannot call `useLang()`.
 * We render all three language blocks and use a client wrapper
 * (LangSwitch) to conditionally display the active language, OR
 * we can simply default to Spanish for the server-rendered page
 * (consistent with the rest of the App Router pages that use
 * `generateMetadata` for SEO in Spanish).
 *
 * For maximum simplicity and SEO, the page renders in Spanish
 * with all content statically available for crawlers.  The
 * client-side LanguageToggle in the site layout already handles
 * the lang attribute on <html>.
 */
export default function CategoriesIndexPage() {
  // Default language for the server-rendered page (SEO-optimized).
  const lang = 'es' as const;
  const t = content[lang];
  const siteUrl = process.env.NEXT_PUBLIC_SITE_URL || 'https://tezca.mx';

  const categoryKeys = Object.keys(CATEGORIES) as CategoryKey[];

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
            ],
          }),
        }}
      />

      {/* Hero */}
      <div className="bg-primary text-primary-foreground">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12 sm:py-16">
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
              <li className="text-primary-foreground font-medium" aria-current="page">
                {t.title}
              </li>
            </ol>
          </nav>
          <h1 className="text-3xl sm:text-4xl font-bold tracking-tight">
            {t.title}
          </h1>
          <p className="mt-2 text-lg text-primary-foreground/80">
            {t.subtitle}
          </p>
        </div>
      </div>

      {/* Category grid */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10 sm:py-14">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
          {categoryKeys.map((slug) => (
            <CategoryCard
              key={slug}
              slug={slug}
              category={CATEGORIES[slug]}
              lang={lang}
              viewLabel={t.viewCategory}
            />
          ))}
        </div>
      </div>
    </div>
  );
}
