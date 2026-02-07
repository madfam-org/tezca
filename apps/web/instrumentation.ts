/**
 * Next.js instrumentation hook — runs once on server startup.
 * Used to initialize Sentry on the server side.
 */
export async function register() {
    if (process.env.NEXT_PUBLIC_SENTRY_DSN) {
        const { initSentry } = await import('./lib/sentry');
        initSentry();
    }
}
