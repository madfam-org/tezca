"""DOF exchange-rate (tipo de cambio) sources — the ingestion side of the
fiscal-value oracle for FX.

Tezca is the ecosystem's fiscal-value oracle (see ``fiscal_views.py``). The DOF
publishes a daily reference USD/MXN rate (*tipo de cambio para solventar
obligaciones*), the SAT-defensible rate for foreign-currency fiscal figures.
Consumers — dhanam's ``fx`` module for its ``dof`` rate type, karafiel for CFDI
amounts — read that rate from Tezca instead of each hitting an upstream feed.

This module is deliberately **pluggable** so the upstream can change without
touching the model, endpoint, or consumers:

    OperatorSource     — the live baseline. No network. The rate is entered by
                         an operator (admin) or the seed command, exactly like
                         UMA / salario mínimo are today. provenance=OPERATOR.
    DofOpenDataSource  — best-effort automated fetch from the DOF SIDOF JSON
                         service. The exact tipo-de-cambio nota shape is not yet
                         verified against a live publication, so this source is
                         defensive: it returns None (never a guess) on anything
                         it does not recognize, and is OFF by default.
    BanxicoSieSource   — token-ready stub for Banxico SIE series SF60653 (the
                         official DOF reference series). Becomes the primary
                         automated source once BANXICO_SIE_TOKEN is provisioned;
                         reliable JSON, so it supersedes DofOpenDataSource.

Which source is active is chosen by ``settings.DOF_FX_SOURCE`` (default
``"operator"``). Ingestion is append-only: a new business-day rate is a new
``TipoDeCambio`` row, never an edit — mirroring the rest of the fiscal feed.
"""

from __future__ import annotations

import datetime
import logging
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Optional, Protocol

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TipoDeCambioObservation:
    """One observed DOF exchange rate, source-agnostic.

    ``value`` is units of ``to_currency`` per one unit of ``from_currency``
    (MXN per 1 USD). ``dof_date`` is the DOF publication date; ``vigencia_from``
    is the day the rate is in force (normally the same date the DOF publishes
    it for). Kept as ``Decimal`` end to end — never float — because this feeds
    a fiscal amount.
    """

    value: Decimal
    dof_date: datetime.date
    vigencia_from: datetime.date
    from_currency: str = "USD"
    to_currency: str = "MXN"
    source_citation: str = ""
    source_url: str = ""


class TipoDeCambioSource(Protocol):
    """A source that can (best-effort) fetch the DOF rate for a date."""

    name: str

    def fetch(
        self, on: datetime.date, from_currency: str, to_currency: str
    ) -> Optional[TipoDeCambioObservation]:
        """Return the DOF rate in force on ``on``, or None if unavailable.

        A source MUST return None rather than raise or guess when it cannot
        produce a rate it is confident in — the caller fails closed, and a
        wrong FX figure on a fiscal document is worse than an absent one.
        """
        ...


def _to_decimal(raw: object) -> Optional[Decimal]:
    """Parse a rate string to Decimal without a float round-trip. None if junk."""
    if raw is None:
        return None
    try:
        d = Decimal(str(raw).strip().replace(",", ""))
    except (InvalidOperation, ValueError):
        return None
    return d if d > 0 else None


class OperatorSource:
    """The baseline: no automated fetch. Rates arrive via the admin or the
    seed command (``provenance=OPERATOR``/``seed-unverified``). ``fetch`` always
    returns None, so ``ingest`` is a no-op — the endpoint serves whatever an
    operator has published, and fails closed otherwise."""

    name = "operator"

    def fetch(
        self, on: datetime.date, from_currency: str, to_currency: str
    ) -> Optional[TipoDeCambioObservation]:
        return None


class BanxicoSieSource:
    """Banxico SIE series SF60653 — the official DOF USD/MXN reference series.

    This is the reliable automated path and the intended primary source once a
    Banxico token is provisioned. Stubbed until then: without a token it opts
    out (returns None), never blocking the operator baseline.
    """

    name = "banxico_sie"
    # SF60653 = "Tipo de cambio para solventar obligaciones ... (FIX/DOF)".
    SERIES_USD_MXN = "SF60653"
    BASE_URL = "https://www.banxico.org.mx/SieAPIRest/service/v1/series"

    def __init__(self, token: str = "") -> None:
        self._token = token or ""

    def fetch(
        self, on: datetime.date, from_currency: str, to_currency: str
    ) -> Optional[TipoDeCambioObservation]:
        if not self._token:
            logger.info("BanxicoSieSource: no token configured — opting out.")
            return None
        if (from_currency, to_currency) != ("USD", "MXN"):
            return None  # SF60653 is USD/MXN only.

        from apps.scraper.http import government_session

        d = on.strftime("%Y-%m-%d")
        url = f"{self.BASE_URL}/{self.SERIES_USD_MXN}/datos/{d}/{d}?token={self._token}"
        try:
            session = government_session(self.BASE_URL)
            resp = session.get(url, timeout=15)
            resp.raise_for_status()
            series = resp.json()["bmx"]["series"][0]
            datos = series.get("datos") or []
            if not datos:
                return None
            value = _to_decimal(datos[-1].get("dato"))
            if value is None:
                return None
            return TipoDeCambioObservation(
                value=value,
                dof_date=on,
                vigencia_from=on,
                from_currency="USD",
                to_currency="MXN",
                source_citation=f"Banxico SIE {self.SERIES_USD_MXN} ({on.isoformat()})",
                source_url=f"{self.BASE_URL}/{self.SERIES_USD_MXN}",
            )
        except Exception as exc:  # noqa: BLE001 — best-effort source, never raise
            logger.warning("BanxicoSieSource fetch failed for %s: %s", on, exc)
            return None


