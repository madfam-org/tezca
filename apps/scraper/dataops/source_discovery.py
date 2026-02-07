"""
Source Discovery: Finds alternative sources for laws when primary sources fail.

Tier 1 escalation: probes known URL patterns, Internet Archive Wayback Machine,
and state congress portals to locate alternative data sources.
"""

import logging
from urllib.parse import quote

import requests

from .models import DataSource

logger = logging.getLogger(__name__)

DISCOVERY_TIMEOUT = 15  # seconds

# URL patterns for state congress/legislature portals
STATE_CONGRESS_PATTERNS = [
    "https://www.congreso{state_slug}.gob.mx/legislacion",
    "https://www.congreso{state_slug}.gob.mx/leyes",
    "https://congreso{state_slug}.gob.mx/legislacion",
    "https://congreso{state_slug}.gob.mx/leyes",
    "https://www.{state_slug}.gob.mx/legislacion",
    "https://legislatura{state_slug}.gob.mx/",
    "https://www.congresodel{state_slug}.gob.mx/legislacion",
]

# Known congress portal URLs that don't follow standard patterns
KNOWN_CONGRESS_PORTALS = {
    "Aguascalientes": "https://www.congresoags.gob.mx/",
    "Baja California": "https://www.congresobc.gob.mx/",
    "Baja California Sur": "https://www.cbcs.gob.mx/",
    "Campeche": "https://congresocam.gob.mx/",
    "Chiapas": "https://www.congresochiapas.gob.mx/",
    "Chihuahua": "https://www.congresochihuahua.gob.mx/",
    "Ciudad de México": "https://www.congresocdmx.gob.mx/",
    "Coahuila": "https://congresocoahuila.gob.mx/",
    "Colima": "https://www.congresocol.gob.mx/",
    "Durango": "https://congresodurango.gob.mx/",
    "Estado de México": "https://www.legislaturaedomex.gob.mx/",
    "Guanajuato": "https://www.congresogto.gob.mx/",
    "Guerrero": "https://congresogro.gob.mx/",
    "Hidalgo": "https://www.congreso-hidalgo.gob.mx/",
    "Jalisco": "https://www.congresojal.gob.mx/",
    "Michoacán": "https://congresomich.gob.mx/",
    "Morelos": "https://congresoMorelos.gob.mx/",
    "Nayarit": "https://www.congresonay.gob.mx/",
    "Nuevo León": "https://www.hcnl.gob.mx/",
    "Oaxaca": "https://congresooaxaca.gob.mx/",
    "Puebla": "https://www.congresopuebla.gob.mx/",
    "Querétaro": "https://www.legislaturaqueretaro.gob.mx/",
    "Quintana Roo": "https://congresoqroo.gob.mx/",
    "San Luis Potosí": "https://congresosanluis.gob.mx/",
    "Sinaloa": "https://www.congresosinaloa.gob.mx/",
    "Sonora": "https://www.congresoson.gob.mx/",
    "Tabasco": "https://congresotabasco.gob.mx/",
    "Tamaulipas": "https://www.congresotamaulipas.gob.mx/",
    "Tlaxcala": "https://congresodetlaxcala.gob.mx/",
    "Veracruz": "https://www.legisver.gob.mx/",
    "Yucatán": "https://www.congresoyucatan.gob.mx/",
    "Zacatecas": "https://www.congresozac.gob.mx/",
}

# Periodico Oficial patterns
PERIODICO_OFICIAL_PATTERNS = [
    "https://periodico.{state_slug}.gob.mx/",
    "https://po.{state_slug}.gob.mx/",
    "https://www.{state_slug}.gob.mx/periodico-oficial",
]

# Wayback Machine API
WAYBACK_API_URL = "https://archive.org/wayback/available"


def _slugify_state(state_name):
    """Convert state name to URL-friendly slug."""
    replacements = {
        "á": "a",
        "é": "e",
        "í": "i",
        "ó": "o",
        "ú": "u",
        "ñ": "n",
        "ü": "u",
        "Á": "A",
        "É": "E",
        "Í": "I",
        "Ó": "O",
        "Ú": "U",
        "Ñ": "N",
    }
    slug = state_name.lower()
    for src, dst in replacements.items():
        slug = slug.replace(src, dst)
    slug = slug.replace(" de ", "").replace(" ", "")
    return slug


