'use client';

import { useEffect, useState, useCallback } from 'react';
import { APIError } from '@/lib/api';

interface UseApiDataResult<T> {
    data: T | null;
    loading: boolean;
    error: string | null;
    refresh: () => Promise<void>;
}

/**
 * Generic hook for fetching API data with loading/error states and refresh.
 */
export function useApiData<T>(
    fetchFn: () => Promise<T>,
    errorMessage = 'Error al cargar datos',
): UseApiDataResult<T> {
    const [data, setData] = useState<T | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const refresh = useCallback(async () => {
        setLoading(true);
        setError(null);
        try {
            const result = await fetchFn();
            setData(result);
        } catch (err) {
            if (err instanceof APIError && err.status === 401) {
                setError('Sesión expirada. Redirigiendo al inicio de sesión...');
            } else if (err instanceof APIError && err.status === 403) {
                setError('Acceso denegado. Se requieren permisos de administrador.');
            } else {
                setError(err instanceof Error ? err.message : errorMessage);
            }
        } finally {
            setLoading(false);
        }
    }, [fetchFn, errorMessage]);

    useEffect(() => {
        refresh();
    }, [refresh]);

    return { data, loading, error, refresh };
}
