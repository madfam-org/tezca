import { DEFAULT_ECOSYSTEM_PLATFORMS, type EcosystemPlatform } from '@madfam/ecosystem-banner';

import { ecosystemLink } from './ecosystem-links';

/**
 * Platform list for the ecosystem banner (2026-10-11).
 *
 * WHY: the pinned `@madfam/ecosystem-banner` 0.1.4 links Forgesight to
 * `https://forgesight.quest`, which has no DNS, and renders bare apex URLs, so
 * a visitor who moves to another MADFAM site arrives as "direct" traffic. The
 * fixed package (0.3.0, solarpunk-foundry PR #67) is not published yet, so this
 * app passes the corrected list through the banner's `platforms` prop instead.
 * Remove this file once the pin is bumped to a release that carries the fix.
 *
 * `rel` cannot be changed from outside the published package: links keep
 * `rel="noopener noreferrer"` until 0.3.0 is published and the pin is bumped.
 */

const RETIRED_FORGESIGHT_HOST = 'forgesight.quest';
const FORGESIGHT_URL = 'https://forgesight.app';

/**
 * Registrable domains a cross-property link treats as MADFAM-owned. Mirrors
 * `MADFAM_OWNED_DOMAINS` in `@madfam/ecosystem-banner` 0.3.0 (the product
 * projection, 2026-10-09 revision, plus `madfam.io`; the apex covers every
 * `*.madfam.io` product host).
 */
export const MADFAM_OWNED_DOMAINS: readonly string[] = [
  'madfam.io',
  'enclii.dev',
  'janua.dev',
  'selva.town',
  'forgesight.app',
  'dhan.am',
  'fortuna.tube',
  'rondel.io',
  'karafiel.mx',
  'tezca.mx',
  'avala.studio',
  'yantra4d.com',
  'cotiza.studio',
  'phynd.app',
  'ceq.lol',
  'kalya.app',
  'nauta.quest',
  'fashioncabi.net',
  'factl.as',
  'routecraft.app',
  'telesia.quest',
  'madf.am',
];

function hostOf(url: string): string {
  try {
    return new URL(url).hostname;
  } catch {
    return '';
  }
}

/** The package defaults with the retired Forgesight host replaced. */
export const ECOSYSTEM_BANNER_PLATFORMS: readonly EcosystemPlatform[] =
  DEFAULT_ECOSYSTEM_PLATFORMS.map((platform) =>
    hostOf(platform.url) === RETIRED_FORGESIGHT_HOST
      ? { ...platform, url: FORGESIGHT_URL }
      : platform
  );

/**
 * Applies the own-site link policy (`ecosystem-links.ts`) to each platform URL
 * for a page served from `originHost`: own-site links gain the ecosystem UTM
 * set; same-host, localhost, IP and third-party links are left unchanged.
 */
export function tagEcosystemPlatforms(
  platforms: readonly EcosystemPlatform[],
  originHost: string
): EcosystemPlatform[] {
  return platforms.map((platform) => ({
    ...platform,
    url: ecosystemLink(platform.url, {
      surface: 'banner',
      originHost,
      ownedDomains: MADFAM_OWNED_DOMAINS,
    }).href,
  }));
}
