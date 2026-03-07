import { test, expect } from '@playwright/test';

/**
 * Search data completeness E2E tests.
 *
 * Verifies that search results from the live API are rendered
 * completely and accurately in the UI.
 *
 * Skipped by default. Enable with:
 *   UI_FIDELITY_E2E=1 npx playwright test e2e/search-data-completeness.spec.ts
 *
 * Requirements:
 *   - Next.js server on localhost:3000
 *   - Django API running with Elasticsearch populated
 */

const LIVE = process.env.UI_FIDELITY_E2E === '1';

test.describe('Search data completeness', () => {
    test.skip(!LIVE, 'Requires UI_FIDELITY_E2E=1 with live API');

    test('search "amparo" returns results with law names', async ({ page }) => {
        await page.goto('/busqueda?q=amparo');
        await page.waitForSelector('a[href*="/leyes/"]', { timeout: 15_000 });

        // Each result card should have a law name badge
        const lawNameBadges = page.locator('a[href*="/leyes/"] span.font-mono');
        const count = await lawNameBadges.count();
        expect(count).toBeGreaterThan(0);

        // Verify law names are not empty
        const names = await lawNameBadges.allTextContents();
        for (const name of names) {
            expect(name.trim().length).toBeGreaterThan(0);
        }
    });

    test('search results have clickable links', async ({ page }) => {
        await page.goto('/busqueda?q=amparo');
        await page.waitForSelector('a[href*="/leyes/"]', { timeout: 15_000 });

        const links = page.locator('a[href*="/leyes/"]');
        const hrefs = await links.evaluateAll(els =>
            els.map(el => el.getAttribute('href')).filter(Boolean)
        );

        expect(hrefs.length).toBeGreaterThan(0);
        for (const href of hrefs) {
            expect(href).toMatch(/^\/leyes\//);
        }
    });

    test('search result snippet is not blank', async ({ page }) => {
        await page.goto('/busqueda?q=constitucion');
        await page.waitForSelector('a[href*="/leyes/"]', { timeout: 15_000 });

        const snippets = await page.locator('.line-clamp-3').allTextContents();
        expect(snippets.length).toBeGreaterThan(0);
        for (const snippet of snippets) {
            expect(snippet.trim().length).toBeGreaterThan(10);
        }
    });

    test('search pagination navigates pages', async ({ page }) => {
        await page.goto('/busqueda?q=ley');
        await page.waitForSelector('a[href*="/leyes/"]', { timeout: 15_000 });

        // Get first page result text
        const firstPageSnippets = await page.locator('.line-clamp-3').allTextContents();
        expect(firstPageSnippets.length).toBeGreaterThan(0);

        // Navigate to page 2 if pagination exists
        const page2Btn = page.locator('button:has-text("2"), a:has-text("2")').first();
        if (await page2Btn.isVisible()) {
            await page2Btn.click();
            await page.waitForSelector('a[href*="/leyes/"]', { timeout: 15_000 });

            const secondPageSnippets = await page.locator('.line-clamp-3').allTextContents();
            expect(secondPageSnippets.length).toBeGreaterThan(0);

            // Page 2 should have different results
            expect(secondPageSnippets[0]).not.toBe(firstPageSnippets[0]);
        }
    });

    test('search filters by category narrows results', async ({ page }) => {
        await page.goto('/busqueda?q=ley');
        await page.waitForSelector('a[href*="/leyes/"]', { timeout: 15_000 });

        const showingText = await page.locator('text=/Mostrando|Showing/').textContent();
        const totalMatch = showingText?.match(/de (\d+)|of (\d+)/);
        const totalBefore = totalMatch ? parseInt(totalMatch[1] || totalMatch[2]) : 0;

        // Apply category filter
        await page.goto('/busqueda?q=ley&category=Constitucional');
        await page.waitForSelector('a[href*="/leyes/"]', { timeout: 15_000 });

        const filteredText = await page.locator('text=/Mostrando|Showing/').textContent();
        const filteredMatch = filteredText?.match(/de (\d+)|of (\d+)/);
        const totalAfter = filteredMatch ? parseInt(filteredMatch[1] || filteredMatch[2]) : 0;

        // Filtered results should be fewer (or equal if category matches all)
        expect(totalAfter).toBeLessThanOrEqual(totalBefore);
    });

    test('search filters by jurisdiction changes results', async ({ page }) => {
        await page.goto('/busqueda?q=ley&jurisdiction=state');
        await page.waitForSelector('a[href*="/leyes/"]', { timeout: 15_000 });

        // Results should exist for state jurisdiction
        const results = await page.locator('a[href*="/leyes/"]').count();
        expect(results).toBeGreaterThan(0);
    });

    test('search with empty query shows prompt', async ({ page }) => {
        await page.goto('/busqueda');
        await page.waitForLoadState('networkidle');

        // Should show the "enter search term" prompt
        const prompt = page.locator('text=/Ingresa un t\u00e9rmino|Enter a search term/');
        await expect(prompt).toBeVisible({ timeout: 5_000 });
    });

    test('within-law search finds articles', async ({ page }) => {
        await page.goto('/leyes/cpeum');
        await page.waitForSelector('article', { timeout: 20_000 });

        // Find the within-law search input
        const searchInput = page.locator('input[placeholder*="Buscar dentro"], input[placeholder*="Search within"]');
        await expect(searchInput).toBeVisible();

        // Type a query
        await searchInput.fill('educaci\u00f3n');
        await page.waitForTimeout(500); // wait for debounce

        // Results dropdown should appear with article IDs
        const resultItems = page.locator('text=/Art\\./');
        const count = await resultItems.count();
        // CPEUM should have articles mentioning "educaci\u00f3n"
        expect(count).toBeGreaterThan(0);
    });
});
