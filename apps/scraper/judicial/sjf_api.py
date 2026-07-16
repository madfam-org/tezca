"""
SJF tesis microservice API client (fix for issue #142).

The SJF portal (sjf2.scjn.gob.mx) is an Angular SPA whose search results
come from a public JSON microservice. DOM scraping against the SPA is
fragile (Material classes churn per release and the old CSS selectors
matched nothing, producing empty records), but the underlying API is
stable, self-describing, and returns every field the judicial pipeline
needs — including full ``texto`` and ``precedentes`` on the detail
endpoint, which the DOM never rendered in the result list at all.

Contract (captured from the live SPA on 2026-07-15):

List:
    POST /services/sjftesismicroservice/api/public/tesis?page=N&size=M
    body: {"classifiers": [{"name": "epoca", "value": ["Undécima Época"]},
                           {"name": "tipoTesis", "value": ["Jurisprudencia"]},
                           {"name": "tipoDocumento", "value": ["1"]}],
           "searchTerms": [], "bFacet": false, "ius": [],
           "idApp": "SJFAPP2020", "lbSearch": [], "filterExpression": ""}
    → {"documents": [...], "classifiers": [facets], "total": N, "totalPage": N}

Detail:
    GET /services/sjftesismicroservice/api/public/tesis/{ius}
        ?isSemanal=<bool>&hostName=https://sjf2.scjn.gob.mx
    → full record incl. texto, precedentes, claveTesis, materias

The endpoints reject requests without browser-shaped Origin/Referer
headers ("Acceso denegado: Formato inválido"), so the session sends them.
"""

import html
import logging
import re
import time
from typing import Any, Dict, List, Optional, Tuple

import requests

logger = logging.getLogger(__name__)

SJF_API_BASE = "https://sjf2.scjn.gob.mx"
SJF_API_TESIS = f"{SJF_API_BASE}/services/sjftesismicroservice/api/public/tesis"
SJF_APP_ID = "SJFAPP2020"

# Public detail-page URL for humans (kept identical to the old scraper output
# so downstream consumers / ingest dedup see stable URLs).
SJF_PUBLIC_DETAIL_URL = f"{SJF_API_BASE}/detalle/tesis"

# The API filters épocas by their accented display label (the repo-level
# EPOCAS map in scjn_scraper.py is intentionally unaccented for metadata).
EPOCA_API_LABELS = {
    1: "Primera Época",
    2: "Segunda Época",
    3: "Tercera Época",
    4: "Cuarta Época",
    5: "Quinta Época",
    6: "Sexta Época",
    7: "Séptima Época",
    8: "Octava Época",
    9: "Novena Época",
    10: "Décima Época",
    11: "Undécima Época",
    12: "Duodécima Época",
}

TIPO_API_LABELS = {
    "jurisprudencia": "Jurisprudencia",
    "tesis_aislada": "Aislada",
}

_REQUEST_TIMEOUT = 30  # seconds
_RATE_LIMIT_SECONDS = 1.0  # politeness floor between API calls

_TAG_RE = re.compile(r"<[^>]+>")


class SjfApiError(Exception):
    """Raised when the SJF microservice rejects or garbles a request."""


def build_list_body(epoca: int, tipo: str) -> Dict[str, Any]:
    """Build the POST body for the tesis list endpoint.

    Shared by the direct requests path (SjfApiClient) and the in-page
    browser fallback (ScjnPlaywrightScraper), so both speak the exact
    same contract.
    """
    epoca_label = EPOCA_API_LABELS.get(epoca)
    if not epoca_label:
        raise SjfApiError(f"Unknown época: {epoca}")
    tipo_label = TIPO_API_LABELS.get(tipo)
    if not tipo_label:
        raise SjfApiError(f"Unknown tipo: {tipo}")

    return {
        "classifiers": [
            {
                "name": "epoca",
                "value": [epoca_label],
                "allSelected": False,
                "visible": False,
                "isMatrix": False,
            },
            {
                "name": "tipoTesis",
                "value": [tipo_label],
                "allSelected": False,
                "visible": False,
                "isMatrix": False,
            },
            {
                "name": "tipoDocumento",
                "value": ["1"],
                "allSelected": False,
                "visible": False,
                "isMatrix": False,
            },
        ],
        "searchTerms": [],
        "bFacet": False,
        "ius": [],
        "idApp": SJF_APP_ID,
        "lbSearch": [],
        "filterExpression": "",
    }


