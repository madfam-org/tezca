'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle, Label, Select, SelectContent, SelectItem, SelectTrigger, SelectValue, Badge, Button, Input } from "@tezca/ui";
import { X, Filter, BookOpen } from 'lucide-react';
import { api } from '@/lib/api';
import { useLang, type Lang } from '@/components/providers/LanguageContext';

export interface SearchFilterState {
    jurisdiction: string[];
    category: string | null;
    state: string | null;
    municipality: string | null;
    status: string;
    law_type: string;
    sort: string;
    date_range?: string;
    title?: string;
    chapter?: string;
}

interface FacetBucket {
    key: string;
    count: number;
}

interface SearchFiltersProps {
    filters: SearchFilterState;
    onFiltersChange: (filters: SearchFilterState) => void;
    resultCount?: number;
    facets?: Record<string, FacetBucket[]>;
}

const content = {
    es: {
        filters: 'Filtros',
        activeSingular: 'activo',
        activePlural: 'activos',
        clear: 'Limpiar',
        resultSingular: 'resultado',
        resultPlural: 'resultados',
        foundSingular: 'encontrado',
        foundPlural: 'encontrados',
        jurisdiction: 'Jurisdicci\u00f3n',
        stateLabel: 'Estado',
        allStates: 'Todos los estados',
        municipality: 'Municipio',
        allMunicipalities: 'Todos los municipios',
        category: 'Categor\u00eda',
        selectCategory: 'Selecciona una categor\u00eda',
        statusValidity: 'Estado (Vigencia)',
        structure: 'Estructura',
        titleLabel: 'T\u00edtulo (ej. "T\u00cdTULO I")',
        titlePlaceholder: 'Filtrar por t\u00edtulo...',
        chapterLabel: 'Cap\u00edtulo (ej. "CAP\u00cdTULO I")',
        chapterPlaceholder: 'Filtrar por cap\u00edtulo...',
        publicationDate: 'Fecha de publicaci\u00f3n',
        anyDate: 'Cualquier fecha',
        thisYear: 'Este a\u00f1o',
        lastYear: 'A\u00f1o pasado',
        last5Years: '\u00daltimos 5 a\u00f1os',
        older: 'M\u00e1s antiguos',
        lawType: 'Tipo de Ley',
        allTypes: 'Todas',
        legislative: 'Legislativas',
        nonLegislative: 'No Legislativas',
        sortBy: 'Ordenar por',
    },
    en: {
        filters: 'Filters',
        activeSingular: 'active',
        activePlural: 'active',
        clear: 'Clear',
        resultSingular: 'result',
        resultPlural: 'results',
        foundSingular: 'found',
        foundPlural: 'found',
        jurisdiction: 'Jurisdiction',
        stateLabel: 'State',
        allStates: 'All states',
        municipality: 'Municipality',
        allMunicipalities: 'All municipalities',
        category: 'Category',
        selectCategory: 'Select a category',
        statusValidity: 'Status (Validity)',
        structure: 'Structure',
        titleLabel: 'Title (e.g. "TITULO I")',
        titlePlaceholder: 'Filter by title...',
        chapterLabel: 'Chapter (e.g. "CAPITULO I")',
        chapterPlaceholder: 'Filter by chapter...',
        publicationDate: 'Publication date',
        anyDate: 'Any date',
        thisYear: 'This year',
        lastYear: 'Last year',
        last5Years: 'Last 5 years',
        older: 'Older',
        lawType: 'Law Type',
        allTypes: 'All',
        legislative: 'Legislative',
        nonLegislative: 'Non-Legislative',
        sortBy: 'Sort by',
    },
    nah: {
        filters: 'Tlachiyaliztli',
        activeSingular: 'mochihua',
        activePlural: 'mochihua',
        clear: 'Xicchīpahua',
        resultSingular: 'tlanextīliztli',
        resultPlural: 'tlanextīliztli',
        foundSingular: 'monextia',
        foundPlural: 'monextia',
        jurisdiction: 'Tenahuatilizpan',
        stateLabel: 'Altepetl',
        allStates: 'Mochi altepetl',
        municipality: 'Calpulli',
        allMunicipalities: 'Mochi calpulli',
        category: 'Tlamantli',
        selectCategory: 'Xicpēpena cē tlamantli',
        statusValidity: 'Tlaneltilīliztli',
        structure: 'Tlachihualiztli',
        titleLabel: 'Tōcāitl',
        titlePlaceholder: 'Xictlatemo tōcāitl...',
        chapterLabel: 'Capitulo',
        chapterPlaceholder: 'Xictlatemo capitulo...',
        publicationDate: 'Tlanextīliliztli',
        anyDate: 'Mochi tōnalli',
        thisYear: 'Inīn xihuitl',
        lastYear: 'Achtopa xihuitl',
        last5Years: 'Tlāmian 5 xihuitl',
        older: 'Huēhcāuh',
        lawType: 'Tenahuatilli tlamantli',
        allTypes: 'Mochi',
        legislative: 'Tenahuatīlli',
        nonLegislative: 'Ahmo Tenahuatīlli',
        sortBy: 'Xictlalia ic',
    },
} as const;

