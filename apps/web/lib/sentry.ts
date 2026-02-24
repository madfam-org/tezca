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
const SENTRY_RELEASE = process.env.NEXT_PUBLIC_SENTRY_RELEASE || '';

/* eslint-disable @typescript-eslint/no-explicit-any */

/**
 * Cached Sentry module promise — avoids re-importing on every call.
 */
let _sentryPromise: Promise<any | null> | null = null;

function loadSentry(): Promise<any | null> {
    if (!_sentryPromise) {
        _sentryPromise = Function('return import("@sentry/nextjs")')().catch(() => null);
    }
    return _sentryPromise;
}

export function initSentry() {
    if (!SENTRY_DSN) return;

    loadSentry().then((Sentry) => {
        if (!Sentry) return;
        Sentry.init({
            dsn: SENTRY_DSN,
            environment: SENTRY_ENVIRONMENT,
            release: SENTRY_RELEASE || undefined,
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
