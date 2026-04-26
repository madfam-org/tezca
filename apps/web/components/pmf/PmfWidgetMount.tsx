'use client';

/**
 * PmfWidgetMount — scaffolded integration for `@madfam/pmf-widget`.
 *
 * SCAFFOLD STATUS (read before "fixing" the dynamic import):
 *
 * `@madfam/pmf-widget@0.1.0` is built but NOT YET PUBLISHED to the
 * MADFAM npm registry. Publish is blocked on `NPM_MADFAM_TOKEN`
 * rotation (operator-only — see project_session_wrapup_2026-04-25.md
 * task #38). The package is declared in apps/web/package.json so
 * lockfile resolution lands the moment the publish unblocks, but
 * `npm ci` in CI today resolves it as a missing optional-ish dep.
 *
 * To keep CI green BEFORE the publish:
 *   1. The import is dynamic (runtime), not static — webpack/turbopack
 *      do not resolve it at build time, so a missing module does not
 *      fail the build.
 *   2. The component is gated on `NEXT_PUBLIC_PMF_WIDGET_ENABLED`. Until
 *      an operator flips the flag, the dynamic import never fires and
 *      no runtime resolution is attempted.
 *   3. A local type stub at `apps/web/types/madfam-pmf-widget.d.ts`
 *      satisfies `tsc --noEmit` so typecheck passes without the package
 *      installed. Delete the stub after the real package is installed
 *      so the published types take over.
 *
 * Activation checklist (post-publish):
 *   - Operator runs `npm install @madfam/pmf-widget@^0.1.0` in apps/web
 *   - Set `NEXT_PUBLIC_PMF_WIDGET_ENABLED=true` in the deployed env
 *   - Set `NEXT_PUBLIC_TULANA_API_URL` if not the default
 *   - Delete `apps/web/types/madfam-pmf-widget.d.ts`
 *
 * See RFC 0013 (internal-devops/rfcs/0013-pmf-via-coforma-and-tulana.md)
 * for the full PMF measurement architecture.
 */

import { useEffect, useState, type ComponentType } from 'react';
import { usePathname } from 'next/navigation';
import { useAuth } from '@/components/providers/AuthContext';

const FLAG_ENABLED = process.env.NEXT_PUBLIC_PMF_WIDGET_ENABLED === 'true';
const TULANA_API_URL =
  process.env.NEXT_PUBLIC_TULANA_API_URL || 'https://api.tulana.madfam.io';

/**
 * Route prefixes where the PMF widget MUST NOT render. PMF signal is only
 * meaningful on the post-login product surface; rendering on auth pages,
 * the UTM-aware onboarding landing, or the internal admin app would either
 * (a) distort the signal (first-session noise) or (b) confuse internal
 * staff into submitting feedback as if they were customers.
 *
 * Marketing/public pages (homepage, /precios, /leyes, etc.) are implicitly
 * excluded by the `auth.isAuthenticated` gate below — anonymous traffic
 * never sees the widget regardless of pathname.
 */
const EXCLUDED_PATH_PREFIXES = [
  '/login',       // Janua sign-in / sign-up flow
  '/bienvenida',  // UTM-aware onboarding landing — first-session, would distort signal
  '/admin',       // Internal admin surface (not customer product)
];

function isExcludedPath(pathname: string | null): boolean {
  if (!pathname) return false;
  return EXCLUDED_PATH_PREFIXES.some(
    (prefix) => pathname === prefix || pathname.startsWith(`${prefix}/`),
  );
}

// Minimal structural type matching @madfam/pmf-widget's PMFWidgetProps.
// Kept narrow so we only depend on the props we actually pass; the real
// types take over once the package is installed.
interface PmfWidgetComponentProps {
  product: string;
  user: { id: string; email?: string; name?: string; plan?: string };
  apiUrl: string;
  triggers: {
    nps?: { afterSession?: number; dismissCooldownDays?: number };
    ellis?: { afterSession?: number; dismissCooldownDays?: number };
    smile?: { afterAction?: { type: string; count: number } };
  };
  productLabel?: string;
  disabled?: boolean;
}

type PmfWidgetModule = {
  PMFWidget: ComponentType<PmfWidgetComponentProps>;
};

export function PmfWidgetMount() {
  const auth = useAuth();
  const pathname = usePathname();
  const [Widget, setWidget] = useState<ComponentType<PmfWidgetComponentProps> | null>(null);
  const [loadFailed, setLoadFailed] = useState(false);

  const pathExcluded = isExcludedPath(pathname);

  useEffect(() => {
    if (!FLAG_ENABLED) return;
    if (pathExcluded) return;
    if (!auth.isAuthenticated || !auth.userId) return;

    let cancelled = false;
    // Dynamic import keeps the build green when the package is not yet
    // installed. Webpack/Turbopack treat the string as a runtime value,
    // so it is not resolved at compile time.
    const modulePath = '@madfam/pmf-widget';
    import(/* webpackIgnore: true */ /* @vite-ignore */ modulePath)
      .then((mod: PmfWidgetModule) => {
        if (cancelled) return;
        setWidget(() => mod.PMFWidget);
      })
      .catch(() => {
        if (cancelled) return;
        // Package not installed yet (pre-publish) or transient runtime
        // resolve failure. Fail closed — never break the page on a
        // telemetry widget.
        setLoadFailed(true);
      });

    return () => {
      cancelled = true;
    };
  }, [auth.isAuthenticated, auth.userId, pathExcluded]);

  if (!FLAG_ENABLED) return null;
  if (pathExcluded) return null;
  if (loadFailed) return null;
  if (!Widget) return null;
  if (!auth.isAuthenticated || !auth.userId) return null;

  return (
    <Widget
      product="tezca"
      user={{
        id: auth.userId,
        email: auth.email ?? undefined,
        name: auth.name ?? undefined,
        plan: auth.tier,
      }}
      apiUrl={TULANA_API_URL}
      productLabel="Tezca"
      triggers={{
        nps: { afterSession: 5, dismissCooldownDays: 30 },
        ellis: { afterSession: 3, dismissCooldownDays: 45 },
        smile: { afterAction: { type: 'law_viewed', count: 3 } },
      }}
    />
  );
}
