import Link from 'next/link';
import { ArrowLeft, Landmark, GraduationCap, Building2, Scale, Globe } from 'lucide-react';
import { Card, CardContent } from '@tezca/ui';
import { LanguageToggle } from '@/components/LanguageToggle';
import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Convocatoria Institucional — Tezca',
  description: 'Invitación a instituciones públicas, universidades y colegios de abogados para colaborar en la digitalización del marco jurídico mexicano.',
};

const content = {
  es: {
    back: 'Volver al inicio',
    hero: {
      title: 'Convocatoria Institucional',
      subtitle: 'Colaboremos para hacer accesible todo el marco jurídico mexicano',
    },
    intro: 'Tezca es infraestructura digital pública bajo licencia AGPL-3.0. Nuestra misión es capturar la totalidad del marco jurídico mexicano y hacerlo accesible de manera programática, confiable y gratuita. Para lograrlo, necesitamos la colaboración de instituciones que custodian datos legislativos esenciales.',
    sections: [
      {
        id: 'scjn',
        icon: 'scale',
        title: 'Suprema Corte de Justicia de la Nación',
        what: 'Solicitamos acceso al corpus completo de jurisprudencia y tesis aisladas del Semanario Judicial de la Federación — aproximadamente 500,000 registros de la Décima y Undécima Época.',
        why: 'La jurisprudencia define cómo se interpretan las leyes en la práctica. Sin acceso a estos precedentes, ciudadanos y abogados operan con información incompleta. Digitalizar este corpus permitiría búsqueda de texto completo, análisis de tendencias jurisprudenciales y vinculación automática con la legislación correspondiente.',
        format: 'Formato preferido: bulk JSON o CSV con campos registro, época, instancia, materia, tipo, rubro, texto, precedentes, votos, ponente, fuente.',
        contact: 'admin@madfam.io — Asunto: Colaboración SCJN-Tezca',
      },
      {
        id: 'state',
        icon: 'landmark',
        title: 'Congresos y Gobiernos Estatales',
        what: 'Identificamos brechas significativas en la legislación no legislativa (reglamentos, decretos ejecutivos, acuerdos judiciales) de Michoacán (~2,291 documentos faltantes), San Luis Potosí (~700), Estado de México (~600), Ciudad de México, y Zacatecas.',
        why: 'El Orden Jurídico Nacional registra estas entidades con cero o muy pocos documentos no legislativos, a pesar de que cada estado genera cientos de reglamentos y acuerdos. La normatividad estatal completa es necesaria para que ciudadanos y empresas entiendan sus obligaciones regulatorias.',
        format: 'Aceptamos periódicos oficiales digitalizados, catálogos de normatividad en cualquier formato (PDF, HTML, bases de datos), o acceso a portales de transparencia con documentos legislativos.',
        contact: 'admin@madfam.io — Asunto: Colaboración Estatal-Tezca',
      },
      {
        id: 'municipal',
        icon: 'building',
        title: 'Gobiernos Municipales',
        what: 'México tiene 2,468 municipios. Actualmente cubrimos solo 6. La Ley General de Transparencia obliga a los municipios a publicar su marco normativo, pero muchos portales de transparencia son inaccesibles o incompletos.',
        why: 'La reglamentación municipal afecta directamente la vida cotidiana: uso de suelo, comercio, servicios públicos, seguridad. Sin acceso a estos reglamentos, emprendedores y ciudadanos no pueden conocer las reglas que los gobiernan a nivel local.',
        format: 'Formato preferido: bandos municipales, reglamentos, códigos y lineamientos en PDF o formato digital. También aceptamos catálogos o inventarios de normatividad vigente.',
        contact: 'admin@madfam.io — Asunto: Colaboración Municipal-Tezca',
      },
      {
        id: 'universities',
        icon: 'graduation',
        title: 'Universidades y Centros de Investigación',
        what: 'Buscamos colaboraciones de investigación para validación de datos, análisis de cobertura, y desarrollo de herramientas de procesamiento de lenguaje natural aplicadas al derecho mexicano.',
        why: 'Tezca ofrece un dataset único para investigación jurídica computacional: 35,000+ leyes estructuradas, 3.5 millones de artículos indexados, y metadatos de referencia cruzada. Colaborar con universidades mejora la calidad de los datos y genera conocimiento académico.',
        format: 'Interesados en: proyectos de tesis, investigaciones conjuntas, validación de parsing de texto legal, análisis de cobertura por jurisdicción, y desarrollo de modelos de NLP jurídico.',
        contact: 'admin@madfam.io — Asunto: Colaboración Académica-Tezca',
      },
      {
        id: 'bar',
        icon: 'globe',
        title: 'Colegios de Abogados y Barras',
        what: 'Invitamos a profesionales del derecho a validar la calidad de nuestros datos, identificar leyes faltantes en sus áreas de especialización, y contribuir con su experiencia en la categorización y estructuración de legislación.',
        why: 'Los abogados son los usuarios más exigentes de información legislativa. Su retroalimentación es invaluable para asegurar que Tezca refleja fielmente el estado actual del marco jurídico. Además, sus redes profesionales pueden facilitar el acceso a fuentes de datos institucionales.',
        format: 'Aceptamos: reportes de errores, identificación de leyes faltantes, validación de categorización, y conexiones con instituciones que custodian datos legislativos.',
        contact: 'admin@madfam.io — Asunto: Colaboración Profesional-Tezca',
      },
    ],
    commitment: {
      title: 'Nuestro compromiso',
      items: [
        'Todo dato contribuido se publica bajo dominio público, accesible para todos.',
        'Atribución completa a la institución contribuyente en nuestras fuentes de datos.',
        'Código fuente abierto (AGPL-3.0) — cualquiera puede auditar cómo procesamos la información.',
        'Sin fines de lucro en el acceso a datos legislativos — siempre gratuito para consulta pública.',
        'Reportes periódicos de impacto: cuántos usuarios acceden a los datos contribuidos.',
      ],
    },
    cta: {
      text: '¿Representas a una de estas instituciones?',
      sub: 'Escríbenos para explorar una colaboración.',
      email: 'admin@madfam.io',
      contribute: 'O contribuye directamente',
      contributeLink: '/contribuir',
    },
  },
  en: {
    back: 'Back to home',
    hero: {
      title: 'Institutional Partnership',
      subtitle: 'Let\'s work together to make Mexico\'s entire legal framework accessible',
    },
    intro: 'Tezca is public digital infrastructure under the AGPL-3.0 license. Our mission is to capture the entirety of Mexico\'s legal framework and make it accessible programmatically, reliably, and free of charge. To achieve this, we need collaboration from institutions that hold essential legislative data.',
    sections: [
      {
        id: 'scjn',
        icon: 'scale',
        title: 'Supreme Court of Justice (SCJN)',
        what: 'We request access to the complete corpus of case law and isolated theses from the Semanario Judicial de la Federación — approximately 500,000 records from the 10th and 11th Epochs.',
        why: 'Case law defines how laws are interpreted in practice. Without access to these precedents, citizens and attorneys operate with incomplete information. Digitizing this corpus would enable full-text search, jurisprudential trend analysis, and automatic linking with corresponding legislation.',
        format: 'Preferred format: bulk JSON or CSV with fields: registro, época, instancia, materia, tipo, rubro, texto, precedentes, votos, ponente, fuente.',
        contact: 'admin@madfam.io — Subject: SCJN-Tezca Collaboration',
      },
      {
        id: 'state',
        icon: 'landmark',
        title: 'State Congresses and Governments',
        what: 'We\'ve identified significant gaps in non-legislative law (regulations, executive decrees, judicial agreements) from Michoacán (~2,291 missing documents), San Luis Potosí (~700), Estado de México (~600), Mexico City, and Zacatecas.',
        why: 'The National Legal Order lists these states with zero or very few non-legislative documents, despite each state producing hundreds of regulations and agreements. Complete state regulations are necessary for citizens and businesses to understand their regulatory obligations.',
        format: 'We accept digitized official gazettes, regulation catalogs in any format (PDF, HTML, databases), or access to transparency portals with legislative documents.',
        contact: 'admin@madfam.io — Subject: State-Tezca Collaboration',
      },
      {
        id: 'municipal',
        icon: 'building',
        title: 'Municipal Governments',
        what: 'Mexico has 2,468 municipalities. We currently cover only 6. The General Transparency Law requires municipalities to publish their regulatory framework, but many transparency portals are inaccessible or incomplete.',
        why: 'Municipal regulations directly affect daily life: land use, commerce, public services, safety. Without access to these regulations, entrepreneurs and citizens cannot know the rules that govern them locally.',
        format: 'Preferred format: municipal statutes, regulations, codes, and guidelines in PDF or digital format. We also accept catalogs or inventories of current regulations.',
        contact: 'admin@madfam.io — Subject: Municipal-Tezca Collaboration',
      },
      {
        id: 'universities',
        icon: 'graduation',
        title: 'Universities and Research Centers',
        what: 'We seek research collaborations for data validation, coverage analysis, and development of natural language processing tools applied to Mexican law.',
        why: 'Tezca offers a unique dataset for computational legal research: 35,000+ structured laws, 3.5 million indexed articles, and cross-reference metadata. Collaborating with universities improves data quality and generates academic knowledge.',
        format: 'Interested in: thesis projects, joint research, legal text parsing validation, coverage analysis by jurisdiction, and development of legal NLP models.',
        contact: 'admin@madfam.io — Subject: Academic-Tezca Collaboration',
      },
      {
        id: 'bar',
        icon: 'globe',
        title: 'Bar Associations',
        what: 'We invite legal professionals to validate our data quality, identify missing laws in their areas of expertise, and contribute their experience in categorizing and structuring legislation.',
        why: 'Attorneys are the most demanding users of legislative information. Their feedback is invaluable to ensure Tezca faithfully reflects the current state of the legal framework. Additionally, their professional networks can facilitate access to institutional data sources.',
        format: 'We accept: error reports, identification of missing laws, categorization validation, and connections with institutions that hold legislative data.',
        contact: 'admin@madfam.io — Subject: Professional-Tezca Collaboration',
      },
    ],
    commitment: {
      title: 'Our commitment',
      items: [
        'All contributed data is published in the public domain, accessible to all.',
        'Full attribution to the contributing institution in our data sources.',
        'Open source code (AGPL-3.0) — anyone can audit how we process information.',
        'No profit motive in legislative data access — always free for public consultation.',
        'Periodic impact reports: how many users access contributed data.',
      ],
    },
    cta: {
      text: 'Do you represent one of these institutions?',
      sub: 'Write to us to explore a collaboration.',
      email: 'admin@madfam.io',
      contribute: 'Or contribute directly',
      contributeLink: '/contribuir',
    },
  },
  nah: {
    back: 'Xicmocuepa caltenco',
    hero: {
      title: 'Tēnōnōtzaliztli',
      subtitle: 'Ma ticchihuacān ic mochi mēxihcatl tenahuatilli monextia',
    },
    intro: 'Tezca cē tēpōzmachiyōtl āltepēyōtl AGPL-3.0. Totēquitl quipiya mochi in mēxihcatl tenahuatilli ihuan quichihua huelīz motēmoa. Ic inīn, monequi tēpalēhuiliztli in tēyācanaliztli tlamachilizpialōyan.',
    sections: [
      {
        id: 'scjn',
        icon: 'scale',
        title: 'SCJN — Suprema Corte',
        what: 'Ticnequi mochi jurisprudencia ihuan tesis aisladas — 500,000 tlapohualli.',
        why: 'In jurisprudencia quināmiqui quēnin in tenahuatilli motēixīmati.',
        format: 'JSON ahnōzo CSV ica mochi tlamachiliztli.',
        contact: 'admin@madfam.io',
      },
      {
        id: 'state',
        icon: 'landmark',
        title: 'Altepetl Tēyācanaliztli',
        what: 'Michoacán, San Luis Potosí, Estado de México, CDMX, Zacatecas — mīlah tenahuatilli pōlihua.',
        why: 'Mochi altepetl quichihua reglamentos ihuan acuerdos.',
        format: 'PDF, HTML, āmoxcalli — mochi aceptamos.',
        contact: 'admin@madfam.io',
      },
      {
        id: 'municipal',
        icon: 'building',
        title: 'Calpulli Tēyācanaliztli',
        what: '2,468 calpulli ipan Mēxihco. Zan 6 mopiya.',
        why: 'Calpulli tenahuatilli quiīxnāmiqui mochi yōliliztli.',
        format: 'Bandos, reglamentos, códigos — PDF ahnōzo digital.',
        contact: 'admin@madfam.io',
      },
      {
        id: 'universities',
        icon: 'graduation',
        title: 'Tlamachtiloyan',
        what: 'Tictēmoa tlapalēhuiliztli ic tlamachiliztli ihuan NLP tenahuatilli.',
        why: 'Tezca quipiya 35,000+ tenahuatilli ihuan 3.5 millones tlanahuatilli.',
        format: 'Tesis, investigación, validación.',
        contact: 'admin@madfam.io',
      },
      {
        id: 'bar',
        icon: 'globe',
        title: 'Abogados Tēnōnōtzaliztli',
        what: 'Xicpalēhuicān ic tlamachiliztli cualli ihuan tenahuatilli pōlihua.',
        why: 'Abogados quimati nelli in tenahuatilli.',
        format: 'Tlahtlacōlli, tenahuatilli pōlihua, categorización.',
        contact: 'admin@madfam.io',
      },
    ],
    commitment: {
      title: 'Totēnēhual',
      items: [
        'Mochi tlamachiliztli āltepēyōtl, mochi huelīz quipiya.',
        'Atribución mochi tēpalēhuiani tēyācanaliztli.',
        'Código abierto AGPL-3.0.',
        'Ahmo tlaxtlahualli ic tenahuatilli.',
        'Reportes ic cuezqui motēquitiltia.',
      ],
    },
    cta: {
      text: 'Titēīxnāmiqui cē inīn tēyācanaliztli?',
      sub: 'Xitēchtlahcuilhui.',
      email: 'admin@madfam.io',
      contribute: 'Ahnōzo xicpalēhui',
      contributeLink: '/contribuir',
    },
  },
};

