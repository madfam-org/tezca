import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { defaultAuthState, mockAuth } from '../../helpers/auth-mock';

// Mock LanguageContext
vi.mock('@/components/providers/LanguageContext', () => ({
    useLang: vi.fn(() => ({ lang: 'es', setLang: vi.fn() })),
}));

// Mock AuthContext
const mockUseAuth = vi.fn(() => defaultAuthState);
vi.mock('@/components/providers/AuthContext', () => ({
    useAuth: (...args: any[]) => mockUseAuth(...args),
}));

// Mock auth-token
vi.mock('@/lib/auth-token', () => ({
    getAuthToken: vi.fn(() => 'test-token'),
}));

// Mock @tezca/lib
vi.mock('@tezca/lib', () => ({
    cn: (...classes: any[]) => classes.filter(Boolean).join(' '),
}));

// Mock lucide-react
vi.mock('lucide-react', () => ({
    Bell: ({ className }: any) => <span data-testid="bell-icon" className={className} />,
    BellOff: ({ className }: any) => <span data-testid="bell-off-icon" className={className} />,
    Check: ({ className }: any) => <span data-testid="check-icon" className={className} />,
}));

const mockGetAlerts = vi.fn();
const mockCreateAlert = vi.fn();
const mockDeleteAlert = vi.fn();

vi.mock('@/lib/api', () => ({
    api: {
        getAlerts: (...args: any[]) => mockGetAlerts(...args),
        createAlert: (...args: any[]) => mockCreateAlert(...args),
        deleteAlert: (...args: any[]) => mockDeleteAlert(...args),
    },
}));

import { AlertButton } from '@/components/laws/AlertButton';
import { useLang } from '@/components/providers/LanguageContext';