class SourceDiscoverer:
    """Discovers alternative data sources for Tier 1 escalation."""

    def search_state_alternatives(self, state_name):
        """Search for alternative law sources for a given state.

        Checks known congress portals and probes URL patterns.

        Returns:
            List of dicts with discovered sources: {url, type, accessible, note}
        """
        discovered = []

        # 1. Check known congress portal
        known_url = KNOWN_CONGRESS_PORTALS.get(state_name)
        if known_url:
            accessible = self._probe_url(known_url)
            discovered.append(
                {
                    "url": known_url,
                    "type": "congress_portal",
                    "accessible": accessible,
                    "note": "Known congress portal URL",
                }
            )

        # 2. Probe URL patterns
        state_slug = _slugify_state(state_name)
        for pattern in STATE_CONGRESS_PATTERNS:
            url = pattern.format(state_slug=state_slug)
            if url == known_url:
                continue
            accessible = self._probe_url(url)
            if accessible:
                discovered.append(
                    {
                        "url": url,
                        "type": "congress_portal",
                        "accessible": accessible,
                        "note": "Discovered via URL pattern probe",
                    }
                )

        # 3. Check Periodico Oficial
        for pattern in PERIODICO_OFICIAL_PATTERNS:
            url = pattern.format(state_slug=state_slug)
            accessible = self._probe_url(url)
            if accessible:
                discovered.append(
                    {
                        "url": url,
                        "type": "periodico_oficial",
                        "accessible": accessible,
                        "note": "State official gazette",
                    }
                )

        return discovered

    def check_wayback(self, url):
        """Query Internet Archive Wayback Machine for archived versions.

        Args:
            url: URL to check for archived versions

        Returns:
            Dict with archive info or None if not archived
        """
        try:
            response = requests.get(
                WAYBACK_API_URL,
                params={"url": url},
                timeout=DISCOVERY_TIMEOUT,
                headers={"User-Agent": "Tezca-SourceDiscovery/1.0"},
            )
            if response.status_code == 200:
                data = response.json()
                snapshot = data.get("archived_snapshots", {}).get("closest")
                if snapshot and snapshot.get("available"):
                    return {
                        "archive_url": snapshot["url"],
                        "timestamp": snapshot.get("timestamp", ""),
                        "status": snapshot.get("status", ""),
                    }
        except requests.RequestException as e:
            logger.warning("Wayback API error for %s: %s", url, e)

        return None

    def validate_discovered_source(self, url):
        """Check if a discovered URL is a valid law source.

        Validates accessibility, content type, and whether
        it appears to contain law/legislation content.

        Returns:
            Dict with validation results
        """
        result = {
            "url": url,
            "accessible": False,
            "content_type": None,
            "has_pdf_links": False,
            "has_law_keywords": False,
        }

        try:
            response = requests.get(
                url,
                timeout=DISCOVERY_TIMEOUT,
                headers={"User-Agent": "Tezca-SourceDiscovery/1.0"},
                allow_redirects=True,
            )
            result["accessible"] = response.status_code == 200
            result["content_type"] = response.headers.get("Content-Type", "")

            if response.status_code == 200 and "text/html" in result["content_type"]:
                text = response.text.lower()
                result["has_pdf_links"] = ".pdf" in text
                law_keywords = [
                    "legislaci",
                    "ley",
                    "codigo",
                    "código",
                    "reglamento",
                    "decreto",
                ]
                result["has_law_keywords"] = any(kw in text for kw in law_keywords)

        except requests.RequestException as e:
            logger.debug("Validation failed for %s: %s", url, e)

        return result

    def discover_for_gap(self, gap_record):
        """Run full discovery pipeline for a GapRecord.

        Returns:
            List of discovered sources
        """
        discovered = []

        if gap_record.state:
            # Search for state alternatives
            state_results = self.search_state_alternatives(gap_record.state)
            discovered.extend(state_results)

        # Check Wayback for the original source URL
        if gap_record.source and gap_record.source.base_url:
            archive = self.check_wayback(gap_record.source.base_url)
            if archive:
                discovered.append(
                    {
                        "url": archive["archive_url"],
                        "type": "wayback_archive",
                        "accessible": True,
                        "note": f"Archived on {archive['timestamp']}",
                    }
                )

        return discovered

    def _probe_url(self, url):
        """Check if a URL is accessible (HTTP 200)."""
        try:
            response = requests.head(
                url,
                timeout=DISCOVERY_TIMEOUT,
                headers={"User-Agent": "Tezca-SourceDiscovery/1.0"},
                allow_redirects=True,
            )
            return response.status_code == 200
        except requests.RequestException:
            return False
