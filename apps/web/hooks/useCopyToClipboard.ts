'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { COPY_FEEDBACK_DURATION_MS } from '@/lib/constants';

interface UseCopyToClipboardResult {
    copied: boolean;
    copy: (value: string) => Promise<boolean>;
    /** Manually clear the `copied` flag (e.g. when unmounting an inline UI). */
    reset: () => void;
}

/**
 * Wraps `navigator.clipboard.writeText` with a transient `copied` flag that
 * auto-clears after COPY_FEEDBACK_DURATION_MS. Falls back to the legacy
 * `document.execCommand('copy')` path when the clipboard API is unavailable
 * (older Safari, embedded webviews).
 *
 * Replaces the duplicated `setTimeout(() => setCopied(false), 2000)` pattern
 * that used to live in AlertButton, ShareButtons, ComparisonToolbar, and
 * ArticleViewer. Centralizing here also lets us audit clipboard interactions
 * from a single place if we ever need to add telemetry or guard against
 * untrusted callers.
 *
 * Returns `false` from `copy()` when the write failed, so callers can show a
 * different affordance for the rare error case.
 */
export function useCopyToClipboard(
    durationMs: number = COPY_FEEDBACK_DURATION_MS,
): UseCopyToClipboardResult {
    const [copied, setCopied] = useState(false);
    const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

    const reset = useCallback(() => {
        if (timeoutRef.current) {
            clearTimeout(timeoutRef.current);
            timeoutRef.current = null;
        }
        setCopied(false);
    }, []);

    const copy = useCallback(async (value: string): Promise<boolean> => {
        let ok = false;
        try {
            if (typeof navigator !== 'undefined' && navigator.clipboard?.writeText) {
                await navigator.clipboard.writeText(value);
                ok = true;
            } else if (typeof document !== 'undefined') {
                // Legacy fallback for non-secure contexts and very old browsers.
                const textarea = document.createElement('textarea');
                textarea.value = value;
                textarea.setAttribute('readonly', '');
                textarea.style.position = 'absolute';
                textarea.style.left = '-9999px';
                document.body.appendChild(textarea);
                textarea.select();
                ok = document.execCommand('copy');
                document.body.removeChild(textarea);
            }
        } catch {
            ok = false;
        }

        if (!ok) return false;

        setCopied(true);
        if (timeoutRef.current) clearTimeout(timeoutRef.current);
        timeoutRef.current = setTimeout(() => {
            setCopied(false);
            timeoutRef.current = null;
        }, durationMs);
        return true;
    }, [durationMs]);

    // Clear pending timeout on unmount so we don't setState on a dead component.
    useEffect(() => {
        return () => {
            if (timeoutRef.current) clearTimeout(timeoutRef.current);
        };
    }, []);

    return { copied, copy, reset };
}
