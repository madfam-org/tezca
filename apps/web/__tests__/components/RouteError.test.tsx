import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';

// Mock next/link
vi.mock('next/link', () => ({
    default: ({ children, href, ...props }: any) => <a href={href} {...props}>{children}</a>,
}));

// Mock LanguageContext
vi.mock('@/components/providers/LanguageContext', () => ({
    useLang: vi.fn(() => ({ lang: 'es', setLang: vi.fn() })),
}));

// Mock Sentry
vi.mock('@/lib/sentry', () => ({
    captureError: vi.fn(),
}));

import { RouteError } from '@/components/RouteError';
import { useLang } from '@/components/providers/LanguageContext';
import { captureError } from '@/lib/sentry';

const MESSAGES = {
    es: { title: 'Error al cargar la página', message: 'Ocurrió un error inesperado.' },
    en: { title: 'Error loading page', message: 'An unexpected error occurred.' },
    nah: { title: 'Ahmo omochīuh in tlacuīlolli', message: 'Ahmo tlamachiltia.' },
};

const FALLBACK_LABEL = {
    es: 'Volver al inicio',
    en: 'Back to home',
    nah: 'Ximocuepa',
};

describe('RouteError', () => {
    const mockReset = vi.fn();
    const testError = Object.assign(new Error('Test error'), { digest: 'abc123' });

    beforeEach(() => {
        vi.clearAllMocks();
        (useLang as ReturnType<typeof vi.fn>).mockReturnValue({ lang: 'es', setLang: vi.fn() });
    });

    // ---------------------------------------------------------------
    // 1. Renders error title
    // ---------------------------------------------------------------
    it('renders error title in Spanish', () => {
        render(
            <RouteError
                error={testError}
                reset={mockReset}
                messages={MESSAGES}
                fallbackHref="/"
                fallbackLabel={FALLBACK_LABEL}
            />,
        );

        expect(screen.getByText('Error al cargar la página')).toBeInTheDocument();
    });

    // ---------------------------------------------------------------
    // 2. Renders error message
    // ---------------------------------------------------------------
    it('renders error message', () => {
        render(
            <RouteError
                error={testError}
                reset={mockReset}
                messages={MESSAGES}
                fallbackHref="/"
                fallbackLabel={FALLBACK_LABEL}
            />,
        );

        expect(screen.getByText('Ocurrió un error inesperado.')).toBeInTheDocument();
    });

    // ---------------------------------------------------------------
    // 3. Renders retry button
    // ---------------------------------------------------------------
    it('renders retry button with correct label', () => {
        render(
            <RouteError
                error={testError}
                reset={mockReset}
                messages={MESSAGES}
                fallbackHref="/"
                fallbackLabel={FALLBACK_LABEL}
            />,
        );

        expect(screen.getByText('Reintentar')).toBeInTheDocument();
    });

    // ---------------------------------------------------------------
    // 4. Retry button calls reset
    // ---------------------------------------------------------------
    it('calls reset when retry button is clicked', () => {
        render(
            <RouteError
                error={testError}
                reset={mockReset}
                messages={MESSAGES}
                fallbackHref="/"
                fallbackLabel={FALLBACK_LABEL}
            />,
        );

        fireEvent.click(screen.getByText('Reintentar'));
        expect(mockReset).toHaveBeenCalledOnce();
    });

    // ---------------------------------------------------------------
    // 5. Renders fallback link
    // ---------------------------------------------------------------
    it('renders fallback link with correct href and label', () => {
        render(
            <RouteError
                error={testError}
                reset={mockReset}
                messages={MESSAGES}
                fallbackHref="/"
                fallbackLabel={FALLBACK_LABEL}
            />,
        );

        const link = screen.getByText('Volver al inicio');
        expect(link).toBeInTheDocument();
        expect(link.closest('a')?.getAttribute('href')).toBe('/');
    });

    // ---------------------------------------------------------------
    // 6. Shows error digest
    // ---------------------------------------------------------------
    it('shows error digest when present', () => {
        render(
            <RouteError
                error={testError}
                reset={mockReset}
                messages={MESSAGES}
                fallbackHref="/"
                fallbackLabel={FALLBACK_LABEL}
            />,
        );

        expect(screen.getByText('abc123')).toBeInTheDocument();
    });

    // ---------------------------------------------------------------
    // 7. Hides digest when not present
    // ---------------------------------------------------------------
    it('hides digest when error has no digest', () => {
        const noDigestError = new Error('No digest');
        render(
            <RouteError
                error={noDigestError as any}
                reset={mockReset}
                messages={MESSAGES}
                fallbackHref="/"
                fallbackLabel={FALLBACK_LABEL}
            />,
        );

        // No monospace digest text
        expect(screen.queryByText('abc123')).not.toBeInTheDocument();
    });

    // ---------------------------------------------------------------
    // 8. Reports error to Sentry
    // ---------------------------------------------------------------
    it('reports error to Sentry on mount', () => {
        render(
            <RouteError
                error={testError}
                reset={mockReset}
                messages={MESSAGES}
                fallbackHref="/"
                fallbackLabel={FALLBACK_LABEL}
            />,
        );

        expect(captureError).toHaveBeenCalledWith(testError, { digest: 'abc123' });
    });

    // ---------------------------------------------------------------
    // 9. English labels
    // ---------------------------------------------------------------
    it('renders in English when lang is en', () => {
        (useLang as ReturnType<typeof vi.fn>).mockReturnValue({ lang: 'en', setLang: vi.fn() });

        render(
            <RouteError
                error={testError}
                reset={mockReset}
                messages={MESSAGES}
                fallbackHref="/"
                fallbackLabel={FALLBACK_LABEL}
            />,
        );

        expect(screen.getByText('Error loading page')).toBeInTheDocument();
        expect(screen.getByText('Retry')).toBeInTheDocument();
        expect(screen.getByText('Back to home')).toBeInTheDocument();
    });

    // ---------------------------------------------------------------
    // 10. Nahuatl labels
    // ---------------------------------------------------------------
    it('renders in Nahuatl when lang is nah', () => {
        (useLang as ReturnType<typeof vi.fn>).mockReturnValue({ lang: 'nah', setLang: vi.fn() });

        render(
            <RouteError
                error={testError}
                reset={mockReset}
                messages={MESSAGES}
                fallbackHref="/"
                fallbackLabel={FALLBACK_LABEL}
            />,
        );

        expect(screen.getByText('Ahmo omochīuh in tlacuīlolli')).toBeInTheDocument();
        expect(screen.getByText('Occeppa')).toBeInTheDocument();
        expect(screen.getByText('Ximocuepa')).toBeInTheDocument();
    });

    // ---------------------------------------------------------------
    // 11. Custom fallback href
    // ---------------------------------------------------------------
    it('uses custom fallback href', () => {
        render(
            <RouteError
                error={testError}
                reset={mockReset}
                messages={MESSAGES}
                fallbackHref="/leyes"
                fallbackLabel={FALLBACK_LABEL}
            />,
        );

        const link = screen.getByText('Volver al inicio').closest('a');
        expect(link?.getAttribute('href')).toBe('/leyes');
    });
});
