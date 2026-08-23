"""
Tests for the SEP calendario fetcher
(apps/scraper/federal/sep_calendario_scraper.py).

Network-free: every test mocks the requests session. The interesting logic
is in ``parse_articles`` (DOF note HTML → one entry per ARTÍCULO, including
the DOF's split "ARTÍCULO" / "PRIMERO.-" heading), ``build_akn`` (per-article
addressable articles for index_laws), ``extract_calendar_dates`` (the
machine-readable artifact kalya consumes), and the pinned corpus + dates
registries.

The HTML fixture reproduces the real DOF/SIDOF quirks observed in note
5793645 on 2026-08-22:
  - a heading split across two lines: "ARTÍCULO" then "PRIMERO.-"
  - the following headings inline: "ARTÍCULO SEGUNDO.-"
  - mid-sentence column wraps ("2026-\n2027")
  - the transitorios (whose own "PRIMERO.-"/"SEGUNDO.-" must NOT be read as
    articles)
"""

from unittest.mock import MagicMock, patch

import pytest

from apps.scraper.federal.sep_calendario_scraper import (
    SEP_CALENDAR_DATES,
    SEP_CALENDAR_DOCUMENTS,
    SEP_CALENDAR_DOCUMENTS_BY_CICLO,
    SEP_CALENDAR_DOCUMENTS_BY_ID,
    SEP_CATEGORY,
    SEP_DOMAINS,
    SepCalendarDocument,
    SepCalendarFetcher,
    build_akn,
    extract_calendar_dates,
    parse_articles,
    validate_article_sequence,
)

# ---------------------------------------------------------------------------
# Fixtures — the real acuerdo body shape (note 5793645)
# ---------------------------------------------------------------------------

ACUERDO_HTML = """
<html><head><title>ACUERDO número 07/07/26 por el que se establecen los calendarios escolares para el ciclo lectivo 2026-2027</title></head>
<body>
<p>ACUERDO</p>
<p>número 07/07/26 por el que se establecen los calendarios escolares para el ciclo lectivo 2026-2027.</p>
<p>MARIO DELGADO CARRILLO, Secretario de Educación Pública, con fundamento en los artículos 38 de la Ley Orgánica</p>
<p>CONSIDERANDO</p>
<p>Que el artículo 3o. de la Constitución Política de los Estados Unidos Mexicanos establece la educación básica.</p>
<p>ARTÍCULO</p>
<p>PRIMERO.-</p>
<p>Se establece el calendario escolar de ciento ochenta y cinco días para el ciclo lectivo 2026-</p>
<p>2027, aplicable en toda la República para las escuelas de educación preescolar, primaria y secundaria.</p>
<p>ARTÍCULO SEGUNDO.-</p>
<p>Se establece el calendario escolar de ciento noventa días para el ciclo lectivo 2026-2027, aplicable a la educación normal.</p>
<p>ARTÍCULO TERCERO.-</p>
<p>Para la aplicación de los calendarios escolares el inicio de cursos será el lunes 31 de agosto de 2026,</p>
<p>concluyendo para la educación preescolar, primaria y secundaria el viernes 9 de julio de 2027.</p>
<p>TRANSITORIOS</p>
<p>PRIMERO.- El presente Acuerdo entrará en vigor al día siguiente de su publicación.</p>
<p>SEGUNDO.- Se abroga el Acuerdo número 18/06/25 publicado el 9 de junio de 2025.</p>
</body></html>
"""

# A note whose title marker does NOT match — an opaque codigo resolving to
# the wrong instrument (the failure mode the identity guard exists to catch).
WRONG_NOTE_HTML = """
<html><head><title>EDICTO judicial de un juzgado de distrito</title></head>
<body><p>Se notifica a las partes el presente edicto en materia mercantil.</p></body></html>
"""


@pytest.fixture
def fetcher(tmp_path):
    return SepCalendarFetcher(output_dir=str(tmp_path))


