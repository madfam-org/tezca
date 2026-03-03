'use client';

import { useState } from 'react';
import Link from 'next/link';
import { ArrowLeft, Search, Scale, BookOpen, Filter, ChevronRight } from 'lucide-react';
import { Button, Card, CardContent, Input, Badge } from '@tezca/ui';
import { LanguageToggle } from '@/components/common/LanguageToggle';
import { useLang } from '@/contexts/LanguageContext';
import { API_BASE_URL } from '@/lib/config';

type Lang = 'es' | 'en' | 'nah';

const content = {
  es: {
    title: 'Jurisprudencia',
    subtitle: 'Busca en el corpus judicial de la SCJN: jurisprudencia y tesis aisladas.',
    searchPlaceholder: 'Buscar por rubro, texto o registro...',
    search: 'Buscar',
    filters: 'Filtros',
    tipo: 'Tipo',
    materia: 'Materia',
    all: 'Todos',
    jurisprudencia: 'Jurisprudencia',
    tesisAislada: 'Tesis aislada',
    civil: 'Civil',
    penal: 'Penal',
    administrativa: 'Administrativa',
    laboral: 'Laboral',
    constitucional: 'Constitucional',
    comun: 'Común',
    results: 'resultados',
    noResults: 'No se encontraron resultados',
    noResultsHint: 'Intenta con otros términos de búsqueda o ajusta los filtros.',
    loading: 'Buscando...',
    ponente: 'Ponente',
    epoca: 'Época',
    instancia: 'Instancia',
    comingSoon: 'Próximamente',
    comingSoonDesc: 'Estamos trabajando en integrar el corpus judicial de la SCJN. Mientras tanto, puedes consultar el Semanario Judicial de la Federación directamente.',
    visitSJF: 'Visitar SJF',
    back: 'Inicio',
  },
  en: {
    title: 'Case Law',
    subtitle: 'Search the SCJN judicial corpus: binding precedent and isolated theses.',
    searchPlaceholder: 'Search by heading, text, or registry...',
    search: 'Search',
    filters: 'Filters',
    tipo: 'Type',
    materia: 'Subject',
    all: 'All',
    jurisprudencia: 'Binding precedent',
    tesisAislada: 'Isolated thesis',
    civil: 'Civil',
    penal: 'Criminal',
    administrativa: 'Administrative',
    laboral: 'Labor',
    constitucional: 'Constitutional',
    comun: 'General',
    results: 'results',
    noResults: 'No results found',
    noResultsHint: 'Try different search terms or adjust your filters.',
    loading: 'Searching...',
    ponente: 'Reporting Justice',
    epoca: 'Epoch',
    instancia: 'Court',
    comingSoon: 'Coming Soon',
    comingSoonDesc: 'We are working on integrating the SCJN judicial corpus. In the meantime, you can consult the Federal Judicial Weekly directly.',
    visitSJF: 'Visit SJF',
    back: 'Home',
  },
  nah: {
    title: 'Tlatēcpantlahtolli',
    subtitle: 'Xictēmoa īpan SCJN tlahtōlhuāztli: tlatēcpantlahtolli īhuān tēixnāmictīliztli.',
    searchPlaceholder: 'Xictēmoa...',
    search: 'Tēmoa',
    filters: 'Tlapēpenaliztli',
    tipo: 'Tlamantli',
    materia: 'Tlahcuilōlli',
    all: 'Mochi',
    jurisprudencia: 'Tlatēcpantlahtolli',
    tesisAislada: 'Tēixnāmictīliztli',
    civil: 'Civil',
    penal: 'Tētzacuiltīliztli',
    administrativa: 'Tēpachōliztli',
    laboral: 'Tequitl',
    constitucional: 'Tlanahuatīlli',
    comun: 'Nēnquīzqui',
    results: 'tlahtōlmeh',
    noResults: 'Ahmo mottac',
    noResultsHint: 'Xicyēyeco occē tlahtōlli.',
    loading: 'Motēmoa...',
    ponente: 'Tlahtōcāyōtl',
    epoca: 'Cāhuitl',
    instancia: 'Tēcpancalli',
    comingSoon: 'Niman huālāz',
    comingSoonDesc: 'Ticchīhua in SCJN tlahtōlhuāztli. Ahmo huehcāuh.',
    visitSJF: 'SJF',
    back: 'Calīxcuāitl',
  },
};

interface JudicialResult {
  id: number;
  registro: string;
  epoca: string;
  instancia: string;
  materia: string;
  tipo: string;
  rubro: string;
  ponente: string;
  fecha_publicacion: string | null;
}

interface SearchResponse {
  total: number;
  page: number;
  page_size: number;
  results: JudicialResult[];
}

const materiaColors: Record<string, string> = {
  civil: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
  penal: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
  administrativa: 'bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-200',
  laboral: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
  constitucional: 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200',
  comun: 'bg-muted text-muted-foreground',
};