def strip_html(value: Optional[str]) -> str:
    """Strip tags and unescape entities from API HTML fragments."""
    if not value:
        return ""
    return html.unescape(_TAG_RE.sub("", value)).strip()


class SjfApiClient:
    """Minimal client for the public SJF tesis microservice."""

    def __init__(self, session: Optional[requests.Session] = None) -> None:
        self._session = session or requests.Session()
        self._session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/126.0 Safari/537.36"
                ),
                "Accept": "application/json, text/plain, */*",
                "Origin": SJF_API_BASE,
                "Referer": f"{SJF_API_BASE}/listado-resultado-tesis",
            }
        )
        self._last_request_ts = 0.0

    # ------------------------------------------------------------------
    # HTTP plumbing
    # ------------------------------------------------------------------

    def _rate_limit(self) -> None:
        elapsed = time.monotonic() - self._last_request_ts
        if elapsed < _RATE_LIMIT_SECONDS:
            time.sleep(_RATE_LIMIT_SECONDS - elapsed)
        self._last_request_ts = time.monotonic()

    def _check(self, resp: requests.Response, what: str) -> Dict[str, Any]:
        if resp.status_code != 200:
            raise SjfApiError(
                f"SJF API {what} returned HTTP {resp.status_code}: "
                f"{resp.text[:200]}"
            )
        try:
            return resp.json()
        except ValueError as exc:
            raise SjfApiError(f"SJF API {what} returned non-JSON body") from exc

    # ------------------------------------------------------------------
    # Endpoints
    # ------------------------------------------------------------------

    def list_tesis(
        self,
        epoca: int,
        tipo: str = "jurisprudencia",
        page: int = 0,
        size: int = 50,
    ) -> Tuple[List[Dict[str, Any]], int, int]:
        """Fetch one page of tesis for an época/tipo.

        Returns:
            (documents, total, total_pages)
        """
        body = build_list_body(epoca, tipo)

        self._rate_limit()
        resp = self._session.post(
            SJF_API_TESIS,
            params={"page": page, "size": size},
            json=body,
            timeout=_REQUEST_TIMEOUT,
        )
        data = self._check(resp, f"list(epoca={epoca}, page={page})")
        documents = data.get("documents") or []
        total = int(data.get("total") or 0)
        total_pages = int(data.get("totalPage") or 0)
        return documents, total, total_pages

    def fetch_detail(self, ius: Any, semanal: bool = False) -> Dict[str, Any]:
        """Fetch the full record (texto, precedentes, ...) for one tesis."""
        self._rate_limit()
        resp = self._session.get(
            f"{SJF_API_TESIS}/{ius}",
            params={
                "isSemanal": "true" if semanal else "false",
                "hostName": SJF_API_BASE,
            },
            timeout=_REQUEST_TIMEOUT,
        )
        return self._check(resp, f"detail(ius={ius})")


def doc_to_record(
    doc: Dict[str, Any],
    epoca: int,
    epoca_nombre: str,
    tipo: str,
) -> Dict[str, Any]:
    """Map an API list document onto the canonical judicial record schema.

    Keeps the exact field set ``ScjnPlaywrightScraper._make_record`` has
    always produced so batches stay compatible with
    ``ingest_judicial_batches`` and existing dedup keys.
    """
    registro = str(doc.get("ius") or doc.get("id") or "").strip()
    instancia = strip_html(doc.get("instanciaAbr") or doc.get("sala") or "")
    return {
        "registro": registro,
        "tipo": tipo,
        "epoca": epoca,
        "epoca_nombre": epoca_nombre,
        "instancia": instancia,
        "materia": strip_html(doc.get("materias") or ""),
        "tesis_num": strip_html(doc.get("claveTesis") or ""),
        "rubro": strip_html(doc.get("rubro") or ""),
        "texto": strip_html(doc.get("texto") or ""),
        "precedentes": strip_html(doc.get("precedentes") or ""),
        "url": f"{SJF_PUBLIC_DETAIL_URL}/{registro}" if registro else "",
        "source": "sjf_scjn_api",
        # ingest_judicial reads these when present; the DOM scraper never
        # had them, the API does.
        "fuente": strip_html(doc.get("fuente") or ""),
        "fecha_publicacion": (doc.get("fechaPublicacion") or "")[:10] or None,
        # Not part of the legacy schema, but required to pick the right
        # detail-endpoint variant; ingest ignores unknown keys.
        "semanal": bool(doc.get("semanal")),
    }