def _response(text, status=200):
    resp = MagicMock()
    resp.text = text
    resp.status_code = status
    resp.raise_for_status = MagicMock()
    return resp


# ---------------------------------------------------------------------------
# The pinned corpus
# ---------------------------------------------------------------------------


class TestSepCalendarRegistry:
    """The enumerated SEP calendario corpus must stay internally consistent."""

    def test_official_ids_are_unique(self):
        ids = [doc.official_id for doc in SEP_CALENDAR_DOCUMENTS]
        assert len(ids) == len(set(ids))

    def test_by_id_and_by_ciclo_indexes_match_list(self):
        assert set(SEP_CALENDAR_DOCUMENTS_BY_ID) == {
            d.official_id for d in SEP_CALENDAR_DOCUMENTS
        }
        assert set(SEP_CALENDAR_DOCUMENTS_BY_CICLO) == {
            d.ciclo for d in SEP_CALENDAR_DOCUMENTS
        }

    def test_2026_2027_acuerdo_identity(self):
        doc = SEP_CALENDAR_DOCUMENTS_BY_CICLO["2026-2027"]
        assert doc.official_id == "sep-calendario-escolar-2026-2027"
        assert doc.status == "vigente"
        assert doc.document_type == "acuerdo"
        # Verified against DOF primary text 2026-08-22.
        assert doc.dof_codigo == "5793645"
        assert doc.publication_date == "2026-07-15"
        # Transitorio Primero: in force the day after publication.
        assert doc.valid_from == "2026-07-16"

    def test_no_document_is_typed_as_a_ley(self):
        """The SEP calendario is an acuerdo, not a ley. Mislabeling it would
        propagate the lie to every consumer of the corpus."""
        for doc in SEP_CALENDAR_DOCUMENTS:
            assert doc.document_type == "acuerdo"

    def test_every_document_carries_education_domain_and_category(self):
        for doc in SEP_CALENDAR_DOCUMENTS:
            assert doc.category == SEP_CATEGORY == "calendario_escolar"
            assert doc.domains == SEP_DOMAINS
            assert "education" in doc.domains

    def test_every_document_has_a_vigencia_note(self):
        for doc in SEP_CALENDAR_DOCUMENTS:
            assert doc.vigencia_note.strip(), doc.official_id

    def test_dof_and_sidof_urls_are_derived_from_the_codigo(self):
        doc = SEP_CALENDAR_DOCUMENTS_BY_CICLO["2026-2027"]
        assert doc.sidof_url == "https://sidof.segob.gob.mx/notas/docFuente/5793645"
        # DOF wants DD/MM/YYYY, not the ISO date we store.
        assert doc.dof_url == (
            "https://dof.gob.mx/nota_detalle.php?codigo=5793645&fecha=15/07/2026"
        )

    def test_official_ids_fit_the_law_model_column(self):
        from apps.api.models import Law

        for doc in SEP_CALENDAR_DOCUMENTS:
            assert len(doc.official_id) <= Law.OFFICIAL_ID_MAX_LENGTH

    def test_ciclo_label_is_consecutive_years(self):
        """kalya keys its OrganizationalCalendar on a 'YYYY-YYYY' ciclo of
        consecutive years — the year-over-year identity."""
        for doc in SEP_CALENDAR_DOCUMENTS:
            start, end = doc.ciclo.split("-")
            assert int(end) == int(start) + 1


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------


