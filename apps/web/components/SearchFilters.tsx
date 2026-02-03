'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { X, Filter } from 'lucide-react';

export interface SearchFilterState {
    jurisdiction: string[];
    category: string | null;
    status: string;
    sort: string;
}

interface SearchFiltersProps {
    filters: SearchFilterState;
    onFiltersChange: (filters: SearchFilterState) => void;
    resultCount?: number;
}

const JURISDICTIONS = [
    { id: 'federal', name: 'Federal', icon: '🏛️' },
    { id: 'state', name: 'Estatal', icon: '🏢' },
    { id: 'municipal', name: 'Municipal', icon: '🏘️', disabled: true },
];

const CATEGORIES = [
    { value: 'all', label: 'Todas las categorías' },
    { value: 'civil', label: 'Civil' },
    { value: 'penal', label: 'Penal' },
    { value: 'mercantil', label: 'Mercantil' },
    { value: 'fiscal', label: 'Fiscal' },
    { value: 'laboral', label: 'Laboral' },
    { value: 'administrativo', label: 'Administrativo' },
    { value: 'constitucional', label: 'Constitucional' },
];

const STATUS_OPTIONS = [
    { value: 'all', label: 'Todos' },
    { value: 'vigente', label: 'Vigente' },
    { value: 'abrogado', label: 'Abrogado' },
];

const SORT_OPTIONS = [
    { value: 'relevance', label: 'Relevancia' },
    { value: 'date_desc', label: 'Más recientes' },
    { value: 'date_asc', label: 'Más antiguos' },
    { value: 'name', label: 'Nombre (A-Z)' },
];

export function SearchFilters({ filters, onFiltersChange, resultCount }: SearchFiltersProps) {
    const toggleJurisdiction = (jurisdictionId: string) => {
        const newJurisdictions = filters.jurisdiction.includes(jurisdictionId)
            ? filters.jurisdiction.filter(j => j !== jurisdictionId)
            : [...filters.jurisdiction, jurisdictionId];

        onFiltersChange({ ...filters, jurisdiction: newJurisdictions });
    };

    const clearFilters = () => {
        onFiltersChange({
            jurisdiction: ['federal'], // Default to federal
            category: null,
            status: 'all',
            sort: 'relevance',
        });
    };

    const activeFilterCount = () => {
        let count = 0;
        if (filters.jurisdiction.length !== 1 || !filters.jurisdiction.includes('federal')) count++;
        if (filters.category && filters.category !== 'all') count++;
        if (filters.status !== 'all') count++;
        if (filters.sort !== 'relevance') count++;
        return count;
    };

    const activeCount = activeFilterCount();

    return (
        <Card className="mb-6">
            <CardHeader className="pb-4">
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                        <CardTitle className="text-lg">
                            <Filter className="inline h-5 w-5 mr-2" />
                            Filtros
                        </CardTitle>
                        {activeCount > 0 && (
                            <Badge variant="secondary" className="text-xs">
                                {activeCount} activo{activeCount !== 1 ? 's' : ''}
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
                            Limpiar
                        </Button>
                    )}
                </div>

                {resultCount !== undefined && (
                    <p className="text-sm text-muted-foreground mt-2">
                        {resultCount} resultado{resultCount !== 1 ? 's' : ''} encontrado{resultCount !== 1 ? 's' : ''}
                    </p>
                )}
            </CardHeader>

            <CardContent className="space-y-6">
                {/* Jurisdiction */}
                <div>
                    <Label className="mb-3 block text-sm font-medium">Jurisdicción</Label>
                    <div className="flex flex-wrap gap-2">
                        {JURISDICTIONS.map((jurisdiction) => (
                            <Button
                                key={jurisdiction.id}
                                variant={filters.jurisdiction.includes(jurisdiction.id) ? 'default' : 'outline'}
                                size="sm"
                                onClick={() => toggleJurisdiction(jurisdiction.id)}
                                disabled={jurisdiction.disabled}
                                className="transition-all"
                            >
                                <span className="mr-1.5">{jurisdiction.icon}</span>
                                {jurisdiction.name}
                                {jurisdiction.disabled && <span className="ml-1 text-xs">(Próximamente)</span>}
                            </Button>
                        ))}
                    </div>
                </div>

                {/* Category */}
                <div>
                    <Label htmlFor="category" className="mb-2 block text-sm font-medium">
                        Categoría
                    </Label>
                    <Select
                        value={filters.category || 'all'}
                        onValueChange={(value) =>
                            onFiltersChange({ ...filters, category: value === 'all' ? null : value })
                        }
                    >
                        <SelectTrigger id="category">
                            <SelectValue placeholder="Selecciona una categoría" />
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
                        Estado
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

                {/* Sort */}
                <div>
                    <Label htmlFor="sort" className="mb-2 block text-sm font-medium">
                        Ordenar por
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
