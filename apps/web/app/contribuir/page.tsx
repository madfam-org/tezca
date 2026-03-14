import Link from 'next/link';
import { ArrowLeft, Users, Upload, Code2 } from 'lucide-react';
import { Card, CardContent } from '@tezca/ui';
import { LanguageToggle } from '@/components/LanguageToggle';
import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Contribuir — Tezca',
  description: 'Contribuye a Tezca: ayuda a completar el acervo legislativo mexicano con tu experiencia o datos.',
};

const content = {
  es: {
    back: 'Volver al inicio',
    hero: {
      title: 'Contribuir',
      subtitle: 'Ayuda a completar el espejo de la ley',
    },
    gap: {
      title: 'La brecha de datos',
      body: 'Tezca alberga m\u00e1s de 35,000 leyes y 3.5 millones de art\u00edculos indexados, pero el universo legislativo mexicano es a\u00fan m\u00e1s vasto. Reglamentos municipales, normas oficiales, tratados internacionales y jurisprudencia siguen dispersos en formatos inaccesibles. Cada contribuci\u00f3n \u2014 ya sea una fuente de datos, una correcci\u00f3n textual o conocimiento especializado \u2014 acerca a M\u00e9xico a tener un sistema jur\u00eddico verdaderamente abierto.',
    },
    cards: {
      expert: {
        title: 'Contacto de experto',
        desc: '\u00bfEres abogado, acad\u00e9mico o especialista en derecho mexicano? Tu conocimiento puede ayudar a verificar, clasificar y enriquecer el acervo legislativo.',
        cta: 'Ofrecer experiencia',
      },
      data: {
        title: 'Enviar datos',
        desc: 'Tienes acceso a gacetas oficiales, reglamentos municipales u otras fuentes legislativas? Env\u00edanos la informaci\u00f3n para integrarla a la plataforma.',
        cta: 'Enviar datos',
      },
    },
    openSource: {
      title: 'C\u00f3digo abierto',
      body: 'Tezca es software libre bajo la licencia AGPL-3.0. El c\u00f3digo fuente est\u00e1 disponible para auditor\u00eda, contribuci\u00f3n y reutilizaci\u00f3n. Si eres desarrollador, tambi\u00e9n puedes contribuir directamente al c\u00f3digo.',
      link: 'Ver repositorio en GitHub',
    },
  },
  en: {
    back: 'Back to home',
    hero: {
      title: 'Contribute',
      subtitle: 'Help complete the mirror of the law',
    },
    gap: {
      title: 'The data gap',
      body: 'Tezca hosts over 35,000 laws and 3.5 million indexed articles, but the Mexican legislative universe is even vaster. Municipal regulations, official standards, international treaties, and case law remain scattered across inaccessible formats. Every contribution \u2014 whether a data source, a textual correction, or specialized knowledge \u2014 brings Mexico closer to a truly open legal system.',
    },
    cards: {
      expert: {
        title: 'Expert contact',
        desc: 'Are you a lawyer, academic, or specialist in Mexican law? Your knowledge can help verify, classify, and enrich the legislative collection.',
        cta: 'Offer expertise',
      },
      data: {
        title: 'Submit data',
        desc: 'Do you have access to official gazettes, municipal regulations, or other legislative sources? Send us the information to integrate it into the platform.',
        cta: 'Submit data',
      },
    },
    openSource: {
      title: 'Open source',
      body: 'Tezca is free software under the AGPL-3.0 license. The source code is available for audit, contribution, and reuse. If you are a developer, you can also contribute directly to the codebase.',
      link: 'View repository on GitHub',
    },
  },
  nah: {
    back: 'Xicmocuepa caltenco',
    hero: {
      title: 'Xicpal\u0113hui',
      subtitle: 'Xicpal\u0113hui ic motl\u0101lia in tezcatl in tenahuatilli',
    },
    gap: {
      title: 'In tlamachiliz\u0101huilli',
      body: 'Tezca quipiya achi 35,000 tenahuatilli ihuan 3.5 mill\u00f3n tlanahuatilli, macihu\u012b in m\u0113xihcatl tenahuatiliz c\u0113m\u0101n\u0101huac oc huey. Calpulli tenahuatilli, normas oficiales, tratados ihuan jurisprudencia oc mochantia ahmo huel\u012bz moqu\u012bxtia. Mochi tlapal\u0113huiliztli \u2014 tlamachiliz, tlahcuilōlli \u0101hn\u014dzo tlamatiliztli \u2014 quihualh\u012bcac M\u0113xihco ic c\u0113 tenahuatiliz t\u0113y\u0101canaliztli nelli tlapo\u0101lli.',
    },
    cards: {
      expert: {
        title: 'Tlamatini t\u0113n\u014dn\u014dtzaliztli',
        desc: 'Tiqu\u012bximati in m\u0113xihcatl tenahuatilli? Motlamatiliztli hueliz quipal\u0113huia ic monel\u012blia ihuan mocuep\u012blia in tenahuatilli.',
        cta: 'Xicn\u0113xtia motlamatiliztli',
      },
      data: {
        title: 'Xict\u012btlani tlamachiliztli',
        desc: 'Ticpiya gacetas oficiales, calpulli tenahuatilli \u0101hn\u014dzo oc c\u0113 tenahuatiliz tlamachilizpial\u014dyan? Xict\u012btlani ic motemachilia.',
        cta: 'Xict\u012btlani tlamachiliztli',
      },
    },
    openSource: {
      title: 'Tlapo\u0101lli tlahcuil\u014dlli',
      body: 'Tezca c\u0113 tlapo\u0101lli t\u0113p\u014dzmachiy\u014dtl ica AGPL-3.0. In tlahcuil\u014dlli moqu\u012bxtia ic motlachiya, mopal\u0113huia ihuan mocuep\u012blia. Intl\u0101 ticchihua t\u0113p\u014dzmachiy\u014dtl, n\u014d hueliz ticpal\u0113huia niman ic tlahcuil\u014dlli.',
      link: 'Xiquitta GitHub',
    },
  },
};