export default function JurisprudenciaPage() {
  const { lang } = useLang() as { lang: Lang };
  const t = content[lang];

  const [query, setQuery] = useState('');
  const [tipo, setTipo] = useState('');
  const [materia, setMateria] = useState('');
  const [results, setResults] = useState<SearchResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [hasSearched, setHasSearched] = useState(false);

  const handleSearch = async (page = 1) => {
    if (!query.trim()) return;
    setLoading(true);
    setHasSearched(true);

    const params = new URLSearchParams({ q: query, page: String(page), page_size: '20' });
    if (tipo) params.set('tipo', tipo);
    if (materia) params.set('materia', materia);

    try {
      const res = await fetch(`${API_BASE_URL}/judicial/search/?${params}`);
      if (res.ok) {
        setResults(await res.json());
      }
    } catch {
      // silent fail
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <div className="border-b bg-muted/30">
        <div className="mx-auto max-w-5xl px-4 py-3 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors">
            <ArrowLeft className="h-4 w-4" />
            {t.back}
          </Link>
          <LanguageToggle />
        </div>
      </div>

      <div className="mx-auto max-w-5xl px-4 py-12">
        {/* Hero */}
        <div className="text-center mb-10">
          <div className="flex items-center justify-center gap-3 mb-4">
            <Scale className="h-8 w-8 text-primary" />
            <h1 className="font-display text-3xl sm:text-4xl font-bold text-foreground">
              {t.title}
            </h1>
          </div>
          <p className="text-muted-foreground max-w-2xl mx-auto">{t.subtitle}</p>
        </div>

        {/* Search */}
        <div className="mb-8">
          <form
            onSubmit={(e) => { e.preventDefault(); handleSearch(); }}
            className="flex gap-2"
          >
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                value={query}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => setQuery(e.target.value)}
                placeholder={t.searchPlaceholder}
                className="pl-10"
              />
            </div>
            <Button type="submit" disabled={loading}>
              {loading ? t.loading : t.search}
            </Button>
          </form>

          {/* Filters */}
          <div className="flex flex-wrap gap-4 mt-4">
            <div className="flex items-center gap-2">
              <Filter className="h-4 w-4 text-muted-foreground" />
              <span className="text-sm text-muted-foreground">{t.filters}:</span>
            </div>
            <select
              value={tipo}
              onChange={(e) => setTipo(e.target.value)}
              className="text-sm border rounded-md px-2 py-1 bg-background text-foreground"
            >
              <option value="">{t.tipo}: {t.all}</option>
              <option value="jurisprudencia">{t.jurisprudencia}</option>
              <option value="tesis_aislada">{t.tesisAislada}</option>
            </select>
            <select
              value={materia}
              onChange={(e) => setMateria(e.target.value)}
              className="text-sm border rounded-md px-2 py-1 bg-background text-foreground"
            >
              <option value="">{t.materia}: {t.all}</option>
              <option value="civil">{t.civil}</option>
              <option value="penal">{t.penal}</option>
              <option value="administrativa">{t.administrativa}</option>
              <option value="laboral">{t.laboral}</option>
              <option value="constitucional">{t.constitucional}</option>
              <option value="comun">{t.comun}</option>
            </select>
          </div>
        </div>

        {/* Results */}
        {hasSearched && results && (
          <div className="space-y-4">
            <p className="text-sm text-muted-foreground">
              {results.total.toLocaleString()} {t.results}
            </p>

            {results.results.length === 0 ? (
              <Card>
                <CardContent className="p-8 text-center">
                  <BookOpen className="h-10 w-10 text-muted-foreground mx-auto mb-3" />
                  <p className="font-medium text-foreground">{t.noResults}</p>
                  <p className="text-sm text-muted-foreground mt-1">{t.noResultsHint}</p>
                </CardContent>
              </Card>
            ) : (
              results.results.map((record) => (
                <Card key={record.id} className="hover:bg-muted/30 transition-colors">
                  <CardContent className="p-4">
                    <div className="flex items-start gap-3">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1 flex-wrap">
                          <Badge variant="outline" className="text-xs">
                            {record.tipo === 'jurisprudencia' ? t.jurisprudencia : t.tesisAislada}
                          </Badge>
                          <span className={`text-xs px-2 py-0.5 rounded-full ${materiaColors[record.materia] || materiaColors.comun}`}>
                            {t[record.materia as keyof typeof t] || record.materia}
                          </span>
                          <span className="text-xs text-muted-foreground">
                            {record.registro}
                          </span>
                        </div>
                        <h3 className="font-medium text-sm text-foreground line-clamp-2">
                          {record.rubro}
                        </h3>
                        <div className="flex items-center gap-4 mt-2 text-xs text-muted-foreground">
                          {record.instancia && (
                            <span>{t.instancia}: {record.instancia}</span>
                          )}
                          {record.ponente && (
                            <span>{t.ponente}: {record.ponente}</span>
                          )}
                          {record.epoca && (
                            <span>{t.epoca}: {record.epoca}</span>
                          )}
                        </div>
                      </div>
                      <ChevronRight className="h-5 w-5 text-muted-foreground shrink-0 mt-1" />
                    </div>
                  </CardContent>
                </Card>
              ))
            )}

            {/* Pagination */}
            {results.total > results.page_size && (
              <div className="flex justify-center gap-2 pt-4">
                {results.page > 1 && (
                  <Button variant="outline" size="sm" onClick={() => handleSearch(results.page - 1)}>
                    ←
                  </Button>
                )}
                <span className="text-sm text-muted-foreground flex items-center px-3">
                  {results.page} / {Math.ceil(results.total / results.page_size)}
                </span>
                {results.page < Math.ceil(results.total / results.page_size) && (
                  <Button variant="outline" size="sm" onClick={() => handleSearch(results.page + 1)}>
                    →
                  </Button>
                )}
              </div>
            )}
          </div>
        )}

        {/* Coming Soon notice (shown when no search has been done) */}
        {!hasSearched && (
          <Card className="mt-8">
            <CardContent className="p-8 text-center">
              <Scale className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
              <h2 className="font-semibold text-lg text-foreground mb-2">{t.comingSoon}</h2>
              <p className="text-muted-foreground max-w-lg mx-auto mb-4">
                {t.comingSoonDesc}
              </p>
              <Button variant="outline" asChild>
                <a href="https://sjf.scjn.gob.mx" target="_blank" rel="noopener noreferrer">
                  {t.visitSJF} ↗
                </a>
              </Button>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
