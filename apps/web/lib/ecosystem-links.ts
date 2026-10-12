/**
 * Own-site link policy for MADFAM cross-property links (2026-10-11).
 *
 * WHY: every banner link used to carry `rel="noopener noreferrer"` and a bare
 * apex URL, so a visitor who moved from one MADFAM site to another arrived as
 * "direct" traffic - the destination learned neither the referrer nor the
 * origin. The policy here keeps that origin, and adds nothing else:
 *
 * - A link to a MADFAM-owned host gets `rel="noopener"` (no `noreferrer`, so the
 *   browser's normal Referer reaches our own destination) and
 *   `utm_source=<origin-host>&utm_medium=ecosystem&utm_campaign=<surface>`.
 * - A link to any other host keeps `rel="noopener noreferrer"` and is never
 *   tagged.
 * - No UTM is added when the origin is unknown or not a public host (SSR,
 *   localhost, an IP, a preview), when the link stays on the same host, or when
 *   the URL already names a `utm_source` - the visitor's real source wins.
 *
 * These are plain query parameters on our own links. No cookie, no storage, no
 * tracker, no analytics vendor (analytics rule R41).
 */

/** Where on the page the link sits; becomes `utm_campaign`. */
export type EcosystemSurface = 'banner' | 'ladder' | 'footer' | 'cta';

/** `rel` for a link to a MADFAM-owned host: keep the Referer, drop the opener. */
export const OWN_SITE_REL = 'noopener';
/** `rel` for every other link. */
export const THIRD_PARTY_REL = 'noopener noreferrer';
/** `utm_medium` for every own-site cross-property link. */
export const ECOSYSTEM_UTM_MEDIUM = 'ecosystem';

export interface EcosystemLink {
  href: string;
  rel: string;
}

export interface EcosystemLinkOptions {
  /** Which surface the link sits on. */
  surface: EcosystemSurface;
  /**
   * Host of the page the link is rendered on, e.g. `window.location.hostname`.
   * Omitted, empty or non-public: the link gets the own-site `rel` but no UTM.
   */
  originHost?: string | null;
  /** Registrable MADFAM domains; a host equal to one, or a subdomain of one, is own. */
  ownedDomains: readonly string[];
}

/** Lower-cases a host and drops a trailing dot and a leading `www.`. */
export function normalizeHost(host: string): string {
  return host
    .trim()
    .toLowerCase()
    .replace(/\.$/, '')
    .replace(/^www\./, '');
}

/** True when `host` is one of `ownedDomains` or a subdomain of one. */
export function isOwnHost(host: string, ownedDomains: readonly string[]): boolean {
  const candidate = normalizeHost(host);
  if (!candidate) return false;
  return ownedDomains.some((domain) => {
    const owned = normalizeHost(domain);
    return owned !== '' && (candidate === owned || candidate.endsWith(`.${owned}`));
  });
}

const LOCAL_SUFFIXES = ['.localhost', '.local', '.test', '.internal', '.example', '.invalid'];

/**
 * True for a hostname that can name a real site in `utm_source`: it has a dot,
 * is not an IP literal and is not a local or reserved name.
 */
export function isPublicHost(host: string): boolean {
  const h = normalizeHost(host);
  if (!h || !h.includes('.')) return false;
  if (h.includes(':') || h.startsWith('[')) return false; // IPv6 literal
  if (/^\d{1,3}(\.\d{1,3}){3}$/.test(h)) return false; // IPv4 literal
  return !LOCAL_SUFFIXES.some((suffix) => h.endsWith(suffix));
}

/**
 * Resolves the `href` and `rel` for one cross-property link under the policy
 * above. Pure and deterministic: callers pass the origin host explicitly.
 */
export function ecosystemLink(url: string, options: EcosystemLinkOptions): EcosystemLink {
  let parsed: URL;
  try {
    parsed = new URL(url);
  } catch {
    return { href: url, rel: THIRD_PARTY_REL };
  }
  if (parsed.protocol !== 'https:' && parsed.protocol !== 'http:') {
    return { href: url, rel: THIRD_PARTY_REL };
  }
  if (!isOwnHost(parsed.hostname, options.ownedDomains)) {
    return { href: url, rel: THIRD_PARTY_REL };
  }

  const origin = options.originHost ? normalizeHost(options.originHost) : '';
  const sameHost = origin !== '' && origin === normalizeHost(parsed.hostname);
  if (!isPublicHost(origin) || sameHost || parsed.searchParams.has('utm_source')) {
    return { href: url, rel: OWN_SITE_REL };
  }

  parsed.searchParams.set('utm_source', origin);
  parsed.searchParams.set('utm_medium', ECOSYSTEM_UTM_MEDIUM);
  parsed.searchParams.set('utm_campaign', options.surface);
  return { href: parsed.toString(), rel: OWN_SITE_REL };
}
