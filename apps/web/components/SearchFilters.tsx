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
    sort: string;
    date_range?: string;
    title?: string;
    chapter?: string;
}

interface SearchFiltersProps {
    filters: SearchFilterState;
    onFiltersChange: (filters: SearchFilterState) => void;
    resultCount?: number;
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
        thisYear: '2024 (Este a\u00f1o)',
        last5Years: '\u00daltimos 5 a\u00f1os',
        older: 'M\u00e1s antiguos',
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
        thisYear: '2024 (This year)',
        last5Years: 'Last 5 years',
        older: 'Older',
        sortBy: 'Sort by',
    },
} as const;

function getJurisdictions(lang: Lang) {
    return [
        { id: 'federal', name: 'Federal', icon: '\u{1F3DB}\uFE0F' },
        { id: 'state', name: lang === 'es' ? 'Estatal' : 'State', icon: '\u{1F3E2}' },
        { id: 'municipal', name: lang === 'es' ? 'Municipal' : 'Municipal', icon: '\u{1F3D8}\uFE0F' },
    ];
}

function getCategories(lang: Lang) {
    return [
        { value: 'all', label: lang === 'es' ? 'Todas las categor\u00edas' : 'All categories' },
        { value: 'civil', label: 'Civil' },
        { value: 'penal', label: lang === 'es' ? 'Penal' : 'Criminal' },
        { value: 'mercantil', label: lang === 'es' ? 'Mercantil' : 'Commercial' },
        { value: 'fiscal', label: lang === 'es' ? 'Fiscal' : 'Tax' },
        { value: 'laboral', label: lang === 'es' ? 'Laboral' : 'Labor' },
        { value: 'administrativo', label: lang === 'es' ? 'Administrativo' : 'Administrative' },
        { value: 'constitucional', label: lang === 'es' ? 'Constitucional' : 'Constitutional' },
    ];
}

function getStatusOptions(lang: Lang) {
    return [
        { value: 'all', label: lang === 'es' ? 'Todos' : 'All' },
        { value: 'vigente', label: lang === 'es' ? 'Vigente' : 'In force' },
        { value: 'abrogado', label: lang === 'es' ? 'Abrogado' : 'Repealed' },
    ];
}

function getSortOptions(lang: Lang) {
    return [
        { value: 'relevance', label: lang === 'es' ? 'Relevancia' : 'Relevance' },
        { value: 'date_desc', label: lang === 'es' ? 'M\u00e1s recientes' : 'Most recent' },
        { value: 'date_asc', label: lang === 'es' ? 'M\u00e1s antiguos' : 'Oldest' },
        { value: 'name', label: lang === 'es' ? 'Nombre (A-Z)' : 'Name (A-Z)' },
    ];
}

export function SearchFilters({ filters, onFiltersChange, resultCount }: SearchFiltersProps) {
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
        if (filters.sort !== 'relevance') count++;
        if (filters.title) count++;
        if (filters.chapter) count++;
        return count;
    };

    const activeCount = activeFilterCount();
    const showStateSelector = filters.jurisdiction.includes('state');

    return (
        <Card className="mb-6">
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
                    <p className="text-sm text-muted-foreground mt-2">
                        {resultCount} {resultCount !== 1 ? t.resultPlural : t.resultSingular} {resultCount !== 1 ? t.foundPlural : t.foundSingular}
                    </p>
                )}
            </CardHeader>

            <CardContent className="space-y-6">
                {/* Jurisdiction */}
                <div>
                    <Label className="mb-3 block text-sm font-medium">{t.jurisdiction}</Label>
                    <div className="flex flex-wrap gap-2">
                        {JURISDICTIONS.map((jurisdiction) => (
                            <Button
                                key={jurisdiction.id}
                                variant={filters.jurisdiction.includes(jurisdiction.id) ? 'default' : 'outline'}
                                size="sm"
                                onClick={() => toggleJurisdiction(jurisdiction.id)}
                                aria-pressed={filters.jurisdiction.includes(jurisdiction.id)}
                                className="transition-all"
                            >
                                <span className="mr-1.5">{jurisdiction.icon}</span>
                                {jurisdiction.name}
                            </Button>
                        ))}
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
                            {CATEGORIES.map((cat) => (
                                <SelectItem key={cat.value} value={cat.value}>
                                    {cat.label}
                                </SelectItem>
                            ))}
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
                            {STATUS_OPTIONS.map((opt) => (
                                <SelectItem key={opt.value} value={opt.value}>
                                    {opt.label}
                                </SelectItem>
                            ))}
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
                            <SelectItem value="2024">{t.thisYear}</SelectItem>
                            <SelectItem value="2023">2023</SelectItem>
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