const iconMap: Record<string, React.ElementType> = {
  scale: Scale,
  landmark: Landmark,
  building: Building2,
  graduation: GraduationCap,
  globe: Globe,
};

export default async function ConvocatoriaPage({
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
          <Landmark className="mx-auto h-12 w-12 text-primary-200 mb-4" aria-hidden="true" />
          <h1 className="font-display text-4xl sm:text-6xl font-bold tracking-tight text-white">
            {t.hero.title}
          </h1>
          <p className="mt-4 font-serif text-lg sm:text-xl text-primary-200 italic">
            {t.hero.subtitle}
          </p>
        </div>
      </section>

      {/* Nav */}
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

      {/* Content */}
      <div className="container mx-auto px-4 sm:px-6 pb-16 sm:pb-24 max-w-4xl">
        {/* Intro */}
        <p className="font-serif text-base sm:text-lg leading-relaxed text-muted-foreground mb-12">
          {t.intro}
        </p>

        {/* Partnership sections */}
        <div className="space-y-8">
          {t.sections.map((section) => {
            const Icon = iconMap[section.icon] || Landmark;
            return (
              <Card key={section.id}>
                <CardContent className="p-6 sm:p-8">
                  <div className="flex items-start gap-4">
                    <div className="shrink-0 mt-1">
                      <Icon className="h-6 w-6 text-primary" aria-hidden="true" />
                    </div>
                    <div className="space-y-3">
                      <h2 className="font-serif text-xl sm:text-2xl font-semibold text-foreground">
                        {section.title}
                      </h2>
                      <div className="space-y-2 text-sm text-muted-foreground leading-relaxed">
                        <p><span className="font-semibold text-foreground">{lang === 'en' ? 'What we need:' : lang === 'nah' ? 'Tlein monequi:' : 'Qué necesitamos:'}</span> {section.what}</p>
                        <p><span className="font-semibold text-foreground">{lang === 'en' ? 'Why it matters:' : lang === 'nah' ? 'Tlēica:' : 'Por qué importa:'}</span> {section.why}</p>
                        <p><span className="font-semibold text-foreground">{lang === 'en' ? 'Format:' : lang === 'nah' ? 'Tlamantli:' : 'Formato:'}</span> {section.format}</p>
                      </div>
                      <p className="text-xs text-muted-foreground">
                        <a href={`mailto:${section.contact.split(' — ')[0]}`} className="text-primary hover:underline">
                          {section.contact}
                        </a>
                      </p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>

        {/* Commitment */}
        <section className="mt-12 space-y-4">
          <h2 className="font-serif text-xl sm:text-2xl font-semibold tracking-tight text-foreground">
            {t.commitment.title}
          </h2>
          <ul className="space-y-2">
            {t.commitment.items.map((item, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-muted-foreground">
                <span className="text-primary mt-0.5 shrink-0">•</span>
                {item}
              </li>
            ))}
          </ul>
        </section>

        {/* CTA */}
        <div className="mt-16 text-center border-t border-border pt-12">
          <p className="font-serif text-xl sm:text-2xl font-semibold text-foreground">
            {t.cta.text}
          </p>
          <p className="mt-2 text-muted-foreground">
            {t.cta.sub}
          </p>
          <div className="mt-6 flex flex-wrap justify-center gap-3">
            <a
              href={`mailto:${t.cta.email}`}
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-md bg-primary text-primary-foreground text-sm font-medium hover:bg-primary/90 transition-colors"
            >
              {t.cta.email}
            </a>
            <Link
              href={t.cta.contributeLink}
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-md border border-border text-sm font-medium hover:bg-muted transition-colors"
            >
              {t.cta.contribute}
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
