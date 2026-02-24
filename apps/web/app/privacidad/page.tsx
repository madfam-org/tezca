import Link from 'next/link';
import { ArrowLeft, Globe } from 'lucide-react';
import { LanguageToggle } from '@/components/LanguageToggle';
import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Política de Privacidad — Tezca',
  description: 'Política de privacidad de Tezca, plataforma de legislación mexicana digitalizada.',
};

const content = {
  es: {
    back: 'Volver al inicio',
    title: 'Política de Privacidad',
    lastUpdated: 'Última actualización: 6 de febrero de 2026',
    sections: [
      {
        title: 'Recopilación de Datos',
        body: 'Actualmente, Tezca no recopila datos personales de sus usuarios. No se requiere registro, inicio de sesión ni cuenta de usuario para acceder al contenido del sitio. No utilizamos cookies de rastreo ni herramientas de analítica que recopilen información personal identificable.',
      },
      {
        title: 'Almacenamiento Local',
        body: 'El sitio utiliza el almacenamiento local del navegador (localStorage) exclusivamente para guardar preferencias de interfaz como el tema visual (claro/oscuro) y el idioma preferido. Esta información nunca se transmite a nuestros servidores ni a terceros.',
      },
      {
        title: 'Cumplimiento Normativo',
        body: 'Aunque actualmente no recopilamos datos personales, nos comprometemos a cumplir con la Ley Federal de Protección de Datos Personales en Posesión de los Particulares (LFPDPPP) y su Reglamento en caso de que en el futuro se implemente cualquier funcionalidad que requiera el tratamiento de datos personales. En tal caso, esta política se actualizará con el aviso de privacidad correspondiente.',
      },
      {
        title: 'Contacto',
        body: 'Para cualquier consulta relacionada con la privacidad de sus datos, puede contactarnos en: admin@madfam.io',
      },
    ],
    termsLink: 'Consultar Términos y Condiciones',
  },
  en: {
    back: 'Back to home',
    title: 'Privacy Policy',
    lastUpdated: 'Last updated: February 6, 2026',
    sections: [
      {
        title: 'Data Collection',
        body: 'Currently, Tezca does not collect personal data from its users. No registration, login, or user account is required to access the site content. We do not use tracking cookies or analytics tools that collect personally identifiable information.',
      },
      {
        title: 'Local Storage',
        body: 'The site uses browser local storage (localStorage) exclusively to save interface preferences such as the visual theme (light/dark) and preferred language. This information is never transmitted to our servers or third parties.',
      },
      {
        title: 'Regulatory Compliance',
        body: 'Although we currently do not collect personal data, we are committed to complying with the Mexican Federal Law on Protection of Personal Data Held by Private Parties (LFPDPPP) and its Regulations in the event that any functionality requiring the processing of personal data is implemented in the future. In such case, this policy will be updated with the corresponding privacy notice.',
      },
      {
        title: 'Contact',
        body: 'For any inquiries related to the privacy of your data, you may contact us at: admin@madfam.io',
      },
    ],
    termsLink: 'View Terms and Conditions',
  },
  nah: {
    back: 'Xicmocuepa caltenco',
    title: 'Ichtacayōtl Tlanāhuatilli',
    lastUpdated: 'Tlāmian yancuīliztli: 6 de febrero de 2026',
    sections: [
      {
        title: 'Tlamachiliztli Tlacēntīliztli',
        body: 'Āxcān, Tezca ahmo quicēntīlia tlamachiliztli in tetlahtōlpialōyan. Ahmo monequi moīxcuīlia, monemītia, ahnōzo cuenta ic tlahcuilōlpan quīxtia. Ahmo tictēquitiltia cookies ahnōzo tlamachiliztli tēpōzmachiyōtl.',
      },
      {
        title: 'Tlahcuilōlpan Tlapiyaliztli',
        body: 'In tlahcuilōlpan tictēquitiltia localStorage zan ic tlapepenilistli quēmeh tema (tlāhuīlli/tlīlli) ihuan tlahtōlli. Inīn tlamachiliztli ahmo quīza totēpōzmachiyōtl ahnōzo tlateōchīhualli.',
      },
      {
        title: 'Tenahuatiliz Neltilīliztli',
        body: 'Macihuī āxcān ahmo ticēntīlia tlamachiliztli, timonāhuatia ticneltilia in LFPDPPP ihuan ītlanahuatilli intlā mōztla monequi tlamachiliztli. Ihcuāc, inīn tlanāhuatilli moyancuīlia.',
      },
      {
        title: 'Tlanōnōtzaliztli',
        body: 'Ic mochi tlatlanīliztli ichtacayōtl: admin@madfam.io',
      },
    ],
    termsLink: 'Xiquitta Tlanahuatilli ihuan Tlahtōltzin',
  },
};

export default async function PrivacidadPage({
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
        <div className="mb-10">
          <div className="flex items-center gap-3 mb-3">
            <Globe className="h-7 w-7 text-primary-600" />
            <h1 className="text-2xl sm:text-3xl font-bold tracking-tight">{t.title}</h1>
          </div>
          <p className="text-sm text-muted-foreground">{t.lastUpdated}</p>
        </div>

        {/* Sections */}
        <div className="space-y-8">
          {t.sections.map((section) => (
            <section key={section.title} className="space-y-3">
              <h2 className="text-lg font-semibold text-foreground">{section.title}</h2>
              <p className="text-sm sm:text-base leading-relaxed text-muted-foreground">{section.body}</p>
            </section>
          ))}
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
