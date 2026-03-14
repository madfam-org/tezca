import type { Lang } from '@/components/providers/LanguageContext';

// ── Color mode ──────────────────────────────────────────────────────────

export type ColorMode = 'category' | 'tier';

// ── Category colors ─────────────────────────────────────────────────────

export const CATEGORY_COLORS: Record<string, string> = {
    constitucional: '#eab308',
    constitutional: '#eab308',
    fiscal: '#3b82f6',
    laboral: '#22c55e',
    penal: '#ef4444',
    civil: '#a855f7',
    mercantil: '#14b8a6',
    administrativo: '#64748b',
    regulatory: '#64748b',
    judicial: '#f97316',
};

export const DEFAULT_COLOR = '#94a3b8';

// ── Tier colors ─────────────────────────────────────────────────────────

export const TIER_COLORS: Record<string, string> = {
    federal: '#6366f1',
    state: '#10b981',
    municipal: '#f59e0b',
};

export const FOCAL_RING_COLOR = '#ef4444';

// ── Category labels (i18n) ──────────────────────────────────────────────

export const CATEGORY_LABELS: Record<string, Record<Lang, string>> = {
    constitucional: { es: 'Constitucional', en: 'Constitutional', nah: 'Tēpachotl' },
    constitutional: { es: 'Constitucional', en: 'Constitutional', nah: 'Tēpachotl' },
    fiscal: { es: 'Fiscal', en: 'Tax/Fiscal', nah: 'Tequitl' },
    laboral: { es: 'Laboral', en: 'Labor', nah: 'Tequipanoliztli' },
    penal: { es: 'Penal', en: 'Criminal', nah: 'Tētzacualiztli' },
    civil: { es: 'Civil', en: 'Civil', nah: 'Altepemaitl' },
    mercantil: { es: 'Mercantil', en: 'Commercial', nah: 'Tlanāmacaliztli' },
    administrativo: { es: 'Administrativo', en: 'Administrative', nah: 'Tēcpoyōtl' },
    regulatory: { es: 'Regulatorio', en: 'Regulatory', nah: 'Tēcpoyōtl' },
    judicial: { es: 'Judicial', en: 'Judicial', nah: 'Tlatzontequiliztli' },
};

export const TIER_LABELS: Record<string, Record<Lang, string>> = {
    federal: { es: 'Federal', en: 'Federal', nah: 'Federal' },
    state: { es: 'Estatal', en: 'State', nah: 'Altepetl' },
    municipal: { es: 'Municipal', en: 'Municipal', nah: 'Municipal' },
};

// ── Helpers ─────────────────────────────────────────────────────────────

export function getCategoryColor(category: string | null): string {
    if (!category) return DEFAULT_COLOR;
    return CATEGORY_COLORS[category] ?? DEFAULT_COLOR;
}

export function getTierColor(tier: string | null): string {
    if (!tier) return DEFAULT_COLOR;
    return TIER_COLORS[tier] ?? DEFAULT_COLOR;
}

export function getNodeColor(
    colorMode: ColorMode,
    category: string | null,
    tier: string | null
): string {
    return colorMode === 'category'
        ? getCategoryColor(category)
        : getTierColor(tier);
}

export function nodeSize(refCount: number): number {
    return Math.max(6, Math.min(30, 6 + Math.log2(Math.max(1, refCount)) * 3));
}

export function edgeSize(weight: number): number {
    return Math.max(1, Math.min(4, weight * 0.5));
}

/** Unique category keys present in data, for legend/filter rendering */
export function getUniqueCategories(nodes: { category: string | null }[]): string[] {
    const set = new Set<string>();
    for (const n of nodes) {
        if (n.category) set.add(n.category);
    }
    return Array.from(set).sort();
}

/** Unique state names present in data */
export function getUniqueStates(nodes: { state: string | null }[]): string[] {
    const set = new Set<string>();
    for (const n of nodes) {
        if (n.state) set.add(n.state);
    }
    return Array.from(set).sort();
}

export function getNodeLabel(
    shortName: string | null | undefined,
    fullName: string,
    zoomRatio: number
): string {
    if (zoomRatio > 1.5) return '';
    if (zoomRatio >= 0.5) return shortName || (fullName.length > 25 ? fullName.slice(0, 25) + '...' : fullName);
    return fullName;
}