export default async function ContribuirPage({
  searchParams,
}: {
  searchParams: Promise<{ lang?: string }>;
}) {
  const params = await searchParams;
  const lang = (['es', 'en', 'nah'].includes(params.lang ?? '') ? params.lang : 'es') as 'es' | 'en' | 'nah';
  const t = content[lang];

  return (
    <div className="min-h-screen bg-background">
      {/* Hero section */}
      <section className="relative overflow-hidden bg-gradient-to-br from-primary-900 via-primary-800 to-secondary-900 px-4 sm:px-6 py-20 sm:py-28 lg:py-36">
        <div className="absolute inset-0 bg-grid-pattern opacity-10" />
        <div className="relative mx-auto max-w-3xl text-center">
          <h1 className="font-display text-5xl sm:text-7xl lg:text-8xl font-bold tracking-tight text-white">
            {t.hero.title}
          </h1>
          <p className="mt-4 sm:mt-6 font-serif text-xl sm:text-2xl lg:text-3xl text-primary-200 italic">
            {t.hero.subtitle}
          </p>
        </div>
      </section>

      {/* Navigation bar */}
      <div className="container mx-auto px-4 sm:px-6 py-6 max-w-3xl">
        <div className="flex items-center justify-between">
          <Link
            href="/"
            className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors"
          >
            <ArrowLeft className="h-4 w-4" />
            {t.back}
          </Link>
          <LanguageToggle />
        </div>
      </div>

      {/* Content */}
      <div className="container mx-auto px-4 sm:px-6 pb-16 sm:pb-24 max-w-3xl">
        {/* Data gap explanation */}
        <section className="space-y-4">
          <h2 className="font-serif text-2xl sm:text-3xl font-semibold tracking-tight text-foreground">
            {t.gap.title}
          </h2>
          <p className="font-serif text-base sm:text-lg leading-relaxed text-muted-foreground">
            {t.gap.body}
          </p>
        </section>

        {/* CTA cards */}
        <section className="mt-14 sm:mt-20 grid gap-6 sm:grid-cols-2">
          <Link href="/contribuir/contacto" className="group">
            <Card className="h-full transition-shadow hover:shadow-md">
              <CardContent className="p-6 space-y-4">
                <div className="flex items-center gap-3">
                  <Users className="h-6 w-6 text-primary" aria-hidden="true" />
                  <h3 className="font-serif text-xl font-semibold text-foreground">
                    {t.cards.expert.title}
                  </h3>
                </div>
                <p className="text-sm leading-relaxed text-muted-foreground">
                  {t.cards.expert.desc}
                </p>
                <span className="inline-flex items-center text-sm font-medium text-primary group-hover:underline">
                  {t.cards.expert.cta}
                  <ArrowLeft className="ml-1.5 h-3.5 w-3.5 rotate-180" aria-hidden="true" />
                </span>
              </CardContent>
            </Card>
          </Link>

          <Link href="/contribuir/enviar-datos" className="group">
            <Card className="h-full transition-shadow hover:shadow-md">
              <CardContent className="p-6 space-y-4">
                <div className="flex items-center gap-3">
                  <Upload className="h-6 w-6 text-primary" aria-hidden="true" />
                  <h3 className="font-serif text-xl font-semibold text-foreground">
                    {t.cards.data.title}
                  </h3>
                </div>
                <p className="text-sm leading-relaxed text-muted-foreground">
                  {t.cards.data.desc}
                </p>
                <span className="inline-flex items-center text-sm font-medium text-primary group-hover:underline">
                  {t.cards.data.cta}
                  <ArrowLeft className="ml-1.5 h-3.5 w-3.5 rotate-180" aria-hidden="true" />
                </span>
              </CardContent>
            </Card>
          </Link>
        </section>

        {/* Open source */}
        <section className="mt-14 sm:mt-20 space-y-4">
          <div className="flex items-center gap-3">
            <Code2 className="h-6 w-6 text-primary" aria-hidden="true" />
            <h2 className="font-serif text-2xl sm:text-3xl font-semibold tracking-tight text-foreground">
              {t.openSource.title}
            </h2>
          </div>
          <p className="font-serif text-base sm:text-lg leading-relaxed text-muted-foreground">
            {t.openSource.body}
          </p>
          <a
            href="https://github.com/madfam/tezca"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 text-primary hover:underline font-medium"
          >
            <Code2 className="h-4 w-4" />
            {t.openSource.link}
          </a>
        </section>
      </div>
    </div>
  );
}
