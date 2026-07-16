'use client';

import { useState, useCallback, useEffect, useSyncExternalStore } from 'react';

const SIZES = ['text-sm', 'text-base', 'text-lg'] as const;
type FontSize = (typeof SIZES)[number];
const STORAGE_KEY = 'preferred-font-size';

interface FontSizeControlProps {
    onChange: (size: FontSize) => void;
}

export type { FontSize };

function readStoredSize(): FontSize {
    if (typeof window === 'undefined') return 'text-base';
    if (typeof localStorage === 'undefined' || typeof localStorage.getItem !== 'function') return 'text-base';
    try {
        const stored = localStorage.getItem(STORAGE_KEY) as FontSize | null;
        return stored && SIZES.includes(stored) ? stored : 'text-base';
    } catch {
        return 'text-base';
    }
}

export function FontSizeControl({ onChange }: FontSizeControlProps) {
    const subscribe = useCallback(() => () => {}, []);
    const size = useSyncExternalStore(subscribe, readStoredSize, () => 'text-base' as FontSize);
    const [, setTick] = useState(0);

    const handleChange = (newSize: FontSize) => {
        try {
            if (typeof localStorage !== 'undefined' && typeof localStorage.setItem === 'function') {
                localStorage.setItem(STORAGE_KEY, newSize);
            }
        } catch {
            // localStorage unavailable
        }
        setTick((t) => t + 1);
        onChange(newSize);
    };

    // Sync stored preference on mount (client only)
    useEffect(() => {
        if (size !== 'text-base') {
            onChange(size);
        }
    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    return (
        <div className="inline-flex items-center rounded-md border border-border bg-muted/50 p-0.5" role="group" aria-label="Font size">
            <button
                onClick={() => handleChange('text-sm')}
                className={`px-2 py-1 text-xs rounded transition-colors ${
                    size === 'text-sm' ? 'bg-primary text-primary-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground'
                }`}
                aria-label="Small text"
                aria-pressed={size === 'text-sm'}
            >
                A-
            </button>
            <button
                onClick={() => handleChange('text-base')}
                className={`px-2 py-1 text-sm rounded transition-colors ${
                    size === 'text-base' ? 'bg-primary text-primary-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground'
                }`}
                aria-label="Normal text"
                aria-pressed={size === 'text-base'}
            >
                A
            </button>
            <button
                onClick={() => handleChange('text-lg')}
                className={`px-2 py-1 text-base rounded transition-colors ${
                    size === 'text-lg' ? 'bg-primary text-primary-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground'
                }`}
                aria-label="Large text"
                aria-pressed={size === 'text-lg'}
            >
                A+
            </button>
        </div>
    );
}
