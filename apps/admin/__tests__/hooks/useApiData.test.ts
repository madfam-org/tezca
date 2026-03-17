import { renderHook, waitFor, act } from '@testing-library/react';
import { useApiData } from '@/hooks/useApiData';
import { APIError } from '@/lib/api';

describe('useApiData', () => {
    it('starts in loading state with null data', () => {
        const fetchFn = vi.fn(() => new Promise<unknown>(() => {}));
        const { result } = renderHook(() => useApiData(fetchFn));
        expect(result.current.loading).toBe(true);
        expect(result.current.data).toBeNull();
        expect(result.current.error).toBeNull();
    });

    it('returns data on successful fetch', async () => {
        const mockData = { total_laws: 100, status: 'ok' };
        const fetchFn = vi.fn().mockResolvedValue(mockData);
        const { result } = renderHook(() => useApiData(fetchFn));

        await waitFor(() => expect(result.current.loading).toBe(false));
        expect(result.current.data).toEqual(mockData);
        expect(result.current.error).toBeNull();
    });

    it('returns error message from Error instance', async () => {
        const fetchFn = vi.fn().mockRejectedValue(new Error('Server error'));
        const { result } = renderHook(() => useApiData(fetchFn));

        await waitFor(() => expect(result.current.loading).toBe(false));
        expect(result.current.error).toBe('Server error');
        expect(result.current.data).toBeNull();
    });

    it('uses custom error message for non-Error rejections', async () => {
        const fetchFn = vi.fn().mockRejectedValue('string error');
        const { result } = renderHook(() => useApiData(fetchFn, 'Error personalizado'));

        await waitFor(() => expect(result.current.loading).toBe(false));
        expect(result.current.error).toBe('Error personalizado');
    });

    it('uses default error message when none provided', async () => {
        const fetchFn = vi.fn().mockRejectedValue('oops');
        const { result } = renderHook(() => useApiData(fetchFn));

        await waitFor(() => expect(result.current.loading).toBe(false));
        expect(result.current.error).toBe('Error al cargar datos');
    });

    it('refresh re-fetches and updates data', async () => {
        const fetchFn = vi.fn()
            .mockResolvedValueOnce({ value: 1 })
            .mockResolvedValueOnce({ value: 2 });

        const { result } = renderHook(() => useApiData(fetchFn));
        await waitFor(() => expect(result.current.data).toEqual({ value: 1 }));

        await act(() => result.current.refresh());
        expect(result.current.data).toEqual({ value: 2 });
        expect(fetchFn).toHaveBeenCalledTimes(2);
    });

    it('shows session expired message on APIError 401', async () => {
        const fetchFn = vi.fn().mockRejectedValue(new APIError(401, 'Unauthorized'));
        const { result } = renderHook(() => useApiData(fetchFn));

        await waitFor(() => expect(result.current.loading).toBe(false));
        expect(result.current.error).toBe('Sesión expirada. Redirigiendo al inicio de sesión...');
    });

    it('shows access denied message on APIError 403', async () => {
        const fetchFn = vi.fn().mockRejectedValue(new APIError(403, 'Forbidden'));
        const { result } = renderHook(() => useApiData(fetchFn));

        await waitFor(() => expect(result.current.loading).toBe(false));
        expect(result.current.error).toBe('Acceso denegado. Se requieren permisos de administrador.');
    });

    it('refresh clears error on retry success', async () => {
        const fetchFn = vi.fn()
            .mockRejectedValueOnce(new Error('fail'))
            .mockResolvedValueOnce({ ok: true });

        const { result } = renderHook(() => useApiData(fetchFn));
        await waitFor(() => expect(result.current.error).toBe('fail'));

        await act(() => result.current.refresh());
        expect(result.current.error).toBeNull();
        expect(result.current.data).toEqual({ ok: true });
    });
});
