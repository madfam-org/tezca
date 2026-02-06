import { test, expect } from './fixtures';

test.describe('Search flow', () => {
    test('homepage hero search navigates to search page with results', async ({ page }) => {
        await page.goto('/');

        // Hero renders with law count from stats
        await expect(page.getByPlaceholder(/Buscar en/)).toBeVisible();

        // Type a query in the hero search bar
        await page.getByPlaceholder(/Buscar en/).fill('ley federal');
        await page.getByPlaceholder(/Buscar en/).press('Enter');

        // Should navigate to /search?q=ley+federal
        await expect(page).toHaveURL(/\/search\?q=ley/);

        // Search page renders with heading
        await expect(page.getByRole('heading', { name: 'Buscar Leyes' })).toBeVisible();
    });

    test('search page shows results from API', async ({ page }) => {
        await page.goto('/search?q=ley');

        // Wait for results to render
        await expect(page.getByText('Ley Federal del Trabajo').first()).toBeVisible();
        await expect(page.getByText('Código Civil Federal').first()).toBeVisible();

        // Result count is displayed
        await expect(page.getByText(/de 2 resultado/)).toBeVisible();
    });

    test('clicking a search result navigates to law detail', async ({ page }) => {
        await page.goto('/search?q=ley');

        // Wait for results
        await expect(page.getByText('Ley Federal del Trabajo').first()).toBeVisible();

        // Click the first result (it's a link to /laws/ley-federal-del-trabajo)
        await page.getByText('Ley Federal del Trabajo').first().click();

        // Should navigate to the law detail page
        await expect(page).toHaveURL(/\/laws\/ley-federal-del-trabajo/);
    });
});
