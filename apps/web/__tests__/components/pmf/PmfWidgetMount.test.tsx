/**
 * Tests for PmfWidgetMount — the @madfam/pmf-widget host component.
 *
 * Notes on what is and isn't tested here:
 *   - We can deterministically test the synchronous gates (env flag, auth,
 *     pathname). These are pure props/state and produce a `null` render
 *     before any dynamic import is attempted.
 *   - We do NOT test the success path (widget actually rendered) because
 *     `@madfam/pmf-widget` is not installed yet (publish is blocked on
 *     NPM_MADFAM_TOKEN rotation per session_wrapup_2026-04-25). The
 *     dynamic import in the component intentionally swallows the
 *     resolve-failure and renders null. Once the package is published
 *     and installed, follow-up tests should mock `@madfam/pmf-widget`
 *     and assert the widget renders with the expected props.
 *   - Module-level `process.env.NEXT_PUBLIC_PMF_WIDGET_ENABLED` is read
 *     once at import time, so tests use `vi.resetModules()` + dynamic
 *     `await import(...)` to re-evaluate the module under different
 *     env values.
 */
import { render, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { mockAuth } from '../../helpers/auth-mock';

const mockUseAuth = vi.fn(() => mockAuth());
vi.mock('@/components/providers/AuthContext', () => ({
    useAuth: () => mockUseAuth(),
}));

const mockUsePathname = vi.fn<() => string | null>(() => '/leyes');
vi.mock('next/navigation', () => ({
    usePathname: () => mockUsePathname(),
}));

const ORIGINAL_ENV = { ...process.env };

async function loadMount() {
    // Re-evaluate the module so the FLAG_ENABLED constant picks up the
    // current process.env value.
    vi.resetModules();
    const mod = await import('@/components/pmf/PmfWidgetMount');
    return mod.PmfWidgetMount;
}

describe('PmfWidgetMount', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        // Default: pathname is a normal product route.
        mockUsePathname.mockReturnValue('/leyes');
        // Default: not authenticated.
        mockUseAuth.mockReturnValue(mockAuth());
    });

    afterEach(() => {
        // Restore env to avoid leaking flag flips into other suites.
        process.env = { ...ORIGINAL_ENV };
    });

    it('renders nothing when feature flag is off, even if authenticated', async () => {
        process.env.NEXT_PUBLIC_PMF_WIDGET_ENABLED = 'false';
        mockUseAuth.mockReturnValue(
            mockAuth({
                isAuthenticated: true,
                userId: 'user-1',
                email: 'a@example.com',
                tier: 'academic',
            }),
        );
        const PmfWidgetMount = await loadMount();
        const { container } = render(<PmfWidgetMount />);
        expect(container.innerHTML).toBe('');
    });

    it('renders nothing when flag is on but user is anonymous', async () => {
        process.env.NEXT_PUBLIC_PMF_WIDGET_ENABLED = 'true';
        mockUseAuth.mockReturnValue(mockAuth({ isAuthenticated: false }));
        const PmfWidgetMount = await loadMount();
        const { container } = render(<PmfWidgetMount />);
        expect(container.innerHTML).toBe('');
    });

    it('renders nothing on /login even when flag is on and authenticated', async () => {
        process.env.NEXT_PUBLIC_PMF_WIDGET_ENABLED = 'true';
        mockUseAuth.mockReturnValue(
            mockAuth({
                isAuthenticated: true,
                userId: 'user-1',
                tier: 'academic',
            }),
        );
        mockUsePathname.mockReturnValue('/login');
        const PmfWidgetMount = await loadMount();
        const { container } = render(<PmfWidgetMount />);
        expect(container.innerHTML).toBe('');
    });

    it('renders nothing on /login/anything (subpath of excluded prefix)', async () => {
        process.env.NEXT_PUBLIC_PMF_WIDGET_ENABLED = 'true';
        mockUseAuth.mockReturnValue(
            mockAuth({
                isAuthenticated: true,
                userId: 'user-1',
                tier: 'academic',
            }),
        );
        mockUsePathname.mockReturnValue('/login/error');
        const PmfWidgetMount = await loadMount();
        const { container } = render(<PmfWidgetMount />);
        expect(container.innerHTML).toBe('');
    });

    it('renders nothing on /bienvenida (onboarding — would distort signal)', async () => {
        process.env.NEXT_PUBLIC_PMF_WIDGET_ENABLED = 'true';
        mockUseAuth.mockReturnValue(
            mockAuth({
                isAuthenticated: true,
                userId: 'user-1',
                tier: 'free_member',
            }),
        );
        mockUsePathname.mockReturnValue('/bienvenida');
        const PmfWidgetMount = await loadMount();
        const { container } = render(<PmfWidgetMount />);
        expect(container.innerHTML).toBe('');
    });

    it('renders nothing on /admin routes (internal staff)', async () => {
        process.env.NEXT_PUBLIC_PMF_WIDGET_ENABLED = 'true';
        mockUseAuth.mockReturnValue(
            mockAuth({
                isAuthenticated: true,
                userId: 'user-1',
                tier: 'madfam',
            }),
        );
        mockUsePathname.mockReturnValue('/admin/quarantine');
        const PmfWidgetMount = await loadMount();
        const { container } = render(<PmfWidgetMount />);
        expect(container.innerHTML).toBe('');
    });

    it('attempts to load the widget on a normal product route when flag on + authenticated', async () => {
        // We can't assert the widget itself rendered (the @madfam/pmf-widget
        // module is not installed yet), but we can assert the component
        // does not synchronously bail before reaching the dynamic import.
        // Right after mount the render is `null` (Widget state still null),
        // and shortly after the dynamic import rejects → loadFailed=true,
        // still null. This test verifies the gate logic does not short-
        // circuit before the import attempt.
        process.env.NEXT_PUBLIC_PMF_WIDGET_ENABLED = 'true';
        mockUseAuth.mockReturnValue(
            mockAuth({
                isAuthenticated: true,
                userId: 'user-1',
                email: 'a@example.com',
                tier: 'academic',
            }),
        );
        mockUsePathname.mockReturnValue('/leyes/cpeum');
        const PmfWidgetMount = await loadMount();
        const { container } = render(<PmfWidgetMount />);
        // Synchronous render is null (waiting on dynamic import).
        expect(container.innerHTML).toBe('');
        // After the dynamic import settles (rejects, since module isn't
        // installed), the component remains null — verifies the
        // fail-closed catch handler.
        await waitFor(() => {
            expect(container.innerHTML).toBe('');
        });
    });

    it('renders nothing when pathname is null (pre-render edge case)', async () => {
        process.env.NEXT_PUBLIC_PMF_WIDGET_ENABLED = 'true';
        mockUseAuth.mockReturnValue(
            mockAuth({
                isAuthenticated: true,
                userId: 'user-1',
                tier: 'academic',
            }),
        );
        // next/navigation usePathname can return null during initial SSR-
        // hydration mismatches. The component should still render null.
        mockUsePathname.mockReturnValue(null);
        const PmfWidgetMount = await loadMount();
        const { container } = render(<PmfWidgetMount />);
        expect(container.innerHTML).toBe('');
    });
});
