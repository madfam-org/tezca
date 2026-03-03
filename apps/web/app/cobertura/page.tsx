import Link from 'next/link';
import { ArrowLeft, BarChart3, ExternalLink, Users } from 'lucide-react';
import { Card, CardContent } from '@tezca/ui';
import { LanguageToggle } from '@/components/LanguageToggle';
import type { Metadata } from 'next';
import { CoverageDashboard } from '@/components/coverage/CoverageDashboard';

export const metadata: Metadata = {
  title: 'Cobertura de Datos — Tezca',
  description: 'Progreso de captura del universo jurídico mexicano. Consulta qué leyes tenemos y cuáles faltan.',
};

const content = {
  es: {
    back: 'Volver al inicio',
    hero: {
      title: 'Cobertura de Datos',
      subtitle: 'El estado del universo jurídico mexicano en Tezca',
    },
    intro: 'Tezca aspira a capturar la totalidad del marco jurídico mexicano: leyes federales, estatales, municipales, normas oficiales, tratados internacionales, regulaciones y jurisprudencia. Esta página muestra nuestro progreso en tiempo real.',
    methodology: {
      title: 'Metodología',
      body: 'Los conteos del "universo conocido" provienen de fuentes oficiales: la Cámara de Diputados para leyes federales, el Orden Jurídico Nacional (OJN) para legislación estatal, CONAMER para regulaciones, y la SCJN para jurisprudencia. Los conteos de "capturados" reflejan documentos descargados, parseados e indexados en nuestra base de datos. Las barras verdes indican cobertura mayor al 90%, amarillas entre 50-90%, y rojas menor al 50%.',
    },
    help: {
      title: '¿Cómo puedes ayudar?',
      body: 'Si eres investigador, funcionario público, o abogado con acceso a datos legislativos que nos faltan, puedes contribuir directamente.',
      cta: 'Contribuir datos',
      ctaLink: '/contribuir',
      partnership: 'Convocatoria institucional',
      partnershipLink: '/convocatoria',
    },
    sources: {
      title: 'Fuentes de datos',
      items: [
        { name: 'Cámara de Diputados', url: 'https://www.diputados.gob.mx/LeyesBiblio/', desc: 'Leyes federales vigentes' },
        { name: 'Orden Jurídico Nacional', url: 'https://www.ordenjuridico.gob.mx/', desc: 'Legislación estatal y municipal' },
        { name: 'Diario Oficial de la Federación', url: 'https://dof.gob.mx/', desc: 'NOMs, reglamentos, decretos' },
        { name: 'CONAMER', url: 'https://catalogonacional.gob.mx/', desc: 'Catálogo Nacional de Regulaciones' },
        { name: 'SRE — Tratados', url: 'https://cja.sre.gob.mx/tratadosmexico/', desc: 'Tratados internacionales' },
        { name: 'SCJN', url: 'https://sjf.scjn.gob.mx/', desc: 'Jurisprudencia y tesis aisladas' },
      ],
    },
    license: 'Tezca es software libre bajo licencia AGPL-3.0. Todos los datos legislativos son de dominio público.',
  },
  en: {
    back: 'Back to home',
    hero: {
      title: 'Data Coverage',
      subtitle: 'The state of Mexico\'s legal universe in Tezca',
    },
    intro: 'Tezca aims to capture the entirety of Mexico\'s legal framework: federal, state, and municipal laws, official standards, international treaties, regulations, and case law. This page shows our real-time progress.',
    methodology: {
      title: 'Methodology',
      body: 'The "known universe" counts come from official sources: the Chamber of Deputies for federal laws, the National Legal Order (OJN) for state legislation, CONAMER for regulations, and the SCJN for case law. The "captured" counts reflect documents downloaded, parsed, and indexed in our database. Green bars indicate coverage above 90%, yellow between 50-90%, and red below 50%.',
    },
    help: {
      title: 'How you can help',
      body: 'If you are a researcher, public servant, or attorney with access to legislative data we\'re missing, you can contribute directly.',
      cta: 'Contribute data',
      ctaLink: '/contribuir',
      partnership: 'Institutional partnership',
      partnershipLink: '/convocatoria',
    },
    sources: {
      title: 'Data Sources',
      items: [
        { name: 'Chamber of Deputies', url: 'https://www.diputados.gob.mx/LeyesBiblio/', desc: 'Current federal laws' },
        { name: 'National Legal Order', url: 'https://www.ordenjuridico.gob.mx/', desc: 'State and municipal legislation' },
        { name: 'Official Federal Gazette', url: 'https://dof.gob.mx/', desc: 'NOMs, regulations, decrees' },
        { name: 'CONAMER', url: 'https://catalogonacional.gob.mx/', desc: 'National Regulation Catalog' },
        { name: 'SRE — Treaties', url: 'https://cja.sre.gob.mx/tratadosmexico/', desc: 'International treaties' },
        { name: 'SCJN', url: 'https://sjf.scjn.gob.mx/', desc: 'Case law and isolated theses' },
      ],
    },
    license: 'Tezca is free software under the AGPL-3.0 license. All legislative data is in the public domain.',
  },
  nah: {
    back: 'Xicmocuepa caltenco',
    hero: {
      title: 'Tlamachiliz Cobertura',
      subtitle: 'In mēxihcatl tenahuatilli cemānāhuac ipan Tezca',
    },
    intro: 'Tezca quināmiqui quipiya mochi in mēxihcatl tenahuatiliz tlamachiliztli: federal, altepetl, calpulli tenahuatilli, NOMs, tlanōnōtzaliztli, ihuan jurisprudencia. Inīn āmatl quināmiqui totlachihuaz.',
    methodology: {
      title: 'Tlachihualiztli',
      body: 'In "cemānāhuac" tlapohualli ītēuctlahtōlpialōyan: Cámara de Diputados ic federal tenahuatilli, OJN ic altepetl, CONAMER ic regulaciones, ihuan SCJN ic jurisprudencia.',
    },
    help: {
      title: 'Quēnin huelīz tipalēhuia?',
      body: 'Intlā titlamatini, tēuctlahtōqui, ahnōzo abogado ica tlamachiliztli tēch pōlihua, huelīz ticpalēhuia.',
      cta: 'Xicpalēhui',
      ctaLink: '/contribuir',
      partnership: 'Tēnōnōtzaliztli',
      partnershipLink: '/convocatoria',
    },
    sources: {
      title: 'Tlamachilizpialōyan',
      items: [
        { name: 'Cámara de Diputados', url: 'https://www.diputados.gob.mx/LeyesBiblio/', desc: 'Federal tenahuatilli' },
        { name: 'Orden Jurídico Nacional', url: 'https://www.ordenjuridico.gob.mx/', desc: 'Altepetl tenahuatilli' },
        { name: 'DOF', url: 'https://dof.gob.mx/', desc: 'NOMs, reglamentos' },
        { name: 'CONAMER', url: 'https://catalogonacional.gob.mx/', desc: 'Regulaciones' },
        { name: 'SRE', url: 'https://cja.sre.gob.mx/tratadosmexico/', desc: 'Tlanōnōtzaliztli' },
        { name: 'SCJN', url: 'https://sjf.scjn.gob.mx/', desc: 'Jurisprudencia' },
      ],
    },
    license: 'Tezca cē tēpōzmachiyōtl AGPL-3.0. Mochi tenahuatilli āmatl āltepēyōtl.',
  },
};

