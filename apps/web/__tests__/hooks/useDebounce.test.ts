import { renderHook, act } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { useDebounce } from '@/hooks/useDebounce';

describe('useDebounce', () => {
    beforeEach(() => {
        vi.useFakeTimers();
    });

    afterEach(() => {
        vi.useRealTimers();
    });

    it('returns the initial value immediately', () => {
        const { result } = renderHook(() => useDebounce('hello', 300));
        expect(result.current).toBe('hello');
    });

    it('updates the value after the specified delay', () => {
        const { result, rerender } = renderHook(
            ({ value, delay }) => useDebounce(value, delay),
            { initialProps: { value: 'hello', delay: 500 } }
        );

        rerender({ value: 'world', delay: 500 });
        expect(result.current).toBe('hello');

        act(() => {
            vi.advanceTimersByTime(500);
        });
        expect(result.current).toBe('world');
    });

    it('resets the timer when value changes before delay elapses', () => {
        const { result, rerender } = renderHook(
            ({ value }) => useDebounce(value, 300),
            { initialProps: { value: 'a' } }
        );

        rerender({ value: 'b' });
        act(() => {
            vi.advanceTimersByTime(200);
        });

        // Change again before the 300ms elapses
        rerender({ value: 'c' });
        act(() => {
            vi.advanceTimersByTime(200);
        });
        // 'b' was never applied because timer was reset
        expect(result.current).toBe('a');

        act(() => {
            vi.advanceTimersByTime(100);
        });
        expect(result.current).toBe('c');
    });
});
