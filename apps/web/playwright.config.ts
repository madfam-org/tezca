import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
    testDir: './e2e',
    fullyParallel: true,
    forbidOnly: !!process.env.CI,
    retries: process.env.CI ? 2 : 0,
    workers: process.env.CI ? 1 : undefined,
    reporter: process.env.CI ? 'github' : 'html',
    timeout: 30_000,
    use: {
        baseURL: 'http://localhost:3000',
        trace: 'on-first-retry',
        screenshot: 'only-on-failure',
    },
    projects: [
        {
            name: 'chromium',
            use: { ...devices['Desktop Chrome'] },
        },
        {
            name: 'firefox',
            use: { ...devices['Desktop Firefox'] },
        },
        {
            name: 'mobile-safari',
            use: { ...devices['iPhone 14'] },
        },
        {
            name: 'mobile-android',
            use: { ...devices['Pixel 7'] },
        },
    ],
    webServer: {
        command: 'echo CI=$CI && HOSTNAME=0.0.0.0 npx next start -p 3000',
        url: 'http://localhost:3000',
        // The CI E2E workflow already builds and runs web in the
        // docker-compose.e2e.yml stack on :3000 (and waits for it), so
        // Playwright must REUSE that server, not spawn a second `next
        // start` on the same port. reuseExistingServer must therefore be
        // true in CI too — the previous `!process.env.CI` caused a port
        // conflict the moment the API actually booted.
        reuseExistingServer: true,
        timeout: process.env.CI ? 300_000 : 120_000,
    },
});