function getJurisdictions(lang: Lang) {
    const names: Record<Lang, Record<string, string>> = {
        es: { federal: 'Federal', state: 'Estatal', municipal: 'Municipal' },
        en: { federal: 'Federal', state: 'State', municipal: 'Municipal' },
        nah: { federal: 'Federal', state: 'Altepetl', municipal: 'Calpulli' },
    };
    return [
        { id: 'federal', name: names[lang].federal, icon: '\u{1F3DB}\uFE0F' },
        { id: 'state', name: names[lang].state, icon: '\u{1F3E2}' },
        { id: 'municipal', name: names[lang].municipal, icon: '\u{1F3D8}\uFE0F' },
    ];
}

function getCategories(lang: Lang) {
    const labels: Record<Lang, Record<string, string>> = {
        es: { all: 'Todas las categor\u00edas', penal: 'Penal', mercantil: 'Mercantil', fiscal: 'Fiscal', laboral: 'Laboral', administrativo: 'Administrativo', constitucional: 'Constitucional' },
        en: { all: 'All categories', penal: 'Criminal', mercantil: 'Commercial', fiscal: 'Tax', laboral: 'Labor', administrativo: 'Administrative', constitucional: 'Constitutional' },
        nah: { all: 'Mochi tlamantli', penal: 'Tēīxnāmiquiliztli', mercantil: 'Tlanāmacaliztli', fiscal: 'Tequitl', laboral: 'Tequipanōliztli', administrativo: 'Tēuctlahtoāni', constitucional: 'Tenahuatilli' },
    };
    const l = labels[lang];
    return [
        { value: 'all', label: l.all },
        { value: 'civil', label: 'Civil' },
        { value: 'penal', label: l.penal },
        { value: 'mercantil', label: l.mercantil },
        { value: 'fiscal', label: l.fiscal },
        { value: 'laboral', label: l.laboral },
        { value: 'administrativo', label: l.administrativo },
        { value: 'constitucional', label: l.constitucional },
    ];
}

function getStatusOptions(lang: Lang) {
    const labels: Record<Lang, Record<string, string>> = {
        es: { all: 'Todos', vigente: 'Vigente', abrogado: 'Abrogado' },
        en: { all: 'All', vigente: 'In force', abrogado: 'Repealed' },
        nah: { all: 'Mochi', vigente: 'Mochihua', abrogado: 'Ōmopōuh' },
    };
    const l = labels[lang];
    return [
        { value: 'all', label: l.all },
        { value: 'vigente', label: l.vigente },
        { value: 'abrogado', label: l.abrogado },
    ];
}

function getSortOptions(lang: Lang) {
    const labels: Record<Lang, Record<string, string>> = {
        es: { relevance: 'Relevancia', date_desc: 'M\u00e1s recientes', date_asc: 'M\u00e1s antiguos', name: 'Nombre (A-Z)' },
        en: { relevance: 'Relevance', date_desc: 'Most recent', date_asc: 'Oldest', name: 'Name (A-Z)' },
        nah: { relevance: 'Tlaiyōcāyōtl', date_desc: 'Yancuīc', date_asc: 'Huēhcāuh', name: 'Tōcāitl (A-Z)' },
    };
    const l = labels[lang];
    return [
        { value: 'relevance', label: l.relevance },
        { value: 'date_desc', label: l.date_desc },
        { value: 'date_asc', label: l.date_asc },
        { value: 'name', label: l.name },
    ];
}

