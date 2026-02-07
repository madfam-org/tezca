import { test, expect } from './fixtures';

test.describe('Navbar', () => {
    test('navbar shows on homepage with brand link', async ({ page }) => {
        await page.goto('/');

        // The navbar has the brand "Tezca" as a link to home (use .first() — footer also has brand)
        const brandLink = page.getByRole('link', { name: 'Tezca' }).first();
        await expect(brandLink).toBeVisible();
        await expect(brandLink).toHaveAttribute('href', '/');
    });

    test('clicking Buscar navigates to /search', async ({ page }) => {
        await page.goto('/');

        // Desktop nav has a "Buscar" link
        const searchLink = page.getByRole('link', { name: 'Buscar' }).first();
        await expect(searchLink).toBeVisible();

        await searchLink.click();

        await expect(page).toHaveURL('/search');
        await expect(page.getByRole('heading', { name: 'Buscar Leyes' })).toBeVisible();
    });

    test('active nav link has active styling on /search', async ({ page }) => {
        await page.goto('/search');

        // The "Buscar" link should have active class (bg-primary/10 text-primary)
        const searchLink = page.getByRole('link', { name: 'Buscar' }).first();
        await expect(searchLink).toBeVisible();
        await expect(searchLink).toHaveClass(/text-primary/);
        await expect(searchLink).toHaveClass(/bg-primary/);

        // Other links should not have the active class
        const homeLink = page.getByRole('link', { name: 'Inicio' }).first();
        await expect(homeLink).not.toHaveClass(/bg-primary/);
    });

    test('navbar links navigate correctly', async ({ page }) => {
        await page.goto('/');

        // Click "Explorar" to go to /laws
        const exploreLink = page.getByRole('link', { name: 'Explorar' }).first();
        await expect(exploreLink).toBeVisible();
        await exploreLink.click();
        await expect(page).toHaveURL('/laws');

        // Click "Favoritos" to go to /favoritos
        const favoritesLink = page.getByRole('link', { name: 'Favoritos' }).first();
        await expect(favoritesLink).toBeVisible();
        await favoritesLink.click();
        await expect(page).toHaveURL('/favoritos');
    });
});
