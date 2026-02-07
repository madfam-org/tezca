import { test, expect } from './fixtures';

test.describe('404 page', () => {
    test('navigating to nonexistent page shows 404 heading', async ({ page }) => {
        await page.goto('/nonexistent-page-xyz');

        // The not-found page renders "Pagina no encontrada" (Spanish default)
        await expect(page.getByRole('heading', { name: 'Pagina no encontrada' })).toBeVisible();
        await expect(page.getByText('La pagina que buscas no existe o fue movida.')).toBeVisible();
        await expect(page.getByText('404')).toBeVisible();
    });

    test('404 page has link back to home', async ({ page }) => {
        await page.goto('/nonexistent-page-xyz');

        await expect(page.getByRole('heading', { name: 'Pagina no encontrada' })).toBeVisible();

        // "Ir al inicio" link navigates to /
        const homeLink = page.getByRole('link', { name: 'Ir al inicio' });
        await expect(homeLink).toBeVisible();
        await expect(homeLink).toHaveAttribute('href', '/');
    });

    test('404 page has link to search', async ({ page }) => {
        await page.goto('/nonexistent-page-xyz');

        await expect(page.getByRole('heading', { name: 'Pagina no encontrada' })).toBeVisible();

        // "Buscar leyes" link navigates to /search (use exact to avoid footer match)
        const searchLink = page.getByRole('link', { name: 'Buscar leyes', exact: true });
        await expect(searchLink).toBeVisible();
        await expect(searchLink).toHaveAttribute('href', '/search');
    });
});
