import Link from 'next/link';
import { ArrowLeft, Shield, ExternalLink, AlertTriangle } from 'lucide-react';
import { LanguageToggle } from '@/components/LanguageToggle';
import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Aviso Legal — Tezca',
  description: 'Aviso legal de Tezca. Este sitio no es fuente oficial del gobierno mexicano.',
};

const content = {
  es: {
    back: 'Volver al inicio',
    title: 'Aviso Legal',
    lastUpdated: 'Última actualización: 6 de febrero de 2026',
    alertTitle: 'Aviso Importante',
    alertBody:
      'Este sitio web no es una publicación oficial del gobierno mexicano. La legislación presentada es de carácter meramente informativo.',
    sections: [
      {
        title: 'Carácter Informativo',
        body: 'Tezca es un proyecto independiente que tiene como objetivo facilitar el acceso ciudadano a la legislación mexicana en formato digital. Todo el contenido legislativo se presenta con fines exclusivamente informativos y de consulta. No sustituye, complementa ni modifica de ninguna manera las publicaciones oficiales del Diario Oficial de la Federación (DOF), las gacetas oficiales estatales ni ninguna otra fuente oficial del gobierno mexicano.',
      },
      {
        title: 'Fuentes y Actualización',
        body: 'Los textos legislativos se obtienen mediante procesamiento automatizado de fuentes públicas, principalmente el Diario Oficial de la Federación y el Orden Jurídico Nacional. Este procesamiento puede introducir errores de formato, omisiones de contenido o retrasos en la actualización. No garantizamos que los textos presentados correspondan exactamente a la versión vigente de la legislación. La fecha de última verificación de cada ley se indica cuando está disponible.',
      },
      {
        title: 'Exclusión de Responsabilidad',
        body: 'Los responsables de esta plataforma no se hacen responsables de: (a) errores u omisiones en los textos legislativos presentados; (b) interpretaciones derivadas del contenido; (c) daños o perjuicios de cualquier naturaleza que pudieran surgir del uso de la información; (d) decisiones legales, comerciales o personales tomadas con base en el contenido de este sitio. Para cualquier situación que requiera certeza jurídica, consulte las fuentes oficiales y a un profesional del derecho.',
      },
      {
        title: 'Verificación con Fuentes Oficiales',
        body: 'Recomendamos encarecidamente verificar toda información legislativa con las siguientes fuentes oficiales antes de utilizarla para cualquier propósito legal o profesional:',
      },
    ],
    termsLink: 'Consultar Términos y Condiciones completos',
    officialSources: 'Fuentes Oficiales Recomendadas',
    dofDesc: 'Publicación oficial de leyes, decretos y acuerdos federales.',
    ojnDesc: 'Compilación oficial de la legislación mexicana federal y estatal.',
  },
  en: {
    back: 'Back to home',
    title: 'Legal Notice',
    lastUpdated: 'Last updated: February 6, 2026',
    alertTitle: 'Important Notice',
    alertBody:
      'This website is not an official publication of the Mexican government. The legislation presented is for informational purposes only.',
    sections: [
      {
        title: 'Informational Nature',
        body: 'Tezca is an independent project aimed at facilitating citizen access to Mexican legislation in digital format. All legislative content is presented exclusively for informational and reference purposes. It does not replace, supplement, or modify in any way the official publications of the Diario Oficial de la Federación (DOF), state official gazettes, or any other official government source.',
      },
      {
        title: 'Sources and Updates',
        body: 'Legislative texts are obtained through automated processing of public sources, primarily the Diario Oficial de la Federación and the Orden Jurídico Nacional. This processing may introduce formatting errors, content omissions, or update delays. We do not guarantee that the texts presented correspond exactly to the current version of the legislation. The date of last verification for each law is indicated when available.',
      },
      {
        title: 'Exclusion of Liability',
        body: 'The operators of this platform are not responsible for: (a) errors or omissions in the legislative texts presented; (b) interpretations derived from the content; (c) damages or losses of any nature that may arise from the use of the information; (d) legal, commercial, or personal decisions made based on the content of this site. For any situation requiring legal certainty, consult official sources and a legal professional.',
      },
      {
        title: 'Verify with Official Sources',
        body: 'We strongly recommend verifying all legislative information with the following official sources before using it for any legal or professional purpose:',
      },
    ],
    termsLink: 'View full Terms and Conditions',
    officialSources: 'Recommended Official Sources',
    dofDesc: 'Official publication of federal laws, decrees, and agreements.',
    ojnDesc: 'Official compilation of Mexican federal and state legislation.',
  },
  nah: {
    back: 'Xicmocuepa caltenco',
    title: 'Tenahuatilizpan Tlanahuatilli',
    lastUpdated: 'Tlāmian yancuīliztli: 6 de febrero de 2026',
    alertTitle: 'Tlahtōlnahuatilli',
    alertBody: 'Inīn tlahcuilōlpan ahmo tēuctlahtōlpialōyan in mēxihcatl tēuctlahtoāni. In tenahuatilli zan tēmachtilistli.',
    sections: [
      {
        title: 'Tēmachtilistli Tlamantli',
        body: 'Tezca cē tlamachiliztli tēpōzmachiyōtl ic mēxihcatl tenahuatilli tēpōzmachiyōtīlpan. Mochi tenahuatilli monextia zan tēmachtilistli. Ahmo quipātia, ahmo quicuepīlia, ahmo quipōhua in tēuctlahtōlpialōyan DOF, gacetas, ahnōzo itlah tēuctlahtōlpialōyan.',
      },
      {
        title: 'Tlahtōlpialōyan ihuan Yancuīliztli',
        body: 'In tenahuatilli monextia ic tēpōzmachiyōtl tlachihualiztli in āltepēyōtl tlahtōlpialōyan. Inīn huelīz quipiya tlahtlacōlli. Ahmo ticneltilia in tenahuatilli nelli āxcān. In tōnalli tlāmian monextia ihcuāc oncah.',
      },
      {
        title: 'Ahmo Tlanāhuatilli Tēchcopa',
        body: 'Tezca ahmo quināhuatia: (a) tlahtlacōlli tenahuatilli; (b) tlahcuilōlli tlanēmilīlli; (c) itlah ahmo cualli; (d) tlanēmilīlli ic inīn tlamachiliztli. Ic itlah monequi neltilīliztli, xiquitta tēuctlahtōlpialōyan ihuan tenahuatilizmatini.',
      },
      {
        title: 'Xicneltili Tēuctlahtōlpialōyan',
        body: 'Ticnāhuatia xicneltili mochi tenahuatilli inīn tēuctlahtōlpialōyan:',
      },
    ],
    termsLink: 'Xiquitta mochi Tlanahuatilli ihuan Tlahtōltzin',
    officialSources: 'Tēuctlahtōlpialōyan',
    dofDesc: 'Tēuctlahtōlpialōyan in federal tenahuatilli, decretos ihuan acuerdos.',
    ojnDesc: 'Tēuctlahtōlpialōyan mēxihcatl tenahuatilli federal ihuan altepetl.',
  },
};

