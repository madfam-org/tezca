import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { defaultAuthState, mockAuth } from '../helpers/auth-mock';

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
const mockGetAuthToken = vi.fn(() => 'test-token');
vi.mock('@/lib/auth-token', () => ({
    getAuthToken: () => mockGetAuthToken(),
}));

// Mock @tezca/lib
vi.mock('@tezca/lib', () => ({
    cn: (...classes: any[]) => classes.filter(Boolean).join(' '),
}));

// Mock lucide-react
vi.mock('lucide-react', () => ({
    Bell: ({ className }: any) => <span data-testid="bell-icon" className={className} />,
}));

const mockGetNotifications = vi.fn();
const mockMarkNotificationsRead = vi.fn();

vi.mock('@/lib/api', () => ({
    api: {
        getNotifications: (...args: any[]) => mockGetNotifications(...args),
        markNotificationsRead: (...args: any[]) => mockMarkNotificationsRead(...args),
    },
}));

import { NotificationBell } from '@/components/NotificationBell';
import { useLang } from '@/components/providers/LanguageContext';

describe('NotificationBell', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        mockUseAuth.mockReturnValue(defaultAuthState);
        mockGetNotifications.mockResolvedValue({ total: 0, unread: 0, notifications: [] });
        mockMarkNotificationsRead.mockResolvedValue({});
        mockGetAuthToken.mockReturnValue('test-token');
    });

    // ---------------------------------------------------------------
    // 1. Returns null when not authenticated
    // ---------------------------------------------------------------
    it('renders nothing when user is not authenticated', () => {
        const { container } = render(<NotificationBell />);
        expect(container.innerHTML).toBe('');
    });

    // ---------------------------------------------------------------
    // 2. Renders bell button when authenticated
    // ---------------------------------------------------------------
    it('renders bell button when authenticated', () => {
        mockUseAuth.mockReturnValue(mockAuth({ isAuthenticated: true, tier: 'essentials' }));
        render(<NotificationBell />);

        expect(screen.getByLabelText('Notificaciones')).toBeInTheDocument();
    });

    // ---------------------------------------------------------------
    // 3. Shows unread badge
    // ---------------------------------------------------------------
    it('shows unread badge with count', async () => {
        mockUseAuth.mockReturnValue(mockAuth({ isAuthenticated: true, tier: 'academic' }));
        mockGetNotifications.mockResolvedValue({
            total: 3,
            unread: 3,
            notifications: [
                { id: 1, title: 'Test', body: 'Body', link: '/test', is_read: false, created_at: '2026-03-01' },
                { id: 2, title: 'Test 2', body: 'Body 2', link: '/test2', is_read: false, created_at: '2026-03-01' },
                { id: 3, title: 'Test 3', body: 'Body 3', link: '/test3', is_read: false, created_at: '2026-03-01' },
            ],
        });

        render(<NotificationBell />);

        await waitFor(() => {
            expect(screen.getByText('3')).toBeInTheDocument();
        });
    });

    // ---------------------------------------------------------------
    // 4. Shows "9+" for more than 9 unread
    // ---------------------------------------------------------------
    it('shows "9+" when unread count exceeds 9', async () => {
        mockUseAuth.mockReturnValue(mockAuth({ isAuthenticated: true, tier: 'academic' }));
        mockGetNotifications.mockResolvedValue({
            total: 15,
            unread: 15,
            notifications: Array.from({ length: 15 }, (_, i) => ({
                id: i + 1,
                title: `N${i}`,
                body: 'Body',
                link: '#',
                is_read: false,
                created_at: '2026-03-01',
            })),
        });

        render(<NotificationBell />);

        await waitFor(() => {
            expect(screen.getByText('9+')).toBeInTheDocument();
        });
    });

    // ---------------------------------------------------------------
    // 5. Opens dropdown on click
    // ---------------------------------------------------------------
    it('opens dropdown on click', async () => {
        mockUseAuth.mockReturnValue(mockAuth({ isAuthenticated: true, tier: 'academic' }));

        render(<NotificationBell />);

        // Wait for initial fetch
        await waitFor(() => {
            expect(mockGetNotifications).toHaveBeenCalled();
        });

        fireEvent.click(screen.getByLabelText('Notificaciones'));
        expect(screen.getByText('Notificaciones', { selector: 'h3' })).toBeInTheDocument();
    });

    // ---------------------------------------------------------------
    // 6. Shows empty state
    // ---------------------------------------------------------------
    it('shows empty state message in dropdown', async () => {
        mockUseAuth.mockReturnValue(mockAuth({ isAuthenticated: true, tier: 'academic' }));

        render(<NotificationBell />);

        await waitFor(() => {
            expect(mockGetNotifications).toHaveBeenCalled();
        });

        fireEvent.click(screen.getByLabelText('Notificaciones'));
        expect(screen.getByText('No hay notificaciones.')).toBeInTheDocument();
    });

    // ---------------------------------------------------------------
    // 7. Shows notification items
    // ---------------------------------------------------------------
    it('shows notification items in dropdown', async () => {
        mockUseAuth.mockReturnValue(mockAuth({ isAuthenticated: true, tier: 'academic' }));
        mockGetNotifications.mockResolvedValue({
            total: 1,
            unread: 1,
            notifications: [
                { id: 1, title: 'Ley actualizada', body: 'CPEUM modificada', link: '/leyes/cpeum', is_read: false, created_at: '2026-03-01T12:00:00Z' },
            ],
        });

        render(<NotificationBell />);

        await waitFor(() => {
            expect(mockGetNotifications).toHaveBeenCalled();
        });

        fireEvent.click(screen.getByLabelText('Notificaciones'));

        await waitFor(() => {
            expect(screen.getByText('Ley actualizada')).toBeInTheDocument();
            expect(screen.getByText('CPEUM modificada')).toBeInTheDocument();
        });
    });

    // ---------------------------------------------------------------
    // 8. Shows mark-all-read button when unread > 0
    // ---------------------------------------------------------------
    it('shows mark-all-read button when there are unread notifications', async () => {
        mockUseAuth.mockReturnValue(mockAuth({ isAuthenticated: true, tier: 'academic' }));
        mockGetNotifications.mockResolvedValue({
            total: 1,
            unread: 1,
            notifications: [
                { id: 1, title: 'Test', body: 'Body', link: '#', is_read: false, created_at: '2026-03-01' },
            ],
        });

        render(<NotificationBell />);

        await waitFor(() => {
            expect(screen.getByText('1')).toBeInTheDocument();
        });

        fireEvent.click(screen.getByLabelText('Notificaciones'));

        expect(screen.getByText('Marcar todo como leído')).toBeInTheDocument();
    });

    // ---------------------------------------------------------------
    // 9. Mark all read calls API
    // ---------------------------------------------------------------
    it('calls markNotificationsRead when mark-all-read is clicked', async () => {
        mockUseAuth.mockReturnValue(mockAuth({ isAuthenticated: true, tier: 'academic' }));
        mockGetNotifications.mockResolvedValue({
            total: 1,
            unread: 1,
            notifications: [
                { id: 1, title: 'Test', body: 'Body', link: '#', is_read: false, created_at: '2026-03-01' },
            ],
        });

        render(<NotificationBell />);

        await waitFor(() => {
            expect(screen.getByText('1')).toBeInTheDocument();
        });

        fireEvent.click(screen.getByLabelText('Notificaciones'));

        await act(async () => {
            fireEvent.click(screen.getByText('Marcar todo como leído'));
        });

        expect(mockMarkNotificationsRead).toHaveBeenCalledWith('test-token');
    });

    // ---------------------------------------------------------------
    // 10. Does not show unread badge when unread is 0
    // ---------------------------------------------------------------
    it('does not show unread badge when count is 0', async () => {
        mockUseAuth.mockReturnValue(mockAuth({ isAuthenticated: true, tier: 'academic' }));

        render(<NotificationBell />);

        await waitFor(() => {
            expect(mockGetNotifications).toHaveBeenCalled();
        });

        // No badge number should be visible
        expect(screen.queryByText('0')).not.toBeInTheDocument();
    });

    // ---------------------------------------------------------------
    // 11. English label when lang is 'en'
    // ---------------------------------------------------------------
    it('shows English labels when lang is en', () => {
        mockUseAuth.mockReturnValue(mockAuth({ isAuthenticated: true, tier: 'academic' }));
        (useLang as ReturnType<typeof vi.fn>).mockReturnValue({ lang: 'en', setLang: vi.fn() });

        render(<NotificationBell />);

        expect(screen.getByLabelText('Notifications')).toBeInTheDocument();

        fireEvent.click(screen.getByLabelText('Notifications'));
        expect(screen.getByText('No notifications.')).toBeInTheDocument();
    });

    // ---------------------------------------------------------------
    // 12. Does not fetch when token is null
    // ---------------------------------------------------------------
    it('does not fetch notifications when token is null', async () => {
        mockUseAuth.mockReturnValue(mockAuth({ isAuthenticated: true, tier: 'academic' }));
        mockGetAuthToken.mockReturnValue(null as any);

        render(<NotificationBell />);

        // Give time for requestAnimationFrame
        await new Promise((r) => setTimeout(r, 50));

        expect(mockGetNotifications).not.toHaveBeenCalled();
    });
});
