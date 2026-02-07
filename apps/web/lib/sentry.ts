/**
 * Sentry initialization for Next.js web app.
 *
 * Conditionally loads Sentry only when NEXT_PUBLIC_SENTRY_DSN is set
 * AND @sentry/nextjs is installed. Both conditions must be true.
 *
 * To enable: npm install @sentry/nextjs && set NEXT_PUBLIC_SENTRY_DSN in env.
 */

const SENTRY_DSN = process.env.NEXT_PUBLIC_SENTRY_DSN || '';
const SENTRY_ENVIRONMENT = process.env.NEXT_PUBLIC_SENTRY_ENVIRONMENT || 'development';

/* eslint-disable @typescript-eslint/no-explicit-any */

/**
 * Dynamically load the Sentry module. Returns null if not installed.
 */
async function loadSentry(): Promise<any | null> {
    try {
        // Dynamic require avoids TS module resolution errors when not installed
        return await Function('return import("@sentry/nextjs")')();
    } catch {
        return null;
    }
}

export function initSentry() {
    if (!SENTRY_DSN) return;

    loadSentry().then((Sentry) => {
        if (!Sentry) return;
        Sentry.init({
            dsn: SENTRY_DSN,
            environment: SENTRY_ENVIRONMENT,
            tracesSampleRate: 0.1,
        });
    });
}

/**
 * Report an error to Sentry (no-op if Sentry is not configured or installed).
 */
export function captureError(error: unknown, context?: Record<string, unknown>) {
    if (!SENTRY_DSN) return;

    loadSentry().then((Sentry) => {
        if (!Sentry) return;
        if (context) {
            Sentry.withScope((scope: any) => {
                Object.entries(context).forEach(([key, value]) => {
                    scope.setExtra(key, value);
                });
                Sentry.captureException(error);
            });
        } else {
            Sentry.captureException(error);
        }
    });
}
