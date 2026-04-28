import { describe, expect, it } from 'vitest';

import {
    CATEGORY_COLORS,
    CATEGORY_LABELS,
    DEFAULT_COLOR,
    TIER_COLORS,
    edgeSize,
    getCategoryColor,
    getNodeColor,
    getNodeLabel,
    getTierColor,
    getUniqueCategories,
    getUniqueStates,
    nodeSize,
} from '@/components/graph/graphConstants';

describe('getCategoryColor', () => {
    it('returns the registered color for known category', () => {
        expect(getCategoryColor('fiscal')).toBe(CATEGORY_COLORS.fiscal);
        expect(getCategoryColor('penal')).toBe(CATEGORY_COLORS.penal);
    });

    it('returns DEFAULT_COLOR for null category', () => {
        expect(getCategoryColor(null)).toBe(DEFAULT_COLOR);
    });

    it('returns DEFAULT_COLOR for unknown category', () => {
        expect(getCategoryColor('not_a_category')).toBe(DEFAULT_COLOR);
    });
});

describe('getTierColor', () => {
    it('returns the registered color for known tier', () => {
        expect(getTierColor('federal')).toBe(TIER_COLORS.federal);
        expect(getTierColor('state')).toBe(TIER_COLORS.state);
        expect(getTierColor('municipal')).toBe(TIER_COLORS.municipal);
    });

    it('returns DEFAULT_COLOR for null tier', () => {
        expect(getTierColor(null)).toBe(DEFAULT_COLOR);
    });

    it('returns DEFAULT_COLOR for unknown tier', () => {
        expect(getTierColor('imperial')).toBe(DEFAULT_COLOR);
    });
});

describe('getNodeColor', () => {
    it('uses category color when colorMode=category', () => {
        expect(getNodeColor('category', 'fiscal', 'federal')).toBe(CATEGORY_COLORS.fiscal);
    });

    it('uses tier color when colorMode=tier', () => {
        expect(getNodeColor('tier', 'fiscal', 'federal')).toBe(TIER_COLORS.federal);
    });

    it('falls back gracefully when both are null', () => {
        expect(getNodeColor('category', null, null)).toBe(DEFAULT_COLOR);
        expect(getNodeColor('tier', null, null)).toBe(DEFAULT_COLOR);
    });
});

describe('nodeSize', () => {
    it('clamps to a minimum of 6', () => {
        expect(nodeSize(0)).toBe(6);
        expect(nodeSize(1)).toBe(6);
    });

    it('grows with the log of refCount', () => {
        const small = nodeSize(2);
        const big = nodeSize(100);
        expect(big).toBeGreaterThan(small);
    });

    it('clamps to a maximum of 30', () => {
        expect(nodeSize(1_000_000)).toBeLessThanOrEqual(30);
    });
});

describe('edgeSize', () => {
    it('clamps to a minimum of 1', () => {
        expect(edgeSize(0)).toBe(1);
        expect(edgeSize(-5)).toBe(1);
    });

    it('clamps to a maximum of 4', () => {
        expect(edgeSize(100)).toBe(4);
    });

    it('scales linearly between bounds', () => {
        expect(edgeSize(2)).toBe(1);
        expect(edgeSize(4)).toBe(2);
        expect(edgeSize(6)).toBe(3);
    });
});

describe('getUniqueCategories', () => {
    it('returns deduplicated sorted categories', () => {
        const nodes = [
            { category: 'fiscal' },
            { category: 'penal' },
            { category: 'fiscal' },
            { category: null },
        ];
        expect(getUniqueCategories(nodes)).toEqual(['fiscal', 'penal']);
    });

    it('handles empty input', () => {
        expect(getUniqueCategories([])).toEqual([]);
    });

    it('skips null entries', () => {
        expect(getUniqueCategories([{ category: null }, { category: null }])).toEqual([]);
    });
});

describe('getUniqueStates', () => {
    it('returns deduplicated sorted states', () => {
        const nodes = [
            { state: 'Jalisco' },
            { state: 'CDMX' },
            { state: 'Jalisco' },
            { state: null },
        ];
        expect(getUniqueStates(nodes)).toEqual(['CDMX', 'Jalisco']);
    });
});

describe('getNodeLabel', () => {
    it('returns empty string when zoomed out far', () => {
        expect(getNodeLabel('Short', 'Full Name', 2)).toBe('');
    });

    it('returns shortName at mid-zoom when present', () => {
        expect(getNodeLabel('Short', 'Long Full Name', 1)).toBe('Short');
    });

    it('truncates long fullName at mid-zoom when no shortName', () => {
        const long = 'A'.repeat(40);
        const out = getNodeLabel(null, long, 1);
        expect(out.endsWith('...')).toBe(true);
        expect(out.length).toBeLessThanOrEqual(28);
    });

    it('returns full name when zoomed in', () => {
        expect(getNodeLabel('Short', 'Full Name', 0.3)).toBe('Full Name');
    });
});

describe('CATEGORY_LABELS dict', () => {
    it('every category has all three language variants', () => {
        for (const [key, labels] of Object.entries(CATEGORY_LABELS)) {
            expect(labels.es, `${key}.es missing`).toBeTruthy();
            expect(labels.en, `${key}.en missing`).toBeTruthy();
            expect(labels.nah, `${key}.nah missing`).toBeTruthy();
        }
    });
});
