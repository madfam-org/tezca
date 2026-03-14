import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

// Mock LanguageContext
vi.mock('@/components/providers/LanguageContext', () => ({
    useLang: vi.fn(() => ({ lang: 'es', setLang: vi.fn() })),
}));

// Mock lucide-react
vi.mock('lucide-react', () => ({
    Mail: ({ className }: any) => <span data-testid="mail-icon" className={className} />,
}));

import { NewsletterSignup } from '@/components/NewsletterSignup';
import { useLang } from '@/components/providers/LanguageContext';

describe('NewsletterSignup', () => {
    let fetchSpy: ReturnType<typeof vi.fn>;

    beforeEach(() => {
        vi.clearAllMocks();
        // Reset useLang to Spanish after any test that changes it
        (useLang as ReturnType<typeof vi.fn>).mockReturnValue({ lang: 'es', setLang: vi.fn() });
        fetchSpy = vi.fn();
        global.fetch = fetchSpy;
    });

    afterEach(() => {
        vi.restoreAllMocks();
    });

    // ---------------------------------------------------------------
    // 1. Renders title and description
    // ---------------------------------------------------------------
    it('renders title and description in Spanish', () => {
        render(<NewsletterSignup />);

        expect(screen.getByText('Suscríbete al boletín')).toBeInTheDocument();
        expect(screen.getByText('Recibe actualizaciones sobre nuevas leyes y cambios legislativos.')).toBeInTheDocument();
    });

    // ---------------------------------------------------------------
    // 2. Renders email input with placeholder
    // ---------------------------------------------------------------
    it('renders email input with correct placeholder', () => {
        render(<NewsletterSignup />);

        expect(screen.getByPlaceholderText('tu@correo.com')).toBeInTheDocument();
    });

    // ---------------------------------------------------------------
    // 3. Renders subscribe button
    // ---------------------------------------------------------------
    it('renders subscribe button', () => {
        render(<NewsletterSignup />);

        expect(screen.getByText('Suscribirse')).toBeInTheDocument();
    });

    // ---------------------------------------------------------------
    // 4. Submits email on form submit
    // ---------------------------------------------------------------
    it('submits email to API on form submit', async () => {
        fetchSpy.mockResolvedValue({
            ok: true,
            json: () => Promise.resolve({ status: 'subscribed' }),
        });

        render(<NewsletterSignup />);

        fireEvent.change(screen.getByLabelText('Email'), { target: { value: 'test@test.com' } });
        fireEvent.click(screen.getByText('Suscribirse'));

        await waitFor(() => {
            expect(fetchSpy).toHaveBeenCalledWith(
                expect.stringContaining('/newsletter/subscribe/'),
                expect.objectContaining({
                    method: 'POST',
                    body: JSON.stringify({ email: 'test@test.com' }),
                }),
            );
        });
    });

    // ---------------------------------------------------------------
    // 5. Shows success message
    // ---------------------------------------------------------------
    it('shows success message after successful subscription', async () => {
        fetchSpy.mockResolvedValue({
            ok: true,
            json: () => Promise.resolve({ status: 'subscribed' }),
        });

        render(<NewsletterSignup />);

        fireEvent.change(screen.getByLabelText('Email'), { target: { value: 'test@test.com' } });
        fireEvent.click(screen.getByText('Suscribirse'));

        await waitFor(() => {
            expect(screen.getByText('Suscripción exitosa.')).toBeInTheDocument();
        });
    });

    // ---------------------------------------------------------------
    // 6. Shows already subscribed message
    // ---------------------------------------------------------------
    it('shows already subscribed message', async () => {
        fetchSpy.mockResolvedValue({
            ok: true,
            json: () => Promise.resolve({ status: 'already_subscribed' }),
        });

        render(<NewsletterSignup />);

        fireEvent.change(screen.getByLabelText('Email'), { target: { value: 'existing@test.com' } });
        fireEvent.click(screen.getByText('Suscribirse'));

        await waitFor(() => {
            expect(screen.getByText('Ya estás suscrito.')).toBeInTheDocument();
        });
    });

    // ---------------------------------------------------------------
    // 7. Shows error message on API failure
    // ---------------------------------------------------------------
    it('shows error message when API returns error', async () => {
        fetchSpy.mockResolvedValue({
            ok: false,
            json: () => Promise.resolve({ error: 'Internal error' }),
        });

        render(<NewsletterSignup />);

        fireEvent.change(screen.getByLabelText('Email'), { target: { value: 'test@test.com' } });
        fireEvent.click(screen.getByText('Suscribirse'));

        await waitFor(() => {
            expect(screen.getByText('Error al suscribirse. Intenta de nuevo.')).toBeInTheDocument();
        });
    });

    // ---------------------------------------------------------------
    // 8. Shows error message on network failure
    // ---------------------------------------------------------------
    it('shows error message on network failure', async () => {
        fetchSpy.mockRejectedValue(new Error('Network error'));

        render(<NewsletterSignup />);

        fireEvent.change(screen.getByLabelText('Email'), { target: { value: 'test@test.com' } });
        fireEvent.click(screen.getByText('Suscribirse'));

        await waitFor(() => {
            expect(screen.getByText('Error al suscribirse. Intenta de nuevo.')).toBeInTheDocument();
        });
    });

    // ---------------------------------------------------------------
    // 9. Button disabled while loading
    // ---------------------------------------------------------------
    it('disables button while loading', async () => {
        fetchSpy.mockReturnValue(new Promise(() => {})); // Never resolves

        render(<NewsletterSignup />);

        fireEvent.change(screen.getByLabelText('Email'), { target: { value: 'test@test.com' } });
        fireEvent.click(screen.getByText('Suscribirse'));

        await waitFor(() => {
            expect(screen.getByText('Suscribirse').closest('button')).toBeDisabled();
        });
    });

    // ---------------------------------------------------------------
    // 10. Renders in English
    // ---------------------------------------------------------------
    it('renders in English when lang is en', () => {
        (useLang as ReturnType<typeof vi.fn>).mockReturnValue({ lang: 'en', setLang: vi.fn() });

        render(<NewsletterSignup />);

        expect(screen.getByText('Subscribe to our newsletter')).toBeInTheDocument();
        expect(screen.getByPlaceholderText('you@email.com')).toBeInTheDocument();
        expect(screen.getByText('Subscribe')).toBeInTheDocument();
    });

    // ---------------------------------------------------------------
    // 11. Renders in Nahuatl
    // ---------------------------------------------------------------
    it('renders in Nahuatl when lang is nah', () => {
        (useLang as ReturnType<typeof vi.fn>).mockReturnValue({ lang: 'nah', setLang: vi.fn() });

        render(<NewsletterSignup />);

        expect(screen.getByText('Ximomachiyoti ipan amatlahcuilōlli')).toBeInTheDocument();
        expect(screen.getByText('Ximomachiyoti')).toBeInTheDocument();
    });

    // ---------------------------------------------------------------
    // 12. Does not submit empty email
    // ---------------------------------------------------------------
    it('does not submit when email is empty', () => {
        render(<NewsletterSignup />);

        fireEvent.click(screen.getByText('Suscribirse'));

        expect(fetchSpy).not.toHaveBeenCalled();
    });

    // ---------------------------------------------------------------
    // 13. Clears email on success
    // ---------------------------------------------------------------
    it('clears email input after successful subscription', async () => {
        fetchSpy.mockResolvedValue({
            ok: true,
            json: () => Promise.resolve({ status: 'subscribed' }),
        });

        render(<NewsletterSignup />);

        const input = screen.getByLabelText('Email') as HTMLInputElement;
        fireEvent.change(input, { target: { value: 'test@test.com' } });
        fireEvent.click(screen.getByText('Suscribirse'));

        await waitFor(() => {
            expect(input.value).toBe('');
        });
    });

    // ---------------------------------------------------------------
    // 14. Status message has proper role
    // ---------------------------------------------------------------
    it('status message has proper aria role', async () => {
        fetchSpy.mockResolvedValue({
            ok: true,
            json: () => Promise.resolve({ status: 'subscribed' }),
        });

        render(<NewsletterSignup />);

        fireEvent.change(screen.getByLabelText('Email'), { target: { value: 'test@test.com' } });
        fireEvent.click(screen.getByText('Suscribirse'));

        await waitFor(() => {
            const status = screen.getByRole('status');
            expect(status).toBeInTheDocument();
            expect(status.textContent).toBe('Suscripción exitosa.');
        });
    });
});