class TestParseArticles:
    """parse_articles: DOF note HTML → one entry per ARTÍCULO."""

    def test_extracts_the_three_articles_including_split_heading(self):
        """ARTÍCULO PRIMERO's heading is split across two lines in the real
        note ("ARTÍCULO" / "PRIMERO.-"); the parser must still find it."""
        articles = parse_articles(ACUERDO_HTML)
        nums = [a["num"] for a in articles]
        assert nums == ["ARTÍCULO PRIMERO", "ARTÍCULO SEGUNDO", "ARTÍCULO TERCERO"]

    def test_stops_at_the_transitorios(self):
        """The transitorios' own 'PRIMERO.-'/'SEGUNDO.-' must not be read as
        articles, and their text must not leak into an article body."""
        articles = parse_articles(ACUERDO_HTML)
        assert len(articles) == 3
        joined = " ".join(a["text"] for a in articles)
        assert "entrará en vigor" not in joined
        assert "abroga" not in joined

    def test_rejoins_column_wraps(self):
        """ "2026-\n2027" is a mid-word column wrap; the day count sentence
        must read continuously."""
        articles = parse_articles(ACUERDO_HTML)
        primero = articles[0]["text"]
        assert "ciento ochenta y cinco días" in primero
        assert "2026- 2027" in primero or "2026-2027" in primero

    def test_tercero_carries_the_ciclo_bounds_text(self):
        articles = parse_articles(ACUERDO_HTML)
        tercero = articles[2]["text"]
        assert "31 de agosto de 2026" in tercero
        assert "9 de julio de 2027" in tercero

    def test_returns_empty_for_prose_without_articles(self):
        assert parse_articles(WRONG_NOTE_HTML) == []


class TestValidateArticleSequence:
    def test_clean_sequence_has_no_problems(self):
        assert validate_article_sequence(parse_articles(ACUERDO_HTML)) == []

    def test_empty_is_flagged(self):
        assert validate_article_sequence([]) == ["no articles parsed"]

    def test_gap_is_flagged(self):
        broken = [
            {"num": "ARTÍCULO PRIMERO", "heading": "", "text": "a"},
            {"num": "ARTÍCULO TERCERO", "heading": "", "text": "c"},
        ]
        problems = validate_article_sequence(broken)
        assert problems
        assert any("SEGUNDO" in p for p in problems)


# ---------------------------------------------------------------------------
# AKN emission
# ---------------------------------------------------------------------------


class TestBuildAkn:
    def test_is_parseable_akn_that_index_laws_recognizes(self):
        from lxml import etree

        doc = SEP_CALENDAR_DOCUMENTS_BY_CICLO["2026-2027"]
        xml = build_akn(doc, parse_articles(ACUERDO_HTML))
        # index_laws sniffs for this prefix before choosing the AKN path.
        assert xml.startswith("<?xml")
        root = etree.fromstring(xml.encode("utf-8"))
        ns = {"akn": "http://docs.oasis-open.org/legaldocml/ns/akn/3.0"}
        articles = root.xpath("//akn:article", namespaces=ns)
        assert len(articles) == 3
        # Each article's <num> is the addressable ordinal.
        nums = [a.find("akn:num", ns).text for a in articles]
        assert nums == ["ARTÍCULO PRIMERO", "ARTÍCULO SEGUNDO", "ARTÍCULO TERCERO"]

    def test_escapes_xml_special_characters(self):
        from lxml import etree

        doc = SEP_CALENDAR_DOCUMENTS_BY_CICLO["2026-2027"]
        articles = [{"num": "ARTÍCULO PRIMERO", "heading": "", "text": "a < b & c > d"}]
        xml = build_akn(doc, articles)
        etree.fromstring(xml.encode("utf-8"))  # must not raise
        assert "a &lt; b &amp; c &gt; d" in xml


# ---------------------------------------------------------------------------
# Date extraction (the kalya input contract)
# ---------------------------------------------------------------------------


