/**
 * Maps feature_key identifiers to i18n display labels.
 * Used by InterestGate to show human-readable feature names.
 */

type Lang = 'es' | 'en' | 'nah';

const FEATURE_LABELS: Record<string, Record<Lang, string>> = {
    latex_export: {
        es: 'Exportar LaTeX',
        en: 'LaTeX export',
        nah: 'LaTeX tēmōhuiliztli',
    },
    docx_export: {
        es: 'Exportar DOCX',
        en: 'DOCX export',
        nah: 'DOCX tēmōhuiliztli',
    },
    epub_export: {
        es: 'Exportar EPUB',
        en: 'EPUB export',
        nah: 'EPUB tēmōhuiliztli',
    },
    webhooks: {
        es: 'Webhooks',
        en: 'Webhooks',
        nah: 'Webhooks',
    },
    graph_api: {
        es: 'API de grafo',
        en: 'Graph API',
        nah: 'API tlanextīliztli',
    },
    bulk_download: {
        es: 'Descarga masiva',
        en: 'Bulk download',
        nah: 'Huēyi tēmōhuiliztli',
    },
    search_analytics: {
        es: 'Análisis de búsqueda',
        en: 'Search analytics',
        nah: 'Tlatemoliztli tlaixmatiliztli',
    },
    advanced_search: {
        es: 'Búsqueda avanzada',
        en: 'Advanced search',
        nah: 'Huēyi tlatemoliztli',
    },
    platform_access: {
        es: 'Acceso a la plataforma',
        en: 'Platform access',
        nah: 'Tlahtōlcalli',
    },
    early_access: {
        es: 'Acceso anticipado',
        en: 'Early access',
        nah: 'Achto calaquiliztli',
    },
};

export function getFeatureLabel(featureKey: string, lang: Lang): string {
    return FEATURE_LABELS[featureKey]?.[lang] ?? featureKey;
}

export { FEATURE_LABELS };
