import Link from 'next/link';
import { ArrowLeft, Code2, Key, Terminal, BookOpen, Zap } from 'lucide-react';
import { Card, CardContent } from '@tezca/ui';
import { LanguageToggle } from '@/components/LanguageToggle';
import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Desarrolladores — Tezca API',
  description: 'Documentación para desarrolladores de la API de Tezca. Accede al universo legal mexicano de forma programática.',
};

const content = {
  es: {
    back: 'Volver al inicio',
    hero: {
      title: 'API de Tezca',
      subtitle: 'El sistema legal mexicano, accesible por código',
    },
    overview: {
      title: 'Descripción General',
      body: 'La API REST de Tezca ofrece acceso programático a más de 35,000 leyes y 3.5 millones de artículos del universo legal mexicano. Cubre legislación federal, estatal y municipal, incluyendo leyes, códigos, reglamentos, NOMs, tratados y jurisprudencia.',
      features: [
        { label: 'Búsqueda de texto completo', desc: 'Elasticsearch con análisis legal en español, sinónimos jurídicos y normalización de acentos.' },
        { label: 'Filtrado por jurisdicción', desc: 'Federal, estatal (32 estados) y municipal. Filtra por categoría, estatus, tipo y rango de fechas.' },
        { label: 'Exportación multiformato', desc: 'PDF, TXT, LaTeX, DOCX, EPUB y JSON para cualquier ley del corpus.' },
        { label: 'Cobertura nacional', desc: 'Datos del DOF, OJN, gacetas estatales, portales municipales, NOMs, tratados y SCJN.' },
      ],
    },
    auth: {
      title: 'Autenticación',
      body: 'La API soporta tres modos de acceso:',
      methods: [
        {
          name: 'Clave API (recomendado)',
          desc: 'Envía el header X-API-Key con tu clave (prefijo tzk_). Obtén tu clave en tu perfil de usuario.',
          example: 'curl -H "X-API-Key: tzk_tu_clave_aqui" https://api.tezca.mx/api/v1/laws/',
        },
        {
          name: 'JWT (Janua)',
          desc: 'Token Bearer para sesiones autenticadas desde la web. Se obtiene al iniciar sesión.',
          example: 'curl -H "Authorization: Bearer eyJ..." https://api.tezca.mx/api/v1/laws/',
        },
        {
          name: 'Acceso anónimo',
          desc: 'Sin autenticación. Limitado a 10 peticiones/minuto y 100/hora.',
          example: 'curl https://api.tezca.mx/api/v1/search/?q=amparo',
        },
      ],
    },
    tiers: {
      title: 'Niveles de Acceso',
      rows: [
        { tier: 'Anónimo', perMin: '10', perHour: '100', exports: 'TXT' },
        { tier: 'Community', perMin: '1,000', perHour: '100,000', exports: 'TXT, PDF, JSON' },
        { tier: 'Essentials', perMin: '30', perHour: '500', exports: 'TXT, PDF, JSON' },
        { tier: 'Academic', perMin: '60', perHour: '2,000', exports: '+ LaTeX' },
        { tier: 'Institutional', perMin: '200', perHour: '50,000', exports: 'Todos' },
      ],
      headers: ['Nivel', 'Por minuto', 'Por hora', 'Exportación'],
    },
    endpoints: {
      title: 'Endpoints Principales',
      items: [
        { method: 'GET', path: '/api/v1/search/', desc: 'Búsqueda de texto completo con filtros y facetas.' },
        { method: 'GET', path: '/api/v1/laws/', desc: 'Listado de leyes con paginación y filtrado.' },
        { method: 'GET', path: '/api/v1/laws/{id}/', desc: 'Detalle de una ley con artículos y metadatos.' },
        { method: 'GET', path: '/api/v1/laws/{id}/articles/', desc: 'Artículos individuales de una ley.' },
        { method: 'GET', path: '/api/v1/categories/', desc: 'Categorías del corpus legal.' },
        { method: 'GET', path: '/api/v1/coverage/', desc: 'Estadísticas de cobertura del universo legal.' },
        { method: 'GET', path: '/api/v1/judicial/', desc: 'Registros judiciales (jurisprudencia y tesis).' },
        { method: 'GET', path: '/api/v1/export/{id}/{format}/', desc: 'Exportar ley en PDF, TXT, LaTeX, DOCX, EPUB o JSON.' },
        { method: 'GET', path: '/api/v1/schema/', desc: 'Especificación OpenAPI (Swagger).' },
      ],
    },
    quickstart: {
      title: 'Inicio Rápido',
      examples: [
        {
          lang: 'curl',
          label: 'curl',
          code: `# Buscar artículos sobre amparo
curl "https://api.tezca.mx/api/v1/search/?q=amparo&jurisdiction=federal"

# Obtener una ley específica
curl "https://api.tezca.mx/api/v1/laws/fed_ley_amparo/"

# Exportar como PDF
curl -H "X-API-Key: tzk_tu_clave" \\
  "https://api.tezca.mx/api/v1/export/fed_ley_amparo/pdf/" -o amparo.pdf`,
        },
        {
          lang: 'python',
          label: 'Python',
          code: `import requests

API = "https://api.tezca.mx/api/v1"
headers = {"X-API-Key": "tzk_tu_clave"}

# Buscar artículos
resp = requests.get(f"{API}/search/", params={"q": "amparo"}, headers=headers)
data = resp.json()
print(f"{data['total']} resultados encontrados")

for result in data["results"][:5]:
    print(f"  {result['law_name']} - Art. {result['article']}")`,
        },
        {
          lang: 'javascript',
          label: 'JavaScript',
          code: `const API = "https://api.tezca.mx/api/v1";
const headers = { "X-API-Key": "tzk_tu_clave" };

// Buscar artículos
const resp = await fetch(\`\${API}/search/?q=amparo\`, { headers });
const data = await resp.json();
console.log(\`\${data.total} resultados encontrados\`);

data.results.slice(0, 5).forEach(r =>
  console.log(\`  \${r.law_name} - Art. \${r.article}\`)
);`,
        },
      ],
    },
    openapi: {
      title: 'Especificación OpenAPI',
      body: 'La documentación interactiva completa está disponible en:',
      url: 'https://api.tezca.mx/api/v1/schema/',
    },
    contact: {
      title: 'Soporte',
      body: 'Para dudas técnicas, reportes de errores o solicitudes de acceso enterprise:',
      email: 'admin@madfam.io',
    },
    copyrightPre: '© 2026 Innovaciones ',
    copyrightPost: ' SAS de CV. Licencia AGPL-3.0.',
  },
  en: {
    back: 'Back to home',
    hero: {
      title: 'Tezca API',
      subtitle: 'The Mexican legal system, accessible by code',
    },
    overview: {
      title: 'Overview',
      body: 'The Tezca REST API provides programmatic access to over 35,000 laws and 3.5 million articles of the Mexican legal universe. It covers federal, state, and municipal legislation including laws, codes, regulations, NOMs, treaties, and judicial records.',
      features: [
        { label: 'Full-text search', desc: 'Elasticsearch with Spanish legal analysis, legal synonyms, and accent normalization.' },
        { label: 'Jurisdiction filtering', desc: 'Federal, state (32 states), and municipal. Filter by category, status, type, and date range.' },
        { label: 'Multi-format export', desc: 'PDF, TXT, LaTeX, DOCX, EPUB, and JSON for any law in the corpus.' },
        { label: 'National coverage', desc: 'Data from DOF, OJN, state gazettes, municipal portals, NOMs, treaties, and SCJN.' },
      ],
    },
    auth: {
      title: 'Authentication',
      body: 'The API supports three access modes:',
      methods: [
        {
          name: 'API Key (recommended)',
          desc: 'Send the X-API-Key header with your key (tzk_ prefix). Get your key from your user profile.',
          example: 'curl -H "X-API-Key: tzk_your_key_here" https://api.tezca.mx/api/v1/laws/',
        },
        {
          name: 'JWT (Janua)',
          desc: 'Bearer token for authenticated web sessions. Obtained upon login.',
          example: 'curl -H "Authorization: Bearer eyJ..." https://api.tezca.mx/api/v1/laws/',
        },
        {
          name: 'Anonymous access',
          desc: 'No authentication required. Limited to 10 requests/minute and 100/hour.',
          example: 'curl https://api.tezca.mx/api/v1/search/?q=amparo',
        },
      ],
    },
    tiers: {
      title: 'Access Tiers',
      rows: [
        { tier: 'Anonymous', perMin: '10', perHour: '100', exports: 'TXT' },
        { tier: 'Community', perMin: '1,000', perHour: '100,000', exports: 'TXT, PDF, JSON' },
        { tier: 'Essentials', perMin: '30', perHour: '500', exports: 'TXT, PDF, JSON' },
        { tier: 'Academic', perMin: '60', perHour: '2,000', exports: '+ LaTeX' },
        { tier: 'Institutional', perMin: '200', perHour: '50,000', exports: 'All' },
      ],
      headers: ['Tier', 'Per minute', 'Per hour', 'Export'],
    },
    endpoints: {
      title: 'Main Endpoints',
      items: [
        { method: 'GET', path: '/api/v1/search/', desc: 'Full-text search with filters and facets.' },
        { method: 'GET', path: '/api/v1/laws/', desc: 'List laws with pagination and filtering.' },
        { method: 'GET', path: '/api/v1/laws/{id}/', desc: 'Law detail with articles and metadata.' },
        { method: 'GET', path: '/api/v1/laws/{id}/articles/', desc: 'Individual articles of a law.' },
        { method: 'GET', path: '/api/v1/categories/', desc: 'Legal corpus categories.' },
        { method: 'GET', path: '/api/v1/coverage/', desc: 'Coverage statistics of the legal universe.' },
        { method: 'GET', path: '/api/v1/judicial/', desc: 'Judicial records (jurisprudence and theses).' },
        { method: 'GET', path: '/api/v1/export/{id}/{format}/', desc: 'Export law in PDF, TXT, LaTeX, DOCX, EPUB, or JSON.' },
        { method: 'GET', path: '/api/v1/schema/', desc: 'OpenAPI specification (Swagger).' },
      ],
    },
    quickstart: {
      title: 'Quick Start',
      examples: [
        {
          lang: 'curl',
          label: 'curl',
          code: `# Search for articles about amparo
curl "https://api.tezca.mx/api/v1/search/?q=amparo&jurisdiction=federal"

# Get a specific law
curl "https://api.tezca.mx/api/v1/laws/fed_ley_amparo/"

# Export as PDF
curl -H "X-API-Key: tzk_your_key" \\
  "https://api.tezca.mx/api/v1/export/fed_ley_amparo/pdf/" -o amparo.pdf`,
        },
        {
          lang: 'python',
          label: 'Python',
          code: `import requests

API = "https://api.tezca.mx/api/v1"
headers = {"X-API-Key": "tzk_your_key"}

# Search articles
resp = requests.get(f"{API}/search/", params={"q": "amparo"}, headers=headers)
data = resp.json()
print(f"{data['total']} results found")

for result in data["results"][:5]:
    print(f"  {result['law_name']} - Art. {result['article']}")`,
        },
        {
          lang: 'javascript',
          label: 'JavaScript',
          code: `const API = "https://api.tezca.mx/api/v1";
const headers = { "X-API-Key": "tzk_your_key" };

// Search articles
const resp = await fetch(\`\${API}/search/?q=amparo\`, { headers });
const data = await resp.json();
console.log(\`\${data.total} results found\`);

data.results.slice(0, 5).forEach(r =>
  console.log(\`  \${r.law_name} - Art. \${r.article}\`)
);`,
        },
      ],
    },
    openapi: {
      title: 'OpenAPI Specification',
      body: 'Full interactive documentation is available at:',
      url: 'https://api.tezca.mx/api/v1/schema/',
    },
    contact: {
      title: 'Support',
      body: 'For technical questions, bug reports, or enterprise access requests:',
      email: 'admin@madfam.io',
    },
    copyrightPre: '© 2026 Innovaciones ',
    copyrightPost: ' SAS de CV. AGPL-3.0 License.',
  },
  nah: {
    back: 'Xicmocuepa caltenco',
    hero: {
      title: 'Tezca API',
      subtitle: 'In mēxihcatl tenahuatilli, huelīz ic tlahcuilōlli',
    },
    overview: {
      title: 'Tlanēxtīliztli',
      body: 'In Tezca REST API quipiya tēpōzmachiyōtl ic huelīz motēmoa ontlāmantli 35,000 tenahuatilli ihuan 3.5 millones tlanahuatilli in mēxihcatl tenahuatiliz tlamachiliztli. Quipiya federal, altepetl, ihuan calpulli tenahuatilli.',
      features: [
        { label: 'Tlahcuilōlli tēmōliztli', desc: 'Elasticsearch ica español tenahuatilli, sinónimos ihuan normalización.' },
        { label: 'Altepetl tēmōliztli', desc: 'Federal, altepetl (32) ihuan calpulli. Motēmoa ic categoría, estatus, tipo.' },
        { label: 'Mīlah tlamantli exportación', desc: 'PDF, TXT, LaTeX, DOCX, EPUB ihuan JSON.' },
        { label: 'Mochi tlālticpac cobertura', desc: 'DOF, OJN, gacetas, portales municipales, NOMs, tratados ihuan SCJN.' },
      ],
    },
    auth: {
      title: 'Tēnōnōtzaliztli',
      body: 'In API quipiya ēyi tlamantli ic mocaqui:',
      methods: [
        {
          name: 'API tlahtōlōtl (monemilia)',
          desc: 'Xictitlani X-API-Key header ica motlahtōlōtl (tzk_ pēhualiztli).',
          example: 'curl -H "X-API-Key: tzk_motlahtol" https://api.tezca.mx/api/v1/laws/',
        },
        {
          name: 'JWT (Janua)',
          desc: 'Bearer token ic web tēnōnōtzaliztli.',
          example: 'curl -H "Authorization: Bearer eyJ..." https://api.tezca.mx/api/v1/laws/',
        },
        {
          name: 'Ahmo tēnōnōtzaliztli',
          desc: 'Ahmo monequi tlahtōlōtl. 10 tlatlaniliztli/minuto ihuan 100/hora.',
          example: 'curl https://api.tezca.mx/api/v1/search/?q=amparo',
        },
      ],
    },
    tiers: {
      title: 'Tlamantli tēnōnōtzaliztli',
      rows: [
        { tier: 'Ahmo tēnōnōtz', perMin: '10', perHour: '100', exports: 'TXT' },
        { tier: 'Community', perMin: '1,000', perHour: '100,000', exports: 'TXT, PDF, JSON' },
        { tier: 'Essentials', perMin: '30', perHour: '500', exports: 'TXT, PDF, JSON' },
        { tier: 'Academic', perMin: '60', perHour: '2,000', exports: '+ LaTeX' },
        { tier: 'Institutional', perMin: '200', perHour: '50,000', exports: 'Mochi' },
      ],
      headers: ['Tlamantli', 'Ic minuto', 'Ic hora', 'Exportación'],
    },
    endpoints: {
      title: 'Tēnōnōtz huēyi',
      items: [
        { method: 'GET', path: '/api/v1/search/', desc: 'Tlahcuilōlli tēmōliztli ica filtros.' },
        { method: 'GET', path: '/api/v1/laws/', desc: 'Tenahuatilli tlanēxtīliztli.' },
        { method: 'GET', path: '/api/v1/laws/{id}/', desc: 'Tenahuatilli tlanēxtīliztli ica tlanahuatilli.' },
        { method: 'GET', path: '/api/v1/laws/{id}/articles/', desc: 'Tlanahuatilli cē tenahuatilli.' },
        { method: 'GET', path: '/api/v1/categories/', desc: 'Tenahuatilli categorías.' },
        { method: 'GET', path: '/api/v1/coverage/', desc: 'Cobertura tlanēxtīliztli.' },
        { method: 'GET', path: '/api/v1/judicial/', desc: 'Tēyācanaliztli tlanahuatilli.' },
        { method: 'GET', path: '/api/v1/export/{id}/{format}/', desc: 'Exportar tenahuatilli.' },
        { method: 'GET', path: '/api/v1/schema/', desc: 'OpenAPI tlanēxtīliztli.' },
      ],
    },
    quickstart: {
      title: 'Achto pēhualiztli',
      examples: [
        {
          lang: 'curl',
          label: 'curl',
          code: `# Xictēmoa tlanahuatilli ipan amparo
curl "https://api.tezca.mx/api/v1/search/?q=amparo&jurisdiction=federal"

# Xicpiya cē tenahuatilli
curl "https://api.tezca.mx/api/v1/laws/fed_ley_amparo/"

# Xicquīxtia quēmeh PDF
curl -H "X-API-Key: tzk_motlahtol" \\
  "https://api.tezca.mx/api/v1/export/fed_ley_amparo/pdf/" -o amparo.pdf`,
        },
        {
          lang: 'python',
          label: 'Python',
          code: `import requests

API = "https://api.tezca.mx/api/v1"
headers = {"X-API-Key": "tzk_motlahtol"}

# Xictēmoa tlanahuatilli
resp = requests.get(f"{API}/search/", params={"q": "amparo"}, headers=headers)
data = resp.json()
print(f"{data['total']} tlanēxtīliztli")

for result in data["results"][:5]:
    print(f"  {result['law_name']} - Art. {result['article']}")`,
        },
        {
          lang: 'javascript',
          label: 'JavaScript',
          code: `const API = "https://api.tezca.mx/api/v1";
const headers = { "X-API-Key": "tzk_motlahtol" };

// Xictēmoa tlanahuatilli
const resp = await fetch(\`\${API}/search/?q=amparo\`, { headers });
const data = await resp.json();
console.log(\`\${data.total} tlanēxtīliztli\`);

data.results.slice(0, 5).forEach(r =>
  console.log(\`  \${r.law_name} - Art. \${r.article}\`)
);`,
        },
      ],
    },
    openapi: {
      title: 'OpenAPI tlanēxtīliztli',
      body: 'Mochi tlanēxtīliztli motemoa:',
      url: 'https://api.tezca.mx/api/v1/schema/',
    },
    contact: {
      title: 'Tēnōnōtzaliztli',
      body: 'Ic tlatlaniliztli, tlahtlacōlli, ahnōzo enterprise:',
      email: 'admin@madfam.io',
    },
    copyrightPre: '© 2026 Innovaciones ',
    copyrightPost: ' SAS de CV. AGPL-3.0.',
  },
};

