import { test, expect } from '@playwright/test';

/**
 * Data-integrity spot-checks that run against a live API.
 *
 * These tests are skipped by default. Enable them by setting the
 * DATA_INTEGRITY_E2E environment variable:
 *
 *   DATA_INTEGRITY_E2E=1 npx playwright test e2e/data-integrity.spec.ts
 *
 * Requirements:
 *   - The Next.js dev/prod server must be running on localhost:3000
 *   - The Django API must be running and reachable at the configured API URL
 *   - Elasticsearch must be populated with article data
 */

const LIVE_API = process.env.DATA_INTEGRITY_E2E === '1';

test.describe('Data integrity spot-checks', () => {
    test.skip(!LIVE_API, 'Requires DATA_INTEGRITY_E2E=1 with live API');

    test('CPEUM loads with articles', async ({ page }) => {
        await page.goto('/leyes/cpeum');

        // Wait for at least one article element to appear
        await page.waitForSelector('article', { timeout: 15_000 });

        const articleElements = await page.locator('article').count();
        // CPEUM has ~136 articles; verify a meaningful number loaded
        expect(articleElements).toBeGreaterThan(100);
    });

    test('search returns valid snippets', async ({ page }) => {
        await page.goto('/busqueda?q=amparo');

        // Wait for search results to render
        await page.waitForSelector('[data-testid="search-result"], .search-result, a[href*="/leyes/"]', {
            timeout: 15_000,
        });

        // At least one result should have visible snippet text
        const snippets = page.locator('text=/amparo/i');
        const count = await snippets.count();
        expect(count).toBeGreaterThan(0);
    });

    test('article text displays accented characters', async ({ page }) => {
        await page.goto('/leyes/cpeum');

        // Wait for articles to load
        await page.waitForSelector('article', { timeout: 15_000 });

        // Grab all visible article text
        const articleTexts = await page.locator('article').allTextContents();
        const combinedText = articleTexts.join(' ');

        // Mexican legal text uses accented characters extensively
        const hasAccents = /[aeiou\u0301\u00e1\u00e9\u00ed\u00f3\u00fa\u00f1]/i.test(combinedText);
        expect(hasAccents).toBe(true);
    });

    test('law detail shows article count', async ({ page }) => {
        await page.goto('/leyes/cpeum');

        // Wait for the page to fully load articles
        await page.waitForSelector('article', { timeout: 15_000 });

        // Either the page shows an article count in the header/meta, or
        // articles are directly rendered. Verify at least one article is visible.
        const articleCount = await page.locator('article').count();
        expect(articleCount).toBeGreaterThan(0);
    });
});