class TestExtractCalendarDates:
    def test_schema_and_source_header(self):
        artifact = extract_calendar_dates("2026-2027")
        assert artifact["schema"] == "tezca.sep_calendario/v1"
        assert artifact["ciclo"] == "2026-2027"
        assert artifact["nivel"] == "educacion_basica"
        assert artifact["dias_habiles"] == 185
        assert artifact["source"]["dof_codigo"] == "5793645"
        assert artifact["source"]["acuerdo"] == "07/07/26"

    def test_unknown_ciclo_raises(self):
        with pytest.raises(KeyError):
            extract_calendar_dates("2099-2100")

    def test_events_are_sorted_by_date(self):
        events = extract_calendar_dates("2026-2027")["events"]
        dates = [e["date"] for e in events]
        assert dates == sorted(dates)

    def test_every_event_is_sep_sourced_and_traceable(self):
        for event in extract_calendar_dates("2026-2027")["events"]:
            assert event["source"] == "sep"
            assert event["source_ref"].strip()
            # Only kalya taxonomy types appear.
            assert event["type"] in {
                "regreso_a_clases",
                "cierre_ciclo_preescolar",
                "suspension_sep",
                "periodo_vacacional",
                "junta_consejo_tecnico",
            }

    def test_the_nine_suspensiones(self):
        events = extract_calendar_dates("2026-2027")["events"]
        suspensiones = sorted(
            e["date"] for e in events if e["type"] == "suspension_sep"
        )
        assert suspensiones == [
            "2026-09-16",
            "2026-11-02",
            "2026-11-16",
            "2026-12-25",
            "2027-01-01",
            "2027-01-06",
            "2027-02-01",
            "2027-03-15",
            "2027-05-05",
        ]

    def test_the_two_vacation_ranges(self):
        events = extract_calendar_dates("2026-2027")["events"]
        vac = sorted(
            (e["date"], e["end_date"])
            for e in events
            if e["type"] == "periodo_vacacional"
        )
        assert vac == [
            ("2026-12-21", "2027-01-05"),  # winter (regreso Jan 7)
            ("2027-03-22", "2027-04-03"),  # spring (regreso Apr 5)
        ]

    def test_ranges_carry_end_date_and_singles_do_not(self):
        for event in extract_calendar_dates("2026-2027")["events"]:
            if event["type"] in ("periodo_vacacional",):
                assert "end_date" in event
            elif event["type"] in (
                "suspension_sep",
                "regreso_a_clases",
                "cierre_ciclo_preescolar",
            ):
                assert "end_date" not in event

    def test_ciclo_bounds_trace_to_articulo_tercero(self):
        events = extract_calendar_dates("2026-2027")["events"]
        inicio = next(e for e in events if e["type"] == "regreso_a_clases")
        cierre = next(e for e in events if e["type"] == "cierre_ciclo_preescolar")
        assert inicio["date"] == "2026-08-31"
        assert cierre["date"] == "2027-07-09"
        assert "TERCERO" in inicio["source_ref"]
        assert "TERCERO" in cierre["source_ref"]

    def test_eight_ordinary_consejo_tecnico_sessions_plus_intensiva(self):
        events = extract_calendar_dates("2026-2027")["events"]
        cte = [e for e in events if e["type"] == "junta_consejo_tecnico"]
        # 8 ordinarias (single-day) + 1 fase intensiva (a range).
        intensiva = [e for e in cte if e.get("end_date")]
        ordinarias = [e for e in cte if not e.get("end_date")]
        assert len(intensiva) == 1
        assert intensiva[0]["date"] == "2026-08-24"
        assert intensiva[0]["end_date"] == "2026-08-28"
        assert len(ordinarias) == 8

    def test_every_ciclo_in_registry_has_a_dates_bucket(self):
        for doc in SEP_CALENDAR_DOCUMENTS:
            assert doc.ciclo in SEP_CALENDAR_DATES
            # And it extracts without error.
            assert extract_calendar_dates(doc.ciclo)["events"]


# ---------------------------------------------------------------------------
# Fetching
# ---------------------------------------------------------------------------