export default async function DesarrolladoresPage({
  searchParams,
}: {
  searchParams: Promise<{ lang?: string }>;
}) {
  const params = await searchParams;
  const lang = (['es', 'en', 'nah'].includes(params.lang ?? '') ? params.lang : 'es') as 'es' | 'en' | 'nah';
  const t = content[lang];

  return (
    <div className="min-h-screen bg-background">
      {/* Dark hero section */}
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

      <div className="container mx-auto px-4 sm:px-6 pb-16 sm:pb-24 max-w-4xl">
        {/* Overview */}
        <section className="space-y-6">
          <div className="flex items-center gap-3">
            <BookOpen className="h-6 w-6 text-primary" aria-hidden="true" />
            <h2 className="font-serif text-2xl sm:text-3xl font-semibold tracking-tight text-foreground">
              {t.overview.title}
            </h2>
          </div>
          <p className="text-base sm:text-lg leading-relaxed text-muted-foreground">
            {t.overview.body}
          </p>
          <div className="grid gap-4 sm:grid-cols-2">
            {t.overview.features.map((feat) => (
              <Card key={feat.label}>
                <CardContent className="p-5">
                  <h3 className="font-semibold text-sm text-foreground">{feat.label}</h3>
                  <p className="mt-1.5 text-sm text-muted-foreground leading-relaxed">{feat.desc}</p>
                </CardContent>
              </Card>
            ))}
          </div>
        </section>

        {/* Authentication */}
        <section className="mt-14 sm:mt-20 pt-12 border-t border-border space-y-6">
          <div className="flex items-center gap-3">
            <Key className="h-6 w-6 text-primary" aria-hidden="true" />
            <h2 className="font-serif text-2xl sm:text-3xl font-semibold tracking-tight text-foreground">
              {t.auth.title}
            </h2>
          </div>
          <p className="text-base text-muted-foreground">{t.auth.body}</p>
          <div className="space-y-4">
            {t.auth.methods.map((method) => (
              <Card key={method.name}>
                <CardContent className="p-5 space-y-3">
                  <h3 className="font-semibold text-sm text-foreground">{method.name}</h3>
                  <p className="text-sm text-muted-foreground">{method.desc}</p>
                  <pre className="bg-muted rounded-md p-3 text-xs overflow-x-auto">
                    <code>{method.example}</code>
                  </pre>
                </CardContent>
              </Card>
            ))}
          </div>
        </section>

        {/* Rate Limits */}
        <section className="mt-14 sm:mt-20 pt-12 border-t border-border space-y-6">
          <div className="flex items-center gap-3">
            <Zap className="h-6 w-6 text-primary" aria-hidden="true" />
            <h2 className="font-serif text-2xl sm:text-3xl font-semibold tracking-tight text-foreground">
              {t.tiers.title}
            </h2>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border">
                  {t.tiers.headers.map((h) => (
                    <th key={h} className="text-left py-3 px-4 font-semibold text-foreground">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {t.tiers.rows.map((row) => (
                  <tr key={row.tier} className="border-b border-border/50">
                    <td className="py-3 px-4 font-medium text-foreground">{row.tier}</td>
                    <td className="py-3 px-4 text-muted-foreground">{row.perMin}</td>
                    <td className="py-3 px-4 text-muted-foreground">{row.perHour}</td>
                    <td className="py-3 px-4 text-muted-foreground">{row.exports}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        {/* Endpoints */}
        <section className="mt-14 sm:mt-20 pt-12 border-t border-border space-y-6">
          <div className="flex items-center gap-3">
            <Terminal className="h-6 w-6 text-primary" aria-hidden="true" />
            <h2 className="font-serif text-2xl sm:text-3xl font-semibold tracking-tight text-foreground">
              {t.endpoints.title}
            </h2>
          </div>
          <div className="space-y-2">
            {t.endpoints.items.map((ep) => (
              <div key={ep.path} className="flex items-start gap-3 py-2">
                <span className="shrink-0 rounded bg-primary/10 px-2 py-0.5 text-xs font-mono font-semibold text-primary">
                  {ep.method}
                </span>
                <code className="shrink-0 text-sm font-mono text-foreground">{ep.path}</code>
                <span className="text-sm text-muted-foreground">{ep.desc}</span>
              </div>
            ))}
          </div>
        </section>

        {/* Quick Start */}
        <section className="mt-14 sm:mt-20 pt-12 border-t border-border space-y-6">
          <div className="flex items-center gap-3">
            <Code2 className="h-6 w-6 text-primary" aria-hidden="true" />
            <h2 className="font-serif text-2xl sm:text-3xl font-semibold tracking-tight text-foreground">
              {t.quickstart.title}
            </h2>
          </div>
          <div className="space-y-6">
            {t.quickstart.examples.map((ex) => (
              <div key={ex.lang}>
                <h3 className="text-sm font-semibold text-foreground mb-2">{ex.label}</h3>
                <pre className="bg-muted rounded-md p-4 text-xs overflow-x-auto leading-relaxed">
                  <code>{ex.code}</code>
                </pre>
              </div>
            ))}
          </div>
        </section>

        {/* OpenAPI */}
        <section className="mt-14 sm:mt-20 space-y-4">
          <h2 className="font-serif text-2xl sm:text-3xl font-semibold tracking-tight text-foreground">
            {t.openapi.title}
          </h2>
          <p className="text-base text-muted-foreground">{t.openapi.body}</p>
          <a
            href={t.openapi.url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 text-primary hover:underline font-medium font-mono text-sm"
          >
            {t.openapi.url}
          </a>
        </section>

        {/* Contact */}
        <section className="mt-14 sm:mt-20 space-y-4">
          <h2 className="font-serif text-2xl sm:text-3xl font-semibold tracking-tight text-foreground">
            {t.contact.title}
          </h2>
          <p className="text-base text-muted-foreground">{t.contact.body}</p>
          <a
            href={`mailto:${t.contact.email}`}
            className="inline-flex items-center gap-2 text-primary hover:underline font-medium"
          >
            {t.contact.email}
          </a>
        </section>

        {/* Footer */}
        <div className="mt-20 sm:mt-28 text-center border-t border-border pt-12">
          <p className="text-xs text-muted-foreground">
            {t.copyrightPre}
            <a href="https://madfam.io" target="_blank" rel="noopener noreferrer" className="underline hover:text-foreground">MADFAM</a>
            {t.copyrightPost}
          </p>
        </div>
      </div>
    </div>
  );
}
