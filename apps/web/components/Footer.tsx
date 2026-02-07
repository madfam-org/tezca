'use client';

import Link from 'next/link';
import { ExternalLink, Scale } from 'lucide-react';
import { useLang } from '@/components/providers/LanguageContext';
import { LanguageToggle } from '@/components/LanguageToggle';

const content = {
  es: {
    disclaimer:
      'Este sitio es un proyecto informativo independiente. No es una fuente oficial del gobierno mexicano.',
    dofLink: 'Consulta el Diario Oficial de la Federación para textos oficiales.',
    explore: 'Explorar',
    home: 'Inicio',
    search: 'Buscar Leyes',
    catalog: 'Catálogo',
    legal: 'Legal',
    terms: 'Términos y Condiciones',
    notice: 'Aviso Legal',
    privacy: 'Privacidad',
    sources: 'Fuentes Oficiales',
    about: 'Acerca de',
    tagline: 'El Espejo de la Ley',
    copyright: `© ${new Date().getFullYear()} Innovaciones MADFAM SAS de CV. Todos los derechos reservados.`,
    ip: 'Las leyes son de dominio público. La presentación y código de esta plataforma son propiedad de sus autores.',
  },
  en: {
    disclaimer:
      'This site is an independent informational project. It is not an official Mexican government source.',
    dofLink: 'Consult the Diario Oficial de la Federación for official texts.',
    explore: 'Explore',
    home: 'Home',
    search: 'Search Laws',
    catalog: 'Catalog',
    legal: 'Legal',
    terms: 'Terms and Conditions',
    notice: 'Legal Notice',
    privacy: 'Privacy Policy',
    sources: 'Official Sources',
    about: 'About',
    tagline: 'The Mirror of the Law',
    copyright: `© ${new Date().getFullYear()} Innovaciones MADFAM SAS de CV. All rights reserved.`,
    ip: 'The laws are in the public domain. The presentation and code of this platform are the property of their authors.',
  },
  nah: {
    disclaimer:
      'Inīn tlahcuilōlpan ahmo tēuctlahcuilōlli in mēxihcatl tēuctlahtoāni. Zan tēmachtilistli.',
    dofLink: 'Xiquitta in Diario Oficial de la Federación ic tēuctlahcuilōlli.',
    explore: 'Tlaixmatiliztli',
    home: 'Caltenco',
    search: 'Xictlatemo Tenahuatilli',
    catalog: 'Amatlapalōlli',
    legal: 'Tenahuatilizpan',
    terms: 'Tlanahuatilli ihuan Tlahtōltzin',
    notice: 'Tenahuatilizpan Tlanahuatilli',
    privacy: 'Ichtacayōtl',
    sources: 'Tlahtōlpialōyan',
    about: 'Tlen Tezca',
    tagline: 'In Tezcatl in Tenahuatilli',
    copyright: `© ${new Date().getFullYear()} Innovaciones MADFAM SAS de CV. Mochi tlanahuatilli motlapiā.`,
    ip: 'In tenahuatilli mochi tlācameh impan. In tlaixiptlaliztli ihuan tlahcuilōlli intēch in tlachihuanih.',
  },
};

export function Footer() {
  const { lang } = useLang();
  const t = content[lang];

  return (
    <footer className="mt-auto border-t border-border bg-card text-card-foreground">
      {/* Disclaimer bar */}
      <div className="bg-warning-50 dark:bg-warning-700/15 border-b border-warning-500/20">
        <div className="container mx-auto px-4 sm:px-6 py-3 flex flex-col sm:flex-row items-start sm:items-center gap-2 text-xs sm:text-sm text-warning-700 dark:text-warning-500">
          <Scale aria-hidden="true" className="h-4 w-4 flex-shrink-0 mt-0.5 sm:mt-0" />
          <p>
            {t.disclaimer}{' '}
            <a
              href="https://www.dof.gob.mx"
              target="_blank"
              rel="noopener noreferrer"
              className="underline underline-offset-2 hover:text-warning-700 dark:hover:text-warning-500 inline-flex items-center gap-1"
            >
              {t.dofLink}
              <ExternalLink className="h-3 w-3" />
            </a>
          </p>
        </div>
      </div>

      {/* Main footer grid */}
      <div className="container mx-auto px-4 sm:px-6 py-10 sm:py-12">
        <div className="grid grid-cols-2 gap-8 sm:grid-cols-4">
          {/* Brand */}
          <div className="col-span-2 sm:col-span-1">
            <Link href="/" className="text-lg font-bold tracking-tight">
              Tezca
            </Link>
            <p className="mt-2 text-sm text-muted-foreground">{t.tagline}</p>
          </div>

          {/* Explore */}
          <div>
            <h3 className="text-sm font-semibold tracking-wide uppercase text-muted-foreground">
              {t.explore}
            </h3>
            <ul className="mt-3 space-y-2">
              <li>
                <Link href="/" className="text-sm text-foreground/80 hover:text-foreground transition-colors">
                  {t.home}
                </Link>
              </li>
              <li>
                <Link href="/busqueda" className="text-sm text-foreground/80 hover:text-foreground transition-colors">
                  {t.search}
                </Link>
              </li>
              <li>
                <Link href="/leyes" className="text-sm text-foreground/80 hover:text-foreground transition-colors">
                  {t.catalog}
                </Link>
              </li>
              <li>
                <Link href="/acerca-de" className="text-sm text-foreground/80 hover:text-foreground transition-colors">
                  {t.about}
                </Link>
              </li>
            </ul>
          </div>

          {/* Legal */}
          <div>
            <h3 className="text-sm font-semibold tracking-wide uppercase text-muted-foreground">
              {t.legal}
            </h3>
            <ul className="mt-3 space-y-2">
              <li>
                <Link href="/terminos" className="text-sm text-foreground/80 hover:text-foreground transition-colors">
                  {t.terms}
                </Link>
              </li>
              <li>
                <Link href="/aviso-legal" className="text-sm text-foreground/80 hover:text-foreground transition-colors">
                  {t.notice}
                </Link>
              </li>
              <li>
                <Link href="/privacidad" className="text-sm text-foreground/80 hover:text-foreground transition-colors">
                  {t.privacy}
                </Link>
              </li>
            </ul>
          </div>

          {/* Official Sources */}
          <div>
            <h3 className="text-sm font-semibold tracking-wide uppercase text-muted-foreground">
              {t.sources}
            </h3>
            <ul className="mt-3 space-y-2">
              <li>
                <a
                  href="https://www.dof.gob.mx"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-sm text-foreground/80 hover:text-foreground transition-colors inline-flex items-center gap-1"
                >
                  Diario Oficial (DOF)
                  <ExternalLink className="h-3 w-3" />
                </a>
              </li>
              <li>
                <a
                  href="https://www.ordenjuridico.gob.mx"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-sm text-foreground/80 hover:text-foreground transition-colors inline-flex items-center gap-1"
                >
                  Orden Jurídico (OJN)
                  <ExternalLink className="h-3 w-3" />
                </a>
              </li>
            </ul>
          </div>
        </div>
      </div>

      {/* Bottom bar */}
      <div className="border-t border-border">
        <div className="container mx-auto px-4 sm:px-6 py-4 flex flex-col sm:flex-row items-center justify-between gap-3 text-xs text-muted-foreground">
          <div className="text-center sm:text-left">
            <p>{t.copyright}</p>
            <p className="mt-1">{t.ip}</p>
          </div>
          <LanguageToggle />
        </div>
      </div>
    </footer>
  );
}