class TestFetchHtml:
    def test_prefers_sidof(self, fetcher):
        doc = SEP_CALENDAR_DOCUMENTS_BY_CICLO["2026-2027"]
        with patch.object(fetcher, "_session") as session:
            session.get.return_value = _response(ACUERDO_HTML)
            html = fetcher.fetch_html(doc)
        assert html == ACUERDO_HTML
        called = session.get.call_args[0][0]
        assert "sidof.segob.gob.mx" in called

    def test_falls_back_to_dof_when_sidof_misses(self, fetcher):
        import requests

        doc = SEP_CALENDAR_DOCUMENTS_BY_CICLO["2026-2027"]
        miss = MagicMock()
        miss.status_code = 404
        miss.raise_for_status.side_effect = requests.HTTPError(response=miss)

        with patch.object(fetcher, "_session") as session:
            session.get.side_effect = [miss, _response(ACUERDO_HTML)]
            html = fetcher.fetch_html(doc)
        assert html == ACUERDO_HTML
        # Second call hit the DOF canonical URL.
        second = session.get.call_args_list[1][0][0]
        assert "dof.gob.mx/nota_detalle.php" in second

    def test_identity_guard_rejects_wrong_instrument(self, fetcher):
        """A merely-successful fetch proves nothing: an opaque mis-pinned
        codigo resolves to a valid page for the wrong document. The title
        marker turns that into a loud failure, not a corrupt corpus entry."""
        doc = SEP_CALENDAR_DOCUMENTS_BY_CICLO["2026-2027"]
        with patch.object(fetcher, "_session") as session:
            session.get.return_value = _response(WRONG_NOTE_HTML)
            html = fetcher.fetch_html(doc)
        assert html is None


class TestMaterialize:
    def test_writes_akn_for_the_acuerdo(self, fetcher, tmp_path):
        doc = SEP_CALENDAR_DOCUMENTS_BY_CICLO["2026-2027"]
        with patch.object(fetcher, "fetch_html", return_value=ACUERDO_HTML):
            path = fetcher.materialize(doc)
        assert path is not None
        assert path.exists()
        assert path.suffix == ".xml"
        content = path.read_text(encoding="utf-8")
        assert content.startswith("<?xml")
        assert "ARTÍCULO PRIMERO" in content

    def test_refuses_on_bad_article_sequence(self, fetcher):
        doc = SEP_CALENDAR_DOCUMENTS_BY_CICLO["2026-2027"]
        with patch.object(fetcher, "fetch_html", return_value=ACUERDO_HTML):
            with patch(
                "apps.scraper.federal.sep_calendario_scraper."
                "validate_article_sequence",
                return_value=["position 1: expected 'PRIMERO', got 'SEGUNDO'"],
            ):
                path = fetcher.materialize(doc)
        # A broken parse must not masquerade as an ingested document.
        assert path is None


class TestRun:
    def test_run_writes_catalog_and_dates_without_download(self, fetcher, tmp_path):
        result = fetcher.run(download_documents=False)
        assert result["total"] == len(SEP_CALENDAR_DOCUMENTS)
        assert (tmp_path / "catalog.json").exists()
        assert (tmp_path / "dates-2026-2027.json").exists()
        # No network was touched.
        assert result["downloaded"] == 0

    def test_catalog_round_trips_through_the_dataclass(self, fetcher, tmp_path):
        import json

        fetcher.write_catalog(list(SEP_CALENDAR_DOCUMENTS))
        raw = json.loads((tmp_path / "catalog.json").read_text(encoding="utf-8"))
        # Derived fields present for downstream consumers.
        assert raw[0]["dof_url"].startswith("https://dof.gob.mx/")
        assert raw[0]["sidof_url"].startswith("https://sidof.segob.gob.mx/")
        # And a catalog entry rebuilds a valid document.
        rebuilt = SepCalendarDocument(
            **{
                k: v
                for k, v in raw[0].items()
                if k not in ("dof_url", "sidof_url", "text_filename")
            }
        )
        assert rebuilt.official_id == "sep-calendario-escolar-2026-2027"
