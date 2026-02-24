import Link from 'next/link';
import { ArrowLeft, Scale } from 'lucide-react';
import { LanguageToggle } from '@/components/LanguageToggle';
import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Términos y Condiciones — Tezca',
  description: 'Términos y condiciones de uso de Tezca, plataforma de legislación mexicana digitalizada.',
};

const content = {
  es: {
    back: 'Volver al inicio',
    title: 'Términos y Condiciones',
    lastUpdated: 'Última actualización: 6 de febrero de 2026',
    sections: [
      {
        title: '1. Naturaleza del Servicio',
        body: 'Tezca es un proyecto informativo independiente que presenta legislación mexicana en formato digital. El contenido se proporciona "tal cual" (as is), sin garantías de ningún tipo, ya sean expresas o implícitas. No garantizamos la exactitud, integridad, actualidad o idoneidad del contenido para ningún propósito particular.',
      },
      {
        title: '2. No es Fuente Oficial',
        body: 'Este sitio no es una fuente oficial del gobierno mexicano. La legislación aquí presentada se obtiene de fuentes públicas como el Diario Oficial de la Federación (DOF) y el Orden Jurídico Nacional (OJN), pero puede contener errores de procesamiento, omisiones o desactualizaciones. Para efectos legales, siempre debe consultarse la publicación oficial correspondiente en el DOF o las gacetas oficiales estatales.',
      },
      {
        title: '3. No Constituye Asesoría Legal',
        body: 'La información presentada en este sitio no constituye asesoría legal, opinión jurídica ni recomendación profesional de ningún tipo. Para cualquier asunto que requiera orientación legal, consulte a un abogado o profesional del derecho debidamente acreditado. No se debe tomar ninguna acción basándose exclusivamente en la información de este sitio.',
      },
      {
        title: '4. Sin Obligación Legal Vinculante',
        body: 'El uso de este sitio no crea ninguna relación profesional, contractual ni de asesoría entre el usuario y los responsables de la plataforma. El acceso y uso del contenido es bajo el propio riesgo del usuario. Los responsables del sitio no asumen ninguna obligación legal vinculante derivada del uso de la plataforma.',
      },
      {
        title: '5. Propiedad Intelectual',
        body: 'Las leyes y textos legislativos son de dominio público conforme al artículo 14 de la Ley Federal del Derecho de Autor. Sin embargo, la selección, disposición, presentación visual, código fuente, algoritmos de procesamiento y diseño de la plataforma son propiedad de sus autores y están protegidos por las leyes de propiedad intelectual aplicables.',
      },
      {
        title: '6. Limitación de Responsabilidad',
        body: 'En ningún caso los responsables de Tezca serán responsables por daños directos, indirectos, incidentales, especiales o consecuentes que resulten del uso o la imposibilidad de uso de este sitio, incluyendo pero no limitado a: errores u omisiones en el contenido, interrupciones del servicio, decisiones tomadas con base en la información presentada, o pérdidas de cualquier naturaleza.',
      },
      {
        title: '7. Uso Aceptable',
        body: 'El usuario se compromete a utilizar este sitio de manera responsable. Queda prohibido: (a) la extracción masiva automatizada (scraping) con fines comerciales sin autorización; (b) la presentación del contenido como fuente oficial del gobierno; (c) la redistribución del contenido procesado con fines de lucro sin atribución; (d) cualquier uso que interfiera con el funcionamiento normal del servicio.',
      },
      {
        title: '8. Disponibilidad del Servicio',
        body: 'El servicio se ofrece sobre la base de "mejor esfuerzo". No se garantiza la disponibilidad continua, ininterrumpida ni libre de errores del sitio. El servicio puede suspenderse temporal o permanentemente sin previo aviso para mantenimiento, actualizaciones o por cualquier otra razón.',
      },
      {
        title: '9. Legislación Aplicable',
        body: 'Estos términos se rigen por las leyes de los Estados Unidos Mexicanos. Para cualquier controversia derivada del uso de este sitio, las partes se someten a la jurisdicción de los tribunales competentes de la Ciudad de México, renunciando a cualquier otro fuero que pudiera corresponderles.',
      },
      {
        title: '10. Modificaciones y Contacto',
        body: 'Nos reservamos el derecho de modificar estos términos en cualquier momento. Las modificaciones entrarán en vigor desde su publicación en este sitio. El uso continuado del servicio después de cualquier modificación constituye la aceptación de los nuevos términos. Para consultas relacionadas con estos términos, puede contactarnos en: admin@madfam.io',
      },
    ],
  },
  en: {
    back: 'Back to home',
    title: 'Terms and Conditions',
    lastUpdated: 'Last updated: February 6, 2026',
    sections: [
      {
        title: '1. Nature of Service',
        body: 'Tezca is an independent informational project that presents Mexican legislation in digital format. The content is provided "as is", without warranties of any kind, either express or implied. We do not guarantee the accuracy, completeness, timeliness, or suitability of the content for any particular purpose.',
      },
      {
        title: '2. Not an Official Source',
        body: 'This site is not an official source of the Mexican government. The legislation presented here is obtained from public sources such as the Diario Oficial de la Federación (DOF) and the Orden Jurídico Nacional (OJN), but may contain processing errors, omissions, or outdated information. For legal purposes, you should always consult the corresponding official publication in the DOF or state official gazettes.',
      },
      {
        title: '3. Not Legal Advice',
        body: 'The information presented on this site does not constitute legal advice, legal opinion, or professional recommendation of any kind. For any matter requiring legal guidance, consult a duly accredited lawyer or legal professional. No action should be taken based solely on the information on this site.',
      },
      {
        title: '4. No Binding Legal Obligation',
        body: 'Use of this site does not create any professional, contractual, or advisory relationship between the user and the platform operators. Access to and use of the content is at the user\'s own risk. The site operators assume no binding legal obligation arising from the use of the platform.',
      },
      {
        title: '5. Intellectual Property',
        body: 'The laws and legislative texts are in the public domain pursuant to Article 14 of the Mexican Federal Copyright Law. However, the selection, arrangement, visual presentation, source code, processing algorithms, and platform design are the property of their authors and are protected by applicable intellectual property laws.',
      },
      {
        title: '6. Limitation of Liability',
        body: 'In no event shall the operators of Tezca be liable for any direct, indirect, incidental, special, or consequential damages resulting from the use or inability to use this site, including but not limited to: errors or omissions in content, service interruptions, decisions made based on the information presented, or losses of any nature.',
      },
      {
        title: '7. Acceptable Use',
        body: 'Users agree to use this site responsibly. The following are prohibited: (a) automated mass extraction (scraping) for commercial purposes without authorization; (b) presenting the content as an official government source; (c) redistribution of processed content for profit without attribution; (d) any use that interferes with the normal operation of the service.',
      },
      {
        title: '8. Service Availability',
        body: 'The service is provided on a "best effort" basis. We do not guarantee continuous, uninterrupted, or error-free availability of the site. The service may be suspended temporarily or permanently without prior notice for maintenance, updates, or any other reason.',
      },
      {
        title: '9. Governing Law',
        body: 'These terms are governed by the laws of the United Mexican States. For any dispute arising from the use of this site, the parties submit to the jurisdiction of the competent courts of Mexico City, waiving any other jurisdiction that may apply.',
      },
      {
        title: '10. Modifications and Contact',
        body: 'We reserve the right to modify these terms at any time. Modifications take effect upon publication on this site. Continued use of the service after any modification constitutes acceptance of the new terms. For inquiries related to these terms, you may contact us at: admin@madfam.io',
      },
    ],
  },
  nah: {
    back: 'Xicmocuepa caltenco',
    title: 'Tlanahuatilli ihuan Tlahtōltzin',
    lastUpdated: 'Tlāmian yancuīliztli: 6 de febrero de 2026',
    sections: [
      {
        title: '1. Tequitl Tlamantli',
        body: 'Tezca cē tlamachiliztli tēpōzmachiyōtl ic mēxihcatl tenahuatilli tēpōzmachiyōtīlpan. In tlamachiliztli "quēmeh yez" (as is), ahtlē tlaneltilīliztli. Ahmo ticneltilia in nelli, mochi, āxcān ahnōzo cualli ic itlah.',
      },
      {
        title: '2. Ahmo Tēuctlahtōlpialōyan',
        body: 'Inīn tlahcuilōlpan ahmo tēuctlahtōlpialōyan in mēxihcatl tēuctlahtoāni. In tenahuatilli monextia ipan DOF ihuan OJN, macihuī huelīz quipiya tlahtlacōlli. Ic tenahuatiliz, nochipa xiquitta tēuctlahtōlpialōyan.',
      },
      {
        title: '3. Ahmo Tlanōnōtzaliztli',
        body: 'In tlamachiliztli ahmo tlanōnōtzaliztli, ahmo tenahuatiliz tlanēmilīlli. Ic itlah monequi tenahuatiliz, xictlatlanili cē tenahuatilizmatini.',
      },
      {
        title: '4. Ahtlē Tenahuatiliz Tlanāhuatilli',
        body: 'In tictēquitiltia ahmo quichihua tlanōnōtzaliztli tetlahtōlpialōyan ihuan Tezca. In tictēquitiltia tetlahtōlpialōyan ītechcopa.',
      },
      {
        title: '5. Tlaixiptlaliztli Tenahuatilli',
        body: 'In tenahuatilli āltepēyōtl āmatl quēmeh artículo 14 LFDA. Macihuī, in tlaixiptlaliztli, tlahcuilōlli, tēpōzmachiyōtl ihuan tlachihualiztli intēch in tlachihuanih.',
      },
      {
        title: '6. Ahmo Tlanāhuatilli Tēchcopa',
        body: 'Ahmo quēmān Tezca quināhuatia tlaxtlahualiztli ic tlahtlacōlli, ahmo tictēquitiltia ahnōzo itlah ahmo cualli.',
      },
      {
        title: '7. Cualli Tēquitiliztli',
        body: 'In tetlahtōlpialōyan monāhuatia cualli tēquitiliztli. Ahmo huelīz: (a) mīlah tlatemoliztli tlanāmacaliztli; (b) monextia quēmeh tēuctlahtōlpialōyan; (c) tlanāmacaliztli ahtlē tōcāitl; (d) itlah ahmo cualli tēquitiliztli.',
      },
      {
        title: '8. Tēquitiliztli Monextia',
        body: 'In tēquitiliztli "tlanēmilīlli cualli". Ahmo ticneltilia nochipa, ahmo tlanquiliztli, ahmo ahtlē tlahtlacōlli.',
      },
      {
        title: '9. Tenahuatilli Mochihua',
        body: 'Inīn tlanahuatilli mochihua ic tenahuatilli mēxihcatl. Ic mochi tlahtōlli, tetlahtōlpialōyan monāhuatia México Āltepētl.',
      },
      {
        title: '10. Tlapatiliztli ihuan Tlanōnōtzaliztli',
        body: 'Huelīz ticpātia inīn tlanahuatilli. In tlapatiliztli mochihua ihcuāc monextia. Ic tlatlanīliztli: admin@madfam.io',
      },
    ],
  },
};

function LegalSection({ title, body }: { title: string; body: string }) {
  return (
    <section className="space-y-3">
      <h2 className="text-lg font-semibold text-foreground">{title}</h2>
      <p className="text-sm sm:text-base leading-relaxed text-muted-foreground">{body}</p>
    </section>
  );
}

export default async function TerminosPage({
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
            <Scale className="h-7 w-7 text-primary-600" />
            <h1 className="text-2xl sm:text-3xl font-bold tracking-tight">{t.title}</h1>
          </div>
          <p className="text-sm text-muted-foreground">{t.lastUpdated}</p>
        </div>

        {/* Sections */}
        <div className="space-y-8">
          {t.sections.map((section) => (
            <LegalSection key={section.title} title={section.title} body={section.body} />
          ))}
        </div>
      </div>
    </div>
  );
}
