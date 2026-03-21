import { describe, it, expect } from 'vitest';
import { cn } from '@/lib/utils';

describe('cn', () => {
    it('merges class names', () => {
        expect(cn('foo', 'bar')).toBe('foo bar');
    });

    it('handles conditional classes', () => {
        const result = cn('base', false && 'hidden', 'visible');
        expect(result).toBe('base visible');
    });

    it('deduplicates conflicting Tailwind classes', () => {
        const result = cn('px-4', 'px-2');
        expect(result).toBe('px-2');
    });
});