class DofOpenDataSource:
    """Best-effort fetch from the DOF SIDOF JSON service.

    STATUS: the SIDOF ``diarios`` endpoint responds with structured JSON, but
    the exact envelope for the *Banco de México — tipo de cambio* nota has not
    yet been verified against a live publication from this environment. Until
    an operator confirms the shape (and the parser below is pinned to it), this
    source stays OFF by default and returns None on anything it cannot parse
    with confidence — it never returns a guessed rate. When ``BANXICO_SIE_TOKEN``
    lands, ``BanxicoSieSource`` supersedes this entirely.
    """

    name = "dof_open_data"
    BASE_URL = "https://sidof.segob.gob.mx/dof/sidof"

    def fetch(
        self, on: datetime.date, from_currency: str, to_currency: str
    ) -> Optional[TipoDeCambioObservation]:
        if (from_currency, to_currency) != ("USD", "MXN"):
            return None

        from apps.scraper.http import government_session

        url = f"{self.BASE_URL}/diarios/{on.strftime('%Y-%m-%d')}"
        try:
            session = government_session(self.BASE_URL)
            resp = session.get(url, timeout=20, headers={"Accept": "application/json"})
            resp.raise_for_status()
            payload = resp.json()
        except Exception as exc:  # noqa: BLE001 — best-effort source, never raise
            logger.warning("DofOpenDataSource fetch failed for %s: %s", on, exc)
            return None

        value = self._extract_rate(payload)
        if value is None:
            logger.info(
                "DofOpenDataSource: no tipo-de-cambio nota parsed for %s "
                "(unverified endpoint shape — returning None).",
                on,
            )
            return None
        return TipoDeCambioObservation(
            value=value,
            dof_date=on,
            vigencia_from=on,
            from_currency="USD",
            to_currency="MXN",
            source_citation=f"DOF {on.strftime('%d-%m-%Y')}, Banco de México",
            source_url="https://www.dof.gob.mx/",
        )

    @staticmethod
    def _extract_rate(payload: object) -> Optional[Decimal]:
        """Pull the USD/MXN rate from a SIDOF diarios payload.

        Deliberately conservative: walks the notas looking for a Banco de
        México tipo-de-cambio entry that carries an explicit numeric rate
        field, and returns None the moment the shape is unfamiliar. This is a
        placeholder pinned to be safe, NOT verified against a live nota — do
        not treat a non-None result here as authoritative until the endpoint
        shape is confirmed and this parser is tightened.
        """
        if not isinstance(payload, dict):
            return None
        diarios = payload.get("ListaDiarios")
        if not isinstance(diarios, list):
            return None
        for diario in diarios:
            if not isinstance(diario, dict):
                continue
            for key in ("Notas", "ListaNotas", "notas"):
                notas = diario.get(key)
                if not isinstance(notas, list):
                    continue
                for nota in notas:
                    if not isinstance(nota, dict):
                        continue
                    title = str(
                        nota.get("titulo")
                        or nota.get("nombre")
                        or nota.get("title")
                        or ""
                    ).upper()
                    if "CAMBIO" not in title and "BANCO DE M" not in title:
                        continue
                    for rate_key in ("tipoCambio", "valor", "rate", "dato"):
                        value = _to_decimal(nota.get(rate_key))
                        if value is not None:
                            return value
        return None


_SOURCES = {
    OperatorSource.name: OperatorSource,
    DofOpenDataSource.name: DofOpenDataSource,
    BanxicoSieSource.name: BanxicoSieSource,
}


def get_source(name: str = "", token: str = "") -> TipoDeCambioSource:
    """Resolve the configured DOF-FX source. Falls back to the operator
    baseline for an unknown name (never raises — the baseline always works)."""
    key = (name or "operator").strip().lower()
    cls = _SOURCES.get(key, OperatorSource)
    if cls is BanxicoSieSource:
        return cls(token=token)
    return cls()


def ingest_tipo_de_cambio(
    *,
    on: Optional[datetime.date] = None,
    from_currency: str = "USD",
    to_currency: str = "MXN",
    source_name: str = "operator",
    token: str = "",
    provenance: Optional[str] = None,
) -> Optional["object"]:
    """Fetch the DOF rate for ``on`` from the configured source and upsert a
    ``TipoDeCambio`` row (append-only on the natural key). Returns the row, or
    None when the source produced nothing (the operator baseline always does).

    Never overwrites a row an operator promoted to ``published`` — the fetch is
    a floor, not an authority, matching the seed command's contract.
    """
    from apps.api.fiscal_models import Provenance, TipoDeCambio

    on = on or datetime.date.today()
    source = get_source(source_name, token=token)
    obs = source.fetch(on, from_currency, to_currency)
    if obs is None:
        return None

    row_provenance = provenance or Provenance.PUBLISHED
    existing = TipoDeCambio.objects.filter(
        from_currency=obs.from_currency,
        to_currency=obs.to_currency,
        vigencia_from=obs.vigencia_from,
    ).first()
    if existing is not None:
        # Append-only: never rewrite an already-published rate for that day.
        return existing

    return TipoDeCambio.objects.create(
        from_currency=obs.from_currency,
        to_currency=obs.to_currency,
        value=obs.value,
        unit="MXN",
        vigencia_from=obs.vigencia_from,
        vigencia_to=None,
        dof_date=obs.dof_date,
        source_citation=obs.source_citation,
        source_url=obs.source_url,
        provenance=row_provenance,
    )