export default async function AvisoLegalPage({
  searchParams,
}: {
  searchParams: Promise<{ lang?: string }>;
}) {
  const params = await searchParams;
  const lang = (['es', 'en', 'nah'].includes(params.lang ?? '') ? params.lang : 'es') as 'es' | 'en' | 'nah';
  const t = content[lang];

  return (
    <div className="min-h-screen bg-background">
      <div className="container mx-auto px-4 sm:px-6 py-8 sm:py-12 max-w-3xl">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <Link
            href="/"
            className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors"
          >
            <ArrowLeft className="h-4 w-4" />
            {t.back}
          </Link>
          <LanguageToggle />
        </div>

        {/* Title block */}
        <div className="mb-8">
          <div className="flex items-center gap-3 mb-3">
            <Shield className="h-7 w-7 text-primary-600" />
            <h1 className="text-2xl sm:text-3xl font-bold tracking-tight">{t.title}</h1>
          </div>
          <p className="text-sm text-muted-foreground">{t.lastUpdated}</p>
        </div>

        {/* Alert card */}
        <div className="mb-10 rounded-lg border border-warning-500/30 bg-warning-50 dark:bg-warning-700/15 p-4 sm:p-5">
          <div className="flex items-start gap-3">
            <AlertTriangle className="h-5 w-5 text-warning-700 dark:text-warning-500 flex-shrink-0 mt-0.5" />
            <div>
              <h2 className="font-semibold text-warning-700 dark:text-warning-500">{t.alertTitle}</h2>
              <p className="mt-1 text-sm text-warning-700 dark:text-warning-500">{t.alertBody}</p>
            </div>
          </div>
        </div>

        {/* Sections */}
        <div className="space-y-8">
          {t.sections.map((section) => (
            <section key={section.title} className="space-y-3">
              <h2 className="text-lg font-semibold text-foreground">{section.title}</h2>
              <p className="text-sm sm:text-base leading-relaxed text-muted-foreground">{section.body}</p>
            </section>
          ))}

          {/* Official sources list */}
          <div className="rounded-lg border border-border bg-card p-4 sm:p-5 space-y-3">
            <h3 className="text-sm font-semibold text-foreground">{t.officialSources}</h3>
            <ul className="space-y-2">
              <li>
                <a
                  href="https://www.dof.gob.mx"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-sm text-primary-600 hover:text-primary-700 dark:text-primary-400 dark:hover:text-primary-300 inline-flex items-center gap-1"
                >
                  Diario Oficial de la Federación (DOF)
                  <ExternalLink className="h-3 w-3" />
                </a>
                <p className="text-xs text-muted-foreground mt-0.5">{t.dofDesc}</p>
              </li>
              <li>
                <a
                  href="https://www.ordenjuridico.gob.mx"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-sm text-primary-600 hover:text-primary-700 dark:text-primary-400 dark:hover:text-primary-300 inline-flex items-center gap-1"
                >
                  Orden Jurídico Nacional (OJN)
                  <ExternalLink className="h-3 w-3" />
                </a>
                <p className="text-xs text-muted-foreground mt-0.5">{t.ojnDesc}</p>
              </li>
            </ul>
          </div>
        </div>

        {/* Link to full terms */}
        <div className="mt-10 pt-6 border-t border-border">
          <Link
            href="/terminos"
            className="text-sm text-primary-600 hover:text-primary-700 dark:text-primary-400 dark:hover:text-primary-300 font-medium"
          >
            {t.termsLink} &rarr;
          </Link>
        </div>
      </div>
    </div>
  );
}