describe('AlertButton', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        mockUseAuth.mockReturnValue(defaultAuthState);
        mockGetAlerts.mockResolvedValue({ alerts: [] });
        mockCreateAlert.mockResolvedValue({ id: 1, law_id: 'cpeum', alert_type: 'law_updated' });
        mockDeleteAlert.mockResolvedValue({});
        (useLang as ReturnType<typeof vi.fn>).mockReturnValue({ lang: 'es', setLang: vi.fn() });
    });

    // ---------------------------------------------------------------
    // 1. Shows disabled state when not authenticated
    // ---------------------------------------------------------------
    it('shows disabled button when not authenticated', () => {
        render(<AlertButton lawId="cpeum" />);

        const button = screen.getByText('Seguir esta ley').closest('button');
        expect(button).toBeDisabled();
    });

    // ---------------------------------------------------------------
    // 2. Shows title tooltip for unauthenticated
    // ---------------------------------------------------------------
    it('shows login required title when not authenticated', () => {
        render(<AlertButton lawId="cpeum" />);

        const button = screen.getByText('Seguir esta ley').closest('button');
        expect(button?.getAttribute('title')).toBe('Inicia sesión para recibir alertas');
    });

    // ---------------------------------------------------------------
    // 3. Shows watch button when authenticated and not watching
    // ---------------------------------------------------------------
    it('shows watch button when authenticated and not watching', async () => {
        mockUseAuth.mockReturnValue(mockAuth({ isAuthenticated: true, tier: 'pro' }));
        render(<AlertButton lawId="cpeum" />);

        await waitFor(() => {
            expect(screen.getByText('Seguir esta ley')).toBeInTheDocument();
        });
    });

    // ---------------------------------------------------------------
    // 4. Creates alert on click
    // ---------------------------------------------------------------
    it('creates alert when watch button is clicked', async () => {
        mockUseAuth.mockReturnValue(mockAuth({ isAuthenticated: true, tier: 'pro' }));
        render(<AlertButton lawId="cpeum" />);

        await waitFor(() => {
            expect(screen.getByText('Seguir esta ley')).toBeInTheDocument();
        });

        await act(async () => {
            fireEvent.click(screen.getByText('Seguir esta ley'));
        });

        expect(mockCreateAlert).toHaveBeenCalledWith('test-token', {
            law_id: 'cpeum',
            alert_type: 'law_updated',
        });
    });

    // ---------------------------------------------------------------
    // 5. Shows "saved" confirmation briefly (uses fake timers)
    // ---------------------------------------------------------------
    it('shows "Alerta guardada" briefly after creating alert', async () => {
        vi.useFakeTimers({ shouldAdvanceTime: true });

        mockUseAuth.mockReturnValue(mockAuth({ isAuthenticated: true, tier: 'pro' }));
        render(<AlertButton lawId="cpeum" />);

        await waitFor(() => {
            expect(screen.getByText('Seguir esta ley')).toBeInTheDocument();
        });

        await act(async () => {
            fireEvent.click(screen.getByText('Seguir esta ley'));
        });

        expect(screen.getByText('Alerta guardada')).toBeInTheDocument();

        // After timeout, it should switch to "Dejar de seguir"
        act(() => {
            vi.advanceTimersByTime(2000);
        });

        expect(screen.queryByText('Alerta guardada')).not.toBeInTheDocument();
        expect(screen.getByText('Dejar de seguir')).toBeInTheDocument();

        vi.useRealTimers();
    });

    // ---------------------------------------------------------------
    // 6. Shows watching state when alert already exists
    // ---------------------------------------------------------------
    it('shows "Dejar de seguir" when alert already exists for law', async () => {
        mockUseAuth.mockReturnValue(mockAuth({ isAuthenticated: true, tier: 'pro' }));
        mockGetAlerts.mockResolvedValue({
            alerts: [{ id: 42, law_id: 'cpeum', alert_type: 'law_updated' }],
        });

        render(<AlertButton lawId="cpeum" />);

        await waitFor(() => {
            expect(screen.getByText('Dejar de seguir')).toBeInTheDocument();
        });
    });

    // ---------------------------------------------------------------
    // 7. Deletes alert on unwatch
    // ---------------------------------------------------------------
    it('deletes alert when unwatch is clicked', async () => {
        mockUseAuth.mockReturnValue(mockAuth({ isAuthenticated: true, tier: 'pro' }));
        mockGetAlerts.mockResolvedValue({
            alerts: [{ id: 42, law_id: 'cpeum', alert_type: 'law_updated' }],
        });

        render(<AlertButton lawId="cpeum" />);

        await waitFor(() => {
            expect(screen.getByText('Dejar de seguir')).toBeInTheDocument();
        });

        await act(async () => {
            fireEvent.click(screen.getByText('Dejar de seguir'));
        });

        expect(mockDeleteAlert).toHaveBeenCalledWith('test-token', 42);
    });

    // ---------------------------------------------------------------
    // 8. After unwatching, shows watch button again
    // ---------------------------------------------------------------
    it('shows watch button again after unwatching', async () => {
        mockUseAuth.mockReturnValue(mockAuth({ isAuthenticated: true, tier: 'pro' }));
        mockGetAlerts.mockResolvedValue({
            alerts: [{ id: 42, law_id: 'cpeum', alert_type: 'law_updated' }],
        });

        render(<AlertButton lawId="cpeum" />);

        await waitFor(() => {
            expect(screen.getByText('Dejar de seguir')).toBeInTheDocument();
        });

        await act(async () => {
            fireEvent.click(screen.getByText('Dejar de seguir'));
        });

        expect(screen.getByText('Seguir esta ley')).toBeInTheDocument();
    });

    // ---------------------------------------------------------------
    // 9. English labels
    // ---------------------------------------------------------------
    it('renders English labels when lang is en', () => {
        (useLang as ReturnType<typeof vi.fn>).mockReturnValue({ lang: 'en', setLang: vi.fn() });
        render(<AlertButton lawId="cpeum" />);

        expect(screen.getByText('Watch this law')).toBeInTheDocument();
    });

    // ---------------------------------------------------------------
    // 10. Nahuatl labels
    // ---------------------------------------------------------------
    it('renders Nahuatl labels when lang is nah', () => {
        (useLang as ReturnType<typeof vi.fn>).mockReturnValue({ lang: 'nah', setLang: vi.fn() });
        render(<AlertButton lawId="cpeum" />);

        expect(screen.getByText('Xictlachili in tenahuatilli')).toBeInTheDocument();
    });

    // ---------------------------------------------------------------
    // 11. Does not fetch alerts when not authenticated
    // ---------------------------------------------------------------
    it('does not fetch alerts when not authenticated', () => {
        render(<AlertButton lawId="cpeum" />);
        expect(mockGetAlerts).not.toHaveBeenCalled();
    });

    // ---------------------------------------------------------------
    // 12. Custom className is applied
    // ---------------------------------------------------------------
    it('applies custom className', () => {
        render(<AlertButton lawId="cpeum" className="my-custom-class" />);

        const button = screen.getByText('Seguir esta ley').closest('button');
        expect(button?.className).toContain('my-custom-class');
    });
});