function getFacetCount(facets: Record<string, FacetBucket[]> | undefined, facetKey: string, value: string): number | null {
    if (!facets?.[facetKey]) return null;
    const bucket = facets[facetKey].find(b => b.key === value);
    return bucket ? bucket.count : 0;
}

export function SearchFilters({ filters, onFiltersChange, resultCount, facets }: SearchFiltersProps) {
    const { lang } = useLang();
    const t = content[lang];

    const JURISDICTIONS = getJurisdictions(lang);
    const CATEGORIES = getCategories(lang);
    const STATUS_OPTIONS = getStatusOptions(lang);
    const SORT_OPTIONS = getSortOptions(lang);

    const [states, setStates] = useState<string[]>([]);
    const [municipalities, setMunicipalities] = useState<{ municipality: string; state: string; count: number }[]>([]);

    useEffect(() => {
        api.getStates().then(data => setStates(data.states)).catch(console.error);
    }, []);

    const showMunicipalitySelector = filters.jurisdiction.includes('municipal');

    useEffect(() => {
        if (showMunicipalitySelector) {
            api.getMunicipalities(filters.state || undefined)
                .then(setMunicipalities)
                .catch(() => setMunicipalities([]));
        }
    }, [showMunicipalitySelector, filters.state]);

    const toggleJurisdiction = (jurisdictionId: string) => {
        const newJurisdictions = filters.jurisdiction.includes(jurisdictionId)
            ? filters.jurisdiction.filter(j => j !== jurisdictionId)
            : [...filters.jurisdiction, jurisdictionId];

        // If removing state, clear state selection
        const newState = (!newJurisdictions.includes('state')) ? null : filters.state;

        onFiltersChange({ ...filters, jurisdiction: newJurisdictions, state: newState });
    };

    const clearFilters = () => {
        onFiltersChange({
            jurisdiction: ['federal'], // Default to federal
            category: null,
            state: null,
            municipality: null,
            status: 'all',
            law_type: 'all',
            sort: 'relevance',
            title: '',
            chapter: '',
        });
    };

    const activeFilterCount = () => {
        let count = 0;
        if (filters.jurisdiction.length !== 1 || !filters.jurisdiction.includes('federal')) count++;
        if (filters.category && filters.category !== 'all') count++;
        if (filters.state && filters.state !== 'all') count++;
        if (filters.municipality && filters.municipality !== 'all') count++;
        if (filters.status !== 'all') count++;
        if (filters.law_type && filters.law_type !== 'all') count++;
        if (filters.sort !== 'relevance') count++;
        if (filters.title) count++;
        if (filters.chapter) count++;
        return count;
    };

    const activeCount = activeFilterCount();
    const showStateSelector = filters.jurisdiction.includes('state');

    return (
        <Card className="mb-6" role="search" aria-label={t.filters}>
            <CardHeader className="pb-4">
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                        <CardTitle className="text-lg">
                            <Filter aria-hidden="true" className="inline h-5 w-5 mr-2" />
                            {t.filters}
                        </CardTitle>
                        {activeCount > 0 && (
                            <Badge variant="secondary" className="text-xs">
                                {activeCount} {activeCount !== 1 ? t.activePlural : t.activeSingular}
                            </Badge>
                        )}
                    </div>

                    {activeCount > 0 && (
                        <Button
                            variant="ghost"
                            size="sm"
                            onClick={clearFilters}
                            className="h-8"
                        >
                            <X className="mr-1 h-4 w-4" />
                            {t.clear}
                        </Button>
                    )}
                </div>

                {resultCount !== undefined && (
                    <p className="text-sm text-muted-foreground mt-2" aria-live="polite">
                        {resultCount} {resultCount !== 1 ? t.resultPlural : t.resultSingular} {resultCount !== 1 ? t.foundPlural : t.foundSingular}
                    </p>
                )}
            </CardHeader>

            <CardContent className="space-y-6">
                {/* Jurisdiction */}
                <div>
                    <Label className="mb-3 block text-sm font-medium">{t.jurisdiction}</Label>
                    <div className="flex flex-wrap gap-2">
                        {JURISDICTIONS.map((jurisdiction) => {
                            const count = getFacetCount(facets, 'by_tier', jurisdiction.id);
                            return (
                                <Button
                                    key={jurisdiction.id}
                                    variant={filters.jurisdiction.includes(jurisdiction.id) ? 'default' : 'outline'}
                                    size="sm"
                                    onClick={() => toggleJurisdiction(jurisdiction.id)}
                                    aria-pressed={filters.jurisdiction.includes(jurisdiction.id)}
                                    className={`transition-all ${count === 0 ? 'opacity-50' : ''}`}
                                >
                                    <span className="mr-1.5">{jurisdiction.icon}</span>
                                    {jurisdiction.name}
                                    {count !== null && (
                                        <span className="ml-1.5 text-xs opacity-70">({count.toLocaleString()})</span>
                                    )}
                                </Button>
                            );
                        })}
                    </div>
                </div>

                {/* State Selector - Conditional */}
                {showStateSelector && (
                    <div className="animate-in fade-in slide-in-from-top-2 duration-200">
                        <Label htmlFor="state" className="mb-2 block text-sm font-medium">
                            {t.stateLabel}
                        </Label>
                        <Select
                            value={filters.state || 'all'}
                            onValueChange={(value) =>
                                onFiltersChange({ ...filters, state: value === 'all' ? null : value })
                            }
                        >
                            <SelectTrigger id="state">
                                <SelectValue placeholder={t.allStates} />
                            </SelectTrigger>
                            <SelectContent>
                                <SelectItem value="all">{t.allStates}</SelectItem>
                                {states.map((state) => (
                                    <SelectItem key={state} value={state}>
                                        {state}
                                    </SelectItem>
                                ))}
                            </SelectContent>
                        </Select>
                    </div>
                )}

                {/* Municipality Selector - Conditional */}
                {showMunicipalitySelector && (
                    <div className="animate-in fade-in slide-in-from-top-2 duration-200">
                        <Label htmlFor="municipality" className="mb-2 block text-sm font-medium">
                            {t.municipality}
                        </Label>
                        <Select
                            value={filters.municipality || 'all'}
                            onValueChange={(value: string) =>
                                onFiltersChange({ ...filters, municipality: value === 'all' ? null : value })
                            }
                        >
                            <SelectTrigger id="municipality">
                                <SelectValue placeholder={t.allMunicipalities} />
                            </SelectTrigger>
                            <SelectContent>
                                <SelectItem value="all">{t.allMunicipalities}</SelectItem>
                                {municipalities.map((m) => (
                                    <SelectItem key={m.municipality} value={m.municipality}>
                                        {m.municipality} ({m.count})
                                    </SelectItem>
                                ))}
                            </SelectContent>
                        </Select>
                    </div>
                )}

                {/* Category */}
                <div>
                    <Label htmlFor="category" className="mb-2 block text-sm font-medium">
                        {t.category}
                    </Label>
                    <Select
                        value={filters.category || 'all'}
                        onValueChange={(value) =>
                            onFiltersChange({ ...filters, category: value === 'all' ? null : value })
                        }
                    >
                        <SelectTrigger id="category">
                            <SelectValue placeholder={t.selectCategory} />
                        </SelectTrigger>
                        <SelectContent>
                            {CATEGORIES.map((cat) => {
                                const count = cat.value !== 'all' ? getFacetCount(facets, 'by_category', cat.value) : null;
                                return (
                                    <SelectItem key={cat.value} value={cat.value} className={count === 0 ? 'opacity-50' : ''}>
                                        {cat.label}{count !== null ? ` (${count.toLocaleString()})` : ''}
                                    </SelectItem>
                                );
                            })}
                        </SelectContent>
                    </Select>
                </div>

                {/* Status */}
                <div>
                    <Label htmlFor="status" className="mb-2 block text-sm font-medium">
                        {t.statusValidity}
                    </Label>
                    <Select
                        value={filters.status}
                        onValueChange={(value) => onFiltersChange({ ...filters, status: value })}
                    >
                        <SelectTrigger id="status">
                            <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                            {STATUS_OPTIONS.map((opt) => {
                                const count = opt.value !== 'all' ? getFacetCount(facets, 'by_status', opt.value) : null;
                                return (
                                    <SelectItem key={opt.value} value={opt.value} className={count === 0 ? 'opacity-50' : ''}>
                                        {opt.label}{count !== null ? ` (${count.toLocaleString()})` : ''}
                                    </SelectItem>
                                );
                            })}
                        </SelectContent>
                    </Select>
                </div>

                {/* Law Type */}
                <div>
                    <Label htmlFor="law_type" className="mb-2 block text-sm font-medium">
                        {t.lawType}
                    </Label>
                    <Select
                        value={filters.law_type || 'all'}
                        onValueChange={(value) => onFiltersChange({ ...filters, law_type: value })}
                    >
                        <SelectTrigger id="law_type">
                            <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                            <SelectItem value="all">{t.allTypes}</SelectItem>
                            {(['legislative', 'non_legislative'] as const).map((val) => {
                                const count = getFacetCount(facets, 'by_law_type', val);
                                const label = val === 'legislative' ? t.legislative : t.nonLegislative;
                                return (
                                    <SelectItem key={val} value={val} className={count === 0 ? 'opacity-50' : ''}>
                                        {label}{count !== null ? ` (${count.toLocaleString()})` : ''}
                                    </SelectItem>
                                );
                            })}
                        </SelectContent>
                    </Select>
                </div>

                {/* Structure Filters (New) */}
                <div>
                    <h3 className="mb-3 text-sm font-medium flex items-center gap-2 text-muted-foreground border-t pt-4">
                        <BookOpen aria-hidden="true" className="h-4 w-4" />
                        {t.structure}
                    </h3>

                    <div className="space-y-3">
                        <div>
                            <Label htmlFor="title_filter" className="mb-2 block text-xs font-medium text-muted-foreground">
                                {t.titleLabel}
                            </Label>
                            <Input
                                id="title_filter"
                                placeholder={t.titlePlaceholder}
                                value={filters.title || ''}
                                onChange={(e) => onFiltersChange({ ...filters, title: e.target.value })}
                                className="h-8 text-sm"
                            />
                        </div>

                        <div>
                            <Label htmlFor="chapter_filter" className="mb-2 block text-xs font-medium text-muted-foreground">
                                {t.chapterLabel}
                            </Label>
                            <Input
                                id="chapter_filter"
                                placeholder={t.chapterPlaceholder}
                                value={filters.chapter || ''}
                                onChange={(e) => onFiltersChange({ ...filters, chapter: e.target.value })}
                                className="h-8 text-sm"
                            />
                        </div>
                    </div>
                </div>

                <div>
                    <Label htmlFor="date_range" className="mb-2 block text-sm font-medium">
                        {t.publicationDate}
                    </Label>
                    <Select
                        value={filters.date_range || 'all'}
                        onValueChange={(value) => onFiltersChange({ ...filters, date_range: value })}
                    >
                        <SelectTrigger id="date_range">
                            <SelectValue placeholder={t.anyDate} />
                        </SelectTrigger>
                        <SelectContent>
                            <SelectItem value="all">{t.anyDate}</SelectItem>
                            <SelectItem value="this_year">{t.thisYear}</SelectItem>
                            <SelectItem value="last_year">{t.lastYear}</SelectItem>
                            <SelectItem value="last_5_years">{t.last5Years}</SelectItem>
                            <SelectItem value="older">{t.older}</SelectItem>
                        </SelectContent>
                    </Select>
                </div>

                {/* Sort */}
                <div>
                    <Label htmlFor="sort" className="mb-2 block text-sm font-medium">
                        {t.sortBy}
                    </Label>
                    <Select
                        value={filters.sort}
                        onValueChange={(value) => onFiltersChange({ ...filters, sort: value })}
                    >
                        <SelectTrigger id="sort">
                            <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                            {SORT_OPTIONS.map((opt) => (
                                <SelectItem key={opt.value} value={opt.value}>
                                    {opt.label}
                                </SelectItem>
                            ))}
                        </SelectContent>
                    </Select>
                </div>
            </CardContent>
        </Card>
    );
}
