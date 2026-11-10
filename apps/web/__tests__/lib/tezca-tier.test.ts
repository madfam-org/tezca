import { describe, it, expect } from 'vitest';
import { resolveTezcaTier } from '@/lib/tezca-tier';

describe('resolveTezcaTier', () => {
    it.each([
        [{ tier: 'pro' }],
        [{ tier: 'essentials' }],
        [{ tier: 'premium', plan: 'enterprise' }],
        [{ plan: 'pro' }],
        [{ tier: 'community' }],
        [{ tier: 'madfam' }],
        [{ tier: 'pro', karafiel_tier: 'pro' }],
        [{ tier: 'pro', madfam_entitled_products: ['karafiel:pro'] }],
    ])('reads another product\'s tier without tezca_tier as free (%j)', (claims) => {
        expect(resolveTezcaTier(claims)).toBe('free_member');
    });

    it('reads no claims as free', () => {
        expect(resolveTezcaTier({})).toBe('free_member');
        expect(resolveTezcaTier(null)).toBe('free_member');
        expect(resolveTezcaTier(undefined)).toBe('free_member');
    });

    it.each([
        ['free', 'free_member'],
        ['essentials', 'essentials'],
        ['academic', 'academic'],
        ['institutional', 'institutional'],
        ['community', 'community'],
        ['pro', 'academic'],
        ['pro_plus', 'academic'],
        ['enterprise', 'academic'],
        ['ACADEMIC', 'academic'],
    ])('maps tezca_tier=%s to %s', (value, expected) => {
        expect(resolveTezcaTier({ tezca_tier: value, tier: 'community' })).toBe(expected);
    });

    it('prefers tezca_tier over the generic tier', () => {
        expect(resolveTezcaTier({ tezca_tier: 'essentials', tier: 'premium' })).toBe('essentials');
    });

    it('keeps MADFAM operators at the madfam tier', () => {
        expect(resolveTezcaTier({ tezca_tier: 'madfam' })).toBe('madfam');
        expect(resolveTezcaTier({ tezca_tier: 'internal' })).toBe('madfam');
    });

    it.each([[''], ['admin'], ['platinum'], ['tezca:academic'], [3], [['academic']], [{ a: 1 }], ['constructor'], ['__proto__']])(
        'fails closed on malformed or unknown tezca_tier %j',
        (value) => {
            expect(
                resolveTezcaTier({
                    tezca_tier: value,
                    tier: 'premium',
                    madfam_entitled_products: ['tezca:institutional'],
                }),
            ).toBe('free_member');
        },
    );

    it('uses a tezca: entitlement when tezca_tier is absent', () => {
        expect(
            resolveTezcaTier({ tier: 'community', madfam_entitled_products: ['dhanam:pro', 'tezca:academic'] }),
        ).toBe('academic');
    });

    it.each([[['tezca:admin']], [['tezca:']], [['tezcaacademic']], ['tezca:academic'], [[null, 7]]])(
        'fails closed on unusable madfam_entitled_products %j',
        (entitled) => {
            expect(resolveTezcaTier({ tier: 'pro', madfam_entitled_products: entitled })).toBe('free_member');
        },
    );
});