export default async function CoberturaPage({
  searchParams,
}: {
  searchParams: Promise<{ lang?: string }>;
}) {
  const params = await searchParams;
  const lang = (['es', 'en', 'nah'].includes(params.lang ?? '') ? params.lang : 'es') as 'es' | 'en' | 'nah';
  const t = content[lang];

  return (
    <div className="min-h-screen bg-background">
      {/* Hero */}
      <section className="relative overflow-hidden bg-gradient-to-br from-primary-900 via-primary-800 to-secondary-900 px-4 sm:px-6 py-16 sm:py-24">
        <div className="absolute inset-0 bg-grid-pattern opacity-10" />
        <div className="relative mx-auto max-w-4xl text-center">
          <BarChart3 className="mx-auto h-12 w-12 text-primary-200 mb-4" aria-hidden="true" />
          <h1 className="font-display text-4xl sm:text-6xl font-bold tracking-tight text-white">
            {t.hero.title}
          </h1>
          <p className="mt-4 font-serif text-lg sm:text-xl text-primary-200 italic">
            {t.hero.subtitle}
          </p>
        </div>
      </section>

      {/* Nav bar */}
      <div className="container mx-auto px-4 sm:px-6 py-6 max-w-4xl">
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

      {/* Main content */}
      <div className="container mx-auto px-4 sm:px-6 pb-16 sm:pb-24 max-w-4xl">
        {/* Intro */}
        <p className="font-serif text-base sm:text-lg leading-relaxed text-muted-foreground mb-12">
          {t.intro}
        </p>

        {/* Coverage dashboard (client component) */}
        <CoverageDashboard lang={lang} />

        {/* Methodology */}
        <section className="mt-16 space-y-4">
          <h2 className="font-serif text-xl sm:text-2xl font-semibold tracking-tight text-foreground">
            {t.methodology.title}
          </h2>
          <p className="font-serif text-base leading-relaxed text-muted-foreground">
            {t.methodology.body}
          </p>
        </section>

        {/* How to help */}
        <section className="mt-12 p-6 rounded-lg border border-primary/20 bg-primary/5">
          <div className="flex items-center gap-3 mb-3">
            <Users className="h-5 w-5 text-primary" aria-hidden="true" />
            <h2 className="font-serif text-xl font-semibold text-foreground">
              {t.help.title}
            </h2>
          </div>
          <p className="text-muted-foreground mb-4">
            {t.help.body}
          </p>
          <div className="flex flex-wrap gap-3">
            <Link
              href={t.help.ctaLink}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-md bg-primary text-primary-foreground text-sm font-medium hover:bg-primary/90 transition-colors"
            >
              {t.help.cta}
            </Link>
            <Link
              href={t.help.partnershipLink}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-md border border-border text-sm font-medium hover:bg-muted transition-colors"
            >
              {t.help.partnership}
            </Link>
          </div>
        </section>

        {/* Data Sources */}
        <section className="mt-12 space-y-4">
          <h2 className="font-serif text-xl sm:text-2xl font-semibold tracking-tight text-foreground">
            {t.sources.title}
          </h2>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {t.sources.items.map((source) => (
              <Card key={source.name}>
                <CardContent className="p-4">
                  <a
                    href={source.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1.5 font-semibold text-sm text-foreground hover:text-primary transition-colors"
                  >
                    {source.name}
                    <ExternalLink className="h-3 w-3" />
                  </a>
                  <p className="mt-1 text-xs text-muted-foreground">{source.desc}</p>
                </CardContent>
              </Card>
            ))}
          </div>
        </section>

        {/* License */}
        <p className="mt-12 text-xs text-muted-foreground text-center">
          {t.license}
        </p>
      </div>
    </div>
  );
}
