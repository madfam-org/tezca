import { describe, it, expect, vi, afterEach } from 'vitest';
import { STATE_SLUGS, getStateSeo } from '@/lib/states';
import { generateMetadata } from '@/app/estados/[state]/layout';

const ROOT_TITLE = 'Tezca — El Espejo de la Ley';

describe('state page SEO', () => {
    it('covers the 32 states', () => {
        expect(STATE_SLUGS).toHaveLength(32);
    });

    it('gives every state a unique title and description, never the root title', () => {
        const titles = STATE_SLUGS.map((s) => getStateSeo(s).title);
        const descriptions = STATE_SLUGS.map((s) => getStateSeo(s).description);
        expect(new Set(titles).size).toBe(32);
        expect(new Set(descriptions).size).toBe(32);
        expect(titles).not.toContain(ROOT_TITLE);
    });

    it('uses the accented display name', () => {
        expect(getStateSeo('nuevo_leon').title).toBe('Leyes de Nuevo León — Legislación estatal — Tezca');
        expect(getStateSeo('yucatan').description).toContain('Yucatán');
    });

    it('generateMetadata returns the state title, description and canonical', async () => {
        const meta = await generateMetadata({ params: Promise.resolve({ state: 'ciudad_de_mexico' }) });
        expect(meta.title).toBe('Leyes de Ciudad de México — Legislación estatal — Tezca');
        expect(meta.description).toContain('Ciudad de México');
        expect(meta.alternates?.canonical).toBe('https://tezca.mx/estados/ciudad_de_mexico');
    });
});

describe('sitemap', () => {
    afterEach(() => {
        vi.unstubAllGlobals();
    });

    it('lists every state page, the pricing page, and no admin or API URLs', async () => {
        vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('offline')));
        const { default: sitemap } = await import('@/app/sitemap');
        const urls = (await sitemap()).map((e) => e.url);
        for (const slug of STATE_SLUGS) {
            expect(urls).toContain(`https://tezca.mx/estados/${slug}`);
        }
        expect(urls).toContain('https://tezca.mx/precios');
        expect(urls.some((u) => /\/(admin|api)\//.test(u))).toBe(false);
    });
});
