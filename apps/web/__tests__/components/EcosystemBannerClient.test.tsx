import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { EcosystemBannerClient } from '@/components/EcosystemBannerClient';
import {
    ECOSYSTEM_BANNER_PLATFORMS,
    MADFAM_OWNED_DOMAINS,
    tagEcosystemPlatforms,
} from '@/lib/ecosystem-banner-platforms';
import { ecosystemLink, isOwnHost } from '@/lib/ecosystem-links';

// Stand-in for the published 0.1.4 package: same defaults (including the
// retired Forgesight host the wrapper must replace), and it renders `href`
// verbatim from each platform's `url`, as the real banner does.
vi.mock('@madfam/ecosystem-banner', () => ({
    DEFAULT_ECOSYSTEM_PLATFORMS: [
        { keyword: 'LEGAL OPS', name: 'Tezca', url: 'https://tezca.mx' },
        { keyword: 'BUDGETING & WEALTH', name: 'Dhanam', url: 'https://dhan.am' },
        { keyword: 'AUTHENTICATION', name: 'Janua', url: 'https://auth.madfam.io' },
        { keyword: 'INDUSTRY INTELLIGENCE', name: 'Forge Sight', url: 'https://forgesight.quest' },
    ],
    EcosystemBanner: ({
        testId,
        platforms = [],
    }: {
        testId?: string;
        platforms?: readonly { name: string; url: string }[];
    }) => (
        <div data-testid={testId ?? 'ecosystem-banner'}>
            {platforms.map((p) => (
                <a key={p.name} href={p.url}>
                    {p.name}
                </a>
            ))}
        </div>
    ),
}));

describe('EcosystemBannerClient', () => {
    it('renders the banner', () => {
        render(<EcosystemBannerClient />);
        expect(screen.getByTestId('ecosystem-banner')).toBeInTheDocument();
    });

    it('links Forgesight to forgesight.app, never the retired forgesight.quest', () => {
        render(<EcosystemBannerClient />);
        const hrefs = screen.getAllByRole('link').map((a) => a.getAttribute('href') ?? '');
        expect(hrefs.some((h) => new URL(h).hostname === 'forgesight.app')).toBe(true);
        expect(hrefs.some((h) => h.includes('forgesight.quest'))).toBe(false);
    });

    it('adds no UTM when the page host is not public (jsdom serves localhost)', () => {
        render(<EcosystemBannerClient />);
        for (const a of screen.getAllByRole('link')) {
            expect(a.getAttribute('href')).not.toContain('utm_');
        }
    });
});

describe('ecosystem banner platforms (2026-10-11 fix)', () => {
    it('replaces only the Forgesight url in the package defaults', () => {
        expect(ECOSYSTEM_BANNER_PLATFORMS.map((p) => p.url)).toEqual([
            'https://tezca.mx',
            'https://dhan.am',
            'https://auth.madfam.io',
            'https://forgesight.app',
        ]);
    });

    it('treats every banner destination as a MADFAM-owned host', () => {
        for (const p of ECOSYSTEM_BANNER_PLATFORMS) {
            expect(isOwnHost(new URL(p.url).hostname, MADFAM_OWNED_DOMAINS)).toBe(true);
        }
    });

    it('tags other own sites from tezca.mx and leaves the own host untagged', () => {
        const byName = Object.fromEntries(
            tagEcosystemPlatforms(ECOSYSTEM_BANNER_PLATFORMS, 'tezca.mx').map((p) => [p.name, p.url])
        );
        expect(byName['Tezca']).toBe('https://tezca.mx');
        for (const name of ['Dhanam', 'Janua', 'Forge Sight']) {
            const url = new URL(byName[name] as string);
            expect(url.searchParams.get('utm_source')).toBe('tezca.mx');
            expect(url.searchParams.get('utm_medium')).toBe('ecosystem');
            expect(url.searchParams.get('utm_campaign')).toBe('banner');
        }
        expect(new URL(byName['Forge Sight'] as string).hostname).toBe('forgesight.app');
    });

    it('adds no UTM from localhost, an IP or an unknown origin', () => {
        for (const originHost of ['localhost', '127.0.0.1', '']) {
            expect(tagEcosystemPlatforms(ECOSYSTEM_BANNER_PLATFORMS, originHost)).toEqual(
                ECOSYSTEM_BANNER_PLATFORMS
            );
        }
    });

    it('keeps noreferrer and adds no UTM on a third-party link', () => {
        expect(
            ecosystemLink('https://github.com/madfam-org', {
                surface: 'banner',
                originHost: 'tezca.mx',
                ownedDomains: MADFAM_OWNED_DOMAINS,
            })
        ).toEqual({ href: 'https://github.com/madfam-org', rel: 'noopener noreferrer' });
    });

    it('never overrides an existing utm_source', () => {
        const href = 'https://dhan.am/?utm_source=newsletter';
        expect(
            ecosystemLink(href, {
                surface: 'banner',
                originHost: 'tezca.mx',
                ownedDomains: MADFAM_OWNED_DOMAINS,
            }).href
        ).toBe(href);
    });
});
