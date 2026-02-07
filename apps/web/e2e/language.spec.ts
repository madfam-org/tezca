import { test, expect } from './fixtures';

test.describe('Language toggle', () => {
    test('toggling from ES to EN changes heading text on search page', async ({ page }) => {
        await page.goto('/search?q=ley');

        // Default language is Spanish
        await expect(page.getByRole('heading', { name: 'Buscar Leyes' })).toBeVisible();

        // Click the EN button in the language toggle (use .first() — navbar + footer both have toggle)
        const enButton = page.getByRole('button', { name: 'Switch to English' }).first();
        await enButton.click();

        // Heading should now be in English
        await expect(page.getByRole('heading', { name: 'Search Laws' })).toBeVisible();

        // Toggle back to Spanish
        const esButton = page.getByRole('button', { name: 'Cambiar a español' }).first();
        await esButton.click();

        await expect(page.getByRole('heading', { name: 'Buscar Leyes' })).toBeVisible();
    });

    test('language persists across navigation', async ({ page }) => {
        // Start on search page, switch to English
        await page.goto('/search?q=ley');
        await expect(page.getByRole('heading', { name: 'Buscar Leyes' })).toBeVisible();

        const enButton = page.getByRole('button', { name: 'Switch to English' }).first();
        await enButton.click();
        await expect(page.getByRole('heading', { name: 'Search Laws' })).toBeVisible();

        // Navigate to favoritos page — should still be in English
        await page.goto('/favoritos');
        await expect(page.getByText('Favorites').first()).toBeVisible();
        await expect(page.getByText('You have no saved laws')).toBeVisible();

        // Navigate to law detail — English error text if law loads (or header text)
        await page.goto('/laws/ley-federal-del-trabajo');
        await expect(page.getByText('Ley Federal del Trabajo').first()).toBeVisible();
        // The "Compare" button label should be in English
        await expect(page.getByText('Compare').first()).toBeVisible();
    });
});
