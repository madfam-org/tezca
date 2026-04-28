import { describe, expect, it } from 'vitest';

import { FEATURE_LABELS, getFeatureLabel } from '@/lib/feature-labels';

describe('getFeatureLabel', () => {
    it('returns the localized label for a known feature', () => {
        expect(getFeatureLabel('latex_export', 'es')).toBe('Exportar LaTeX');
        expect(getFeatureLabel('latex_export', 'en')).toBe('LaTeX export');
    });

    it('falls back to the feature key for an unknown feature', () => {
        expect(getFeatureLabel('not_a_feature', 'es')).toBe('not_a_feature');
    });

    it('returns Nahuatl labels when lang is nah', () => {
        expect(getFeatureLabel('webhooks', 'nah')).toBe('Webhooks');
        expect(getFeatureLabel('latex_export', 'nah')).toMatch(/LaTeX/);
    });

    it('handles every feature key in all three languages', () => {
        for (const key of Object.keys(FEATURE_LABELS)) {
            for (const lang of ['es', 'en', 'nah'] as const) {
                expect(getFeatureLabel(key, lang)).toBeTruthy();
            }
        }
    });
});

describe('FEATURE_LABELS dict', () => {
    it('includes the canonical interest-capture features', () => {
        const expected = [
            'latex_export',
            'docx_export',
            'epub_export',
            'webhooks',
            'graph_api',
            'bulk_download',
            'search_analytics',
            'early_access',
        ];
        for (const k of expected) {
            expect(FEATURE_LABELS).toHaveProperty(k);
        }
    });

    it('every feature has all three language variants', () => {
        for (const [key, labels] of Object.entries(FEATURE_LABELS)) {
            expect(labels.es, `${key}.es missing`).toBeTruthy();
            expect(labels.en, `${key}.en missing`).toBeTruthy();
            expect(labels.nah, `${key}.nah missing`).toBeTruthy();
        }
    });
});
