import { test, expect } from './fixtures';

test.describe('Comparison flow', () => {
    test('selecting a law on /laws page shows floating bar', async ({ page }) => {
        await page.goto('/laws');

        // Law cards render with comparison checkboxes
        const checkboxes = page.locator('[title="Comparar ley"]');
        await expect(checkboxes.first()).toBeVisible();

        // Click first checkbox
        await checkboxes.nth(0).click();

        // Floating bar appears with "1 leyes seleccionadas"
        await expect(page.getByText(/1 leyes? seleccionadas?/)).toBeVisible();
        await expect(page.getByText('Selecciona otra para comparar')).toBeVisible();
    });

    test('clear button resets selection', async ({ page }) => {
        await page.goto('/laws');

        const checkboxes = page.locator('[title="Comparar ley"]');
        await expect(checkboxes.first()).toBeVisible();

        await checkboxes.nth(0).click();
        await expect(page.getByText(/1 leyes? seleccionadas?/)).toBeVisible();

        // Click clear
        await page.getByText('Limpiar').click();

        // Floating bar should disappear
        await expect(page.getByText(/leyes? seleccionadas?/)).not.toBeVisible();
    });

    test('compare page renders dual pane with metadata', async ({ page }) => {
        await page.goto('/compare?laws=ley-federal-del-trabajo,codigo-civil-federal');

        // Header — use first() since both responsive spans exist in DOM
        await expect(page.getByText('Comparación Estructural').first()).toBeVisible();

        // Metadata panel with tier badges
        await expect(page.getByText('Federal').first()).toBeVisible();

        // Both law names appear
        await expect(page.getByText('Ley Federal del Trabajo').first()).toBeVisible();
        await expect(page.getByText('Código Civil Federal').first()).toBeVisible();

        // Article match count ("Art. 1" is shared → 1 match)
        await expect(page.getByText(/artículo en común/).first()).toBeVisible();
    });

    test('compare page toolbar has sync and copy buttons', async ({ page }) => {
        await page.goto('/compare?laws=ley-federal-del-trabajo,codigo-civil-federal');

        // Wait for comparison to load
        await expect(page.getByText('Ley Federal del Trabajo').first()).toBeVisible();

        // Toolbar buttons
        await expect(page.getByText(/Sincronizar scroll|Sync/).first()).toBeVisible();
        await expect(page.getByText(/Copiar enlace|URL/).first()).toBeVisible();
    });

    test('compare page with insufficient laws shows empty state', async ({ page }) => {
        await page.goto('/compare?laws=ley-federal-del-trabajo');

        await expect(page.getByText('Selecciona leyes para comparar')).toBeVisible();
        await expect(page.getByRole('link', { name: 'Ir al Buscador' })).toBeVisible();
    });
});
