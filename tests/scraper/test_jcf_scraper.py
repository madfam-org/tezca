"""
Tests for the JCF fetcher (apps/scraper/federal/jcf_scraper.py).

Network-free: every test mocks the requests session. The interesting logic
is in ``parse_reglas`` (DOF note HTML → one entry per ordinal Regla),
``validate_regla_sequence`` (catches mis-splits before they corrupt
citations), ``build_akn`` (per-Regla addressable articles for index_laws),
and the pinned ``JCF_DOCUMENTS`` registry itself.

The HTML fixtures below reproduce the real DOF/SIDOF quirks observed in
note 5777674 on 2026-08-22:
  - ordinals in caps with an inconsistent trailing period
  - a rubric on the same line as the ordinal ("DÉCIMA TERCERA. Medidas...")
  - a rubric split onto the next line starting with "." ("DÉCIMA QUINTA"
    then ". Recurso Federal asignado...")
  - mid-sentence column wraps
  - annexes after the transitorios that restart ordinal numbering
"""

from unittest.mock import MagicMock, patch

import pytest

from apps.scraper.federal.jcf_scraper import (
    JCF_CATEGORY,
    JCF_DOCUMENTS,
    JCF_DOCUMENTS_BY_ID,
    JCF_DOMAINS,
    JcfDocument,
    JcfFetcher,
    build_akn,
    html_to_lines,
    parse_reglas,
    validate_regla_sequence,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

ROP_HTML = """
<html><head><title>REGLAS de Operación del Programa Jóvenes Construyendo el Futuro</title></head>
<body>
<p>REGLAS de Operación del Programa Jóvenes Construyendo el Futuro.</p>
<p>MARATH BARUCH BOLAÑOS LÓPEZ, Secretario del Trabajo y Previsión Social,</p>
<p>PRIMERA.</p>
<p>Las presentes Reglas de Operación tienen por objeto regir la operación del</p>
<p>Programa Jóvenes Construyendo el Futuro.</p>
<p>SEGUNDA.</p>
<p>Para los efectos de las presentes Reglas se entenderá por:</p>
<p>III. Apoyo económico.</p>
<p>El que otorga la STPS por concepto de beca hasta por 12 (doce) emisiones,</p>
<p>cuyo monto equivale a $9,582.47 (nueve mil quinientos ochenta y dos pesos 47/100 M.N.).</p>
<p>TERCERA.</p>
<p>Descripción.</p>
<p>DÉCIMA TERCERA. Medidas por incumplimiento.</p>
<p>A) Causales de desvinculación de las y los Aprendices.</p>
<p>DÉCIMA QUINTA</p>
<p>. Recurso Federal asignado, no ejercido y gastos indirectos.</p>
<p>Los recursos aprobados ascienden a $25,173,000,000.00.</p>
<p>TRANSITORIOS</p>
<p>PRIMERA. Las presentes Reglas de Operación entrarán en vigor el día siguiente.</p>
<p>ANEXOS</p>
<p>PRIMERA. Cláusula del convenio modelo que reinicia la numeración.</p>
</body></html>
"""

ACUERDO_HTML = """
<html><head><title>ACUERDO por el que se establecen acciones de simplificación</title></head>
<body>
<p>Que la tercera regla de las Reglas de Operación del Programa Jóvenes</p>
<p>Construyendo el Futuro vigentes señalan que el Programa</p>
<p>Se fusionan los trámites STPS-03-026-A, STPS-03-026-B y STPS-03-026-C.</p>
</body></html>
"""


@pytest.fixture
def fetcher(tmp_path):
    return JcfFetcher(output_dir=str(tmp_path))


# ---------------------------------------------------------------------------
# The pinned corpus
# ---------------------------------------------------------------------------


class TestJcfDocumentsRegistry:
    """The enumerated JCF corpus must stay internally consistent."""

    def test_official_ids_are_unique(self):
        ids = [doc.official_id for doc in JCF_DOCUMENTS]
        assert len(ids) == len(set(ids))

    def test_by_id_index_matches_list(self):
        assert set(JCF_DOCUMENTS_BY_ID) == {d.official_id for d in JCF_DOCUMENTS}
        assert len(JCF_DOCUMENTS_BY_ID) == len(JCF_DOCUMENTS)

    def test_controlling_document_is_the_2026_rop(self):
        doc = JCF_DOCUMENTS_BY_ID["jcf-reglas-2026"]
        assert doc.status == "vigente"
        assert doc.document_type == "reglas_de_operacion"
        assert doc.dof_codigo == "5777674"
        assert doc.publication_date == "2025-12-31"
        # Transitorio Primero: in force the day after publication.
        assert doc.valid_from == "2026-01-01"

    def test_unverified_prior_rop_is_absent(self):
        """The abrogated 2025 ROP is deliberately not registered: its DOF
        codigo could not be verified (the assumed value resolves to an
        unrelated judicial edicto). An acknowledged gap beats a wrong
        citation in the ecosystem's source of law."""
        assert "jcf-reglas-2025" not in JCF_DOCUMENTS_BY_ID

    def test_2019_lineamientos_are_unknown_not_abrogated(self):
        """No instrument expressly abrogates them, so the corpus must not
        claim one does. "unknown" is the honest status."""
        doc = JCF_DOCUMENTS_BY_ID["jcf-lineamientos-2019"]
        assert doc.status == "unknown"
        assert doc.status != "abrogada"
        assert doc.vigencia_note  # must explain the residual status

    def test_every_document_carries_labor_domain_and_category(self):
        for doc in JCF_DOCUMENTS:
            assert doc.category == JCF_CATEGORY
            assert doc.domains == JCF_DOMAINS
            assert "labor" in doc.domains

    def test_no_document_is_typed_as_a_ley(self):
        """JCF has no ley. Mislabeling a Regla de Operación as one would
        propagate the lie to every consumer of the corpus."""
        for doc in JCF_DOCUMENTS:
            assert doc.document_type in ("reglas_de_operacion", "acuerdo")

    def test_every_document_has_a_vigencia_note(self):
        for doc in JCF_DOCUMENTS:
            assert doc.vigencia_note.strip(), doc.official_id

    def test_dof_and_sidof_urls_are_derived_from_the_codigo(self):
        doc = JCF_DOCUMENTS_BY_ID["jcf-reglas-2026"]
        assert doc.sidof_url == ("https://sidof.segob.gob.mx/notas/docFuente/5777674")
        # DOF wants DD/MM/YYYY, not the ISO date we store.
        assert doc.dof_url == (
            "https://dof.gob.mx/nota_detalle.php?codigo=5777674&fecha=31/12/2025"
        )

    def test_official_ids_fit_the_law_model_column(self):
        from apps.api.models import Law

        for doc in JCF_DOCUMENTS:
            assert len(doc.official_id) <= Law.OFFICIAL_ID_MAX_LENGTH


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------


class TestParseReglas:
    """parse_reglas: DOF note HTML → one entry per ordinal Regla."""

    def test_extracts_each_ordinal_regla(self):
        reglas = parse_reglas(ROP_HTML)
        nums = [r["num"] for r in reglas]
        assert nums == [
            "PRIMERA",
            "SEGUNDA",
            "TERCERA",
            "DÉCIMA TERCERA",
            "DÉCIMA QUINTA",
        ]

    def test_stops_at_the_transitorios(self):
        """Annexes after the transitorios restart ordinal numbering; parsing
        past them would produce a second "PRIMERA" that collides in the
        article namespace."""
        reglas = parse_reglas(ROP_HTML)
        assert [r["num"] for r in reglas].count("PRIMERA") == 1
        joined = " ".join(r["text"] for r in reglas)
        assert "entrarán en vigor" not in joined
        assert "convenio modelo" not in joined

    def test_captures_inline_rubric(self):
        regla = next(r for r in parse_reglas(ROP_HTML) if r["num"] == "DÉCIMA TERCERA")
        assert regla["heading"] == "Medidas por incumplimiento."
        assert "Causales de desvinculación" in regla["text"]

    def test_captures_rubric_split_onto_the_next_line(self):
        """The DOF sometimes breaks between the ordinal and its period, so
        the rubric arrives as its own line starting with "."."""
        regla = next(r for r in parse_reglas(ROP_HTML) if r["num"] == "DÉCIMA QUINTA")
        assert regla["heading"] == (
            "Recurso Federal asignado, no ejercido y gastos indirectos."
        )
        assert not regla["text"].startswith(".")
        assert "25,173,000,000.00" in regla["text"]

    def test_rejoins_mid_sentence_column_wraps(self):
        regla = next(r for r in parse_reglas(ROP_HTML) if r["num"] == "PRIMERA")
        assert "operación del Programa Jóvenes" in regla["text"]

    def test_beca_amount_lands_in_segunda_not_decima_quinta(self):
        """The beca figure is defined in SEGUNDA (definiciones), fr. III —
        DÉCIMA QUINTA is the budget rule. Citations must address the Regla
        that actually carries the text."""
        by_num = {r["num"]: r["text"] for r in parse_reglas(ROP_HTML)}
        assert "$9,582.47" in by_num["SEGUNDA"]
        assert "$9,582.47" not in by_num["DÉCIMA QUINTA"]

    def test_returns_empty_for_a_prose_document(self):
        """The simplification Acuerdo has no ordinal Reglas; callers fall
        back to raw text rather than inventing structure."""
        assert parse_reglas(ACUERDO_HTML) == []

    def test_html_to_lines_drops_blanks(self):
        lines = html_to_lines(ACUERDO_HTML)
        assert all(line.strip() for line in lines)
        assert any("STPS-03-026-A" in line for line in lines)


class TestValidateReglaSequence:
    """A gap or repeat means the parser mis-split the note."""

    def test_accepts_a_consecutive_run(self):
        reglas = [{"num": n} for n in ("PRIMERA", "SEGUNDA", "TERCERA")]
        assert validate_regla_sequence(reglas) == []

    def test_accepts_the_full_ordinal_run_through_the_tens(self):
        reglas = [
            {"num": n}
            for n in (
                "PRIMERA",
                "SEGUNDA",
                "TERCERA",
                "CUARTA",
                "QUINTA",
                "SEXTA",
                "SÉPTIMA",
                "OCTAVA",
                "NOVENA",
                "DÉCIMA",
                "DÉCIMA PRIMERA",
            )
        ]
        assert validate_regla_sequence(reglas) == []

    def test_flags_a_gap(self):
        reglas = [{"num": n} for n in ("PRIMERA", "TERCERA")]
        problems = validate_regla_sequence(reglas)
        assert problems
        assert "SEGUNDA" in problems[0]

    def test_flags_an_empty_parse(self):
        assert validate_regla_sequence([]) == ["no reglas parsed"]

    def test_real_fixture_parses_cleanly_in_sequence(self):
        """The fixture skips ordinals on purpose (it is an excerpt), so a
        contiguous slice is what must validate."""
        reglas = parse_reglas(ROP_HTML)[:3]
        assert validate_regla_sequence(reglas) == []


# ---------------------------------------------------------------------------
# AKN emission
# ---------------------------------------------------------------------------


class TestBuildAkn:
    """index_laws reads <akn:article>/<num> — that is what makes a single
    Regla individually addressable through the API."""

    def test_emits_one_article_per_regla(self):
        reglas = parse_reglas(ROP_HTML)
        xml = build_akn(JCF_DOCUMENTS_BY_ID["jcf-reglas-2026"], reglas)
        assert xml.count("<article ") == len(reglas)

    def test_article_num_is_the_ordinal(self):
        xml = build_akn(JCF_DOCUMENTS_BY_ID["jcf-reglas-2026"], parse_reglas(ROP_HTML))
        assert "<num>DÉCIMA QUINTA</num>" in xml
        assert "<num>SEGUNDA</num>" in xml

    def test_eid_is_slugified_and_accent_free(self):
        xml = build_akn(JCF_DOCUMENTS_BY_ID["jcf-reglas-2026"], parse_reglas(ROP_HTML))
        assert 'eId="regla-decima-quinta"' in xml
        assert 'eId="regla-primera"' in xml

    def test_is_parseable_akn_that_index_laws_recognizes(self):
        from lxml import etree

        xml = build_akn(JCF_DOCUMENTS_BY_ID["jcf-reglas-2026"], parse_reglas(ROP_HTML))
        # index_laws sniffs for this prefix before choosing the AKN path.
        assert xml.startswith("<?xml")
        root = etree.fromstring(xml.encode("utf-8"))
        ns = {"akn": "http://docs.oasis-open.org/legaldocml/ns/akn/3.0"}
        articles = root.xpath("//akn:article", namespaces=ns)
        assert len(articles) == 5
        nums = [a.find("akn:num", ns).text for a in articles]
        assert "DÉCIMA TERCERA" in nums

    def test_index_laws_extracts_one_article_per_regla(self):
        """The contract that actually matters: run the emitted AKN through
        the real indexer and confirm each Regla becomes an addressable
        article keyed by its ordinal. Without this, JCF would index as one
        opaque blob and no citation could point at a single Regla."""
        from apps.api.management.commands.index_laws import Command

        xml = build_akn(JCF_DOCUMENTS_BY_ID["jcf-reglas-2026"], parse_reglas(ROP_HTML))
        articles = Command().extract_articles_from_xml(xml, "jcf-reglas-2026")

        ids = [a["article_id"] for a in articles]
        assert ids == [
            "PRIMERA",
            "SEGUNDA",
            "TERCERA",
            "DÉCIMA TERCERA",
            "DÉCIMA QUINTA",
        ]

        by_id = {a["article_id"]: a["text"] for a in articles}
        assert "$9,582.47" in by_id["SEGUNDA"]
        assert not by_id["DÉCIMA QUINTA"].startswith(".")

    def test_escapes_markup_in_source_text(self):
        doc = JCF_DOCUMENTS_BY_ID["jcf-reglas-2026"]
        xml = build_akn(
            doc, [{"num": "PRIMERA", "heading": "", "text": "a < b & c > d"}]
        )
        from lxml import etree

        etree.fromstring(xml.encode("utf-8"))  # must not raise
        assert "a &lt; b &amp; c &gt; d" in xml


# ---------------------------------------------------------------------------
# Fetching
# ---------------------------------------------------------------------------


def _response(text, status=200):
    resp = MagicMock()
    resp.text = text
    resp.status_code = status
    resp.raise_for_status = MagicMock()
    return resp


class TestFetchHtml:
    def test_prefers_sidof(self, fetcher):
        doc = JCF_DOCUMENTS_BY_ID["jcf-reglas-2026"]
        with patch.object(fetcher, "_session") as session:
            session.get.return_value = _response(ROP_HTML)
            html = fetcher.fetch_html(doc)
        assert html == ROP_HTML
        called = session.get.call_args[0][0]
        assert "sidof.segob.gob.mx" in called

    def test_falls_back_to_dof_when_sidof_misses(self, fetcher):
        import requests

        doc = JCF_DOCUMENTS_BY_ID["jcf-reglas-2026"]
        miss = MagicMock()
        miss.status_code = 404
        error = requests.HTTPError(response=miss)
        miss.raise_for_status.side_effect = error

        with patch.object(fetcher, "_session") as session:
            session.get.side_effect = [miss, _response(ROP_HTML)]
            html = fetcher.fetch_html(doc)

        assert html == ROP_HTML
        urls = [call[0][0] for call in session.get.call_args_list]
        assert "sidof.segob.gob.mx" in urls[0]
        assert "dof.gob.mx" in urls[1]


# DOF codigos are opaque and adjacent codes are unrelated notes, so a
# mis-pinned digit returns a perfectly valid page for the wrong document.
# This is not hypothetical: an early draft of JCF_DOCUMENTS pinned 5746288
# for the 2025 ROP, which actually serves a judicial edicto.
EDICTO_HTML = """
<html><head><title>Estados Unidos Mexicanos</title></head>
<body>
<p>Poder Judicial de la Federación</p>
<p>Tercer Tribunal Colegiado en Materias Administrativa y Civil</p>
<p>EDICTO:</p>
<p>Tercero interesado: persona de domicilio ignorado.</p>
</body></html>
"""


class TestIdentityGuard:
    def test_accepts_a_note_carrying_the_title_marker(self, fetcher):
        doc = JCF_DOCUMENTS_BY_ID["jcf-reglas-2026"]
        assert fetcher._identity_matches(doc, ROP_HTML) is True

    def test_rejects_an_unrelated_note(self, fetcher):
        doc = JCF_DOCUMENTS_BY_ID["jcf-reglas-2026"]
        assert fetcher._identity_matches(doc, EDICTO_HTML) is False

    def test_matches_on_body_text_when_the_title_is_generic(self, fetcher):
        """SIDOF sometimes serves a generic <title>; the opening body text
        still identifies the instrument."""
        doc = JCF_DOCUMENTS_BY_ID["jcf-acuerdo-simplificacion-2026"]
        generic = ACUERDO_HTML.replace(
            "<title>ACUERDO por el que se establecen acciones de simplificación</title>",
            "<title>Estados Unidos Mexicanos</title>",
        ).replace(
            "<p>Que la tercera regla",
            "<p>ACUERDO por el que se establecen acciones de simplificación</p><p>Que la tercera regla",
        )
        assert fetcher._identity_matches(doc, generic) is True

    def test_fetch_refuses_a_wrong_document_instead_of_returning_it(self, fetcher):
        """A wrong codigo must fail loudly, not silently corrupt the corpus."""
        doc = JCF_DOCUMENTS_BY_ID["jcf-reglas-2026"]
        with patch.object(fetcher, "_session") as session:
            session.get.return_value = _response(EDICTO_HTML)
            assert fetcher.fetch_html(doc) is None

    def test_materialize_writes_nothing_on_identity_mismatch(self, fetcher, tmp_path):
        doc = JCF_DOCUMENTS_BY_ID["jcf-reglas-2026"]
        with patch.object(fetcher, "_session") as session:
            session.get.return_value = _response(EDICTO_HTML)
            assert fetcher.materialize(doc) is None
        assert not (tmp_path / doc.text_filename).exists()
        assert not (tmp_path / f"{doc.official_id}.txt").exists()

    def test_every_pinned_document_declares_a_title_marker(self):
        for doc in JCF_DOCUMENTS:
            assert doc.title_marker.strip(), doc.official_id


class TestMaterialize:
    def test_writes_akn_for_a_rop(self, fetcher, tmp_path):
        doc = JCF_DOCUMENTS_BY_ID["jcf-reglas-2026"]
        with patch.object(fetcher, "fetch_html", return_value=ROP_HTML):
            with patch(
                "apps.scraper.federal.jcf_scraper.validate_regla_sequence",
                return_value=[],
            ):
                path = fetcher.materialize(doc)

        assert path == tmp_path / "jcf-reglas-2026.xml"
        assert "<akomaNtoso" in path.read_text(encoding="utf-8")

    def test_writes_raw_text_for_a_prose_document(self, fetcher, tmp_path):
        doc = JCF_DOCUMENTS_BY_ID["jcf-acuerdo-simplificacion-2026"]
        with patch.object(fetcher, "fetch_html", return_value=ACUERDO_HTML):
            path = fetcher.materialize(doc)

        assert path == tmp_path / "jcf-acuerdo-simplificacion-2026.txt"
        assert "STPS-03-026-A" in path.read_text(encoding="utf-8")

    def test_returns_none_and_writes_nothing_when_retrieval_fails(
        self, fetcher, tmp_path
    ):
        """A broken fetch must not leave a file that later looks ingested."""
        doc = JCF_DOCUMENTS_BY_ID["jcf-reglas-2026"]
        with patch.object(fetcher, "fetch_html", return_value=None):
            assert fetcher.materialize(doc) is None
        assert not (tmp_path / doc.text_filename).exists()

    def test_refuses_to_write_when_sequence_validation_fails(self, fetcher, tmp_path):
        """A mis-split note would silently corrupt every citation into it."""
        doc = JCF_DOCUMENTS_BY_ID["jcf-reglas-2026"]
        with patch.object(fetcher, "fetch_html", return_value=ROP_HTML):
            with patch(
                "apps.scraper.federal.jcf_scraper.validate_regla_sequence",
                return_value=["position 2: expected 'SEGUNDA', got 'TERCERA'"],
            ):
                assert fetcher.materialize(doc) is None
        assert not (tmp_path / doc.text_filename).exists()


class TestRun:
    def test_catalog_only_run_makes_no_requests(self, fetcher, tmp_path):
        with patch.object(fetcher, "_session") as session:
            result = fetcher.run(download_documents=False)
        session.get.assert_not_called()
        assert result["total"] == len(JCF_DOCUMENTS)
        assert result["downloaded"] == 0
        assert (tmp_path / "catalog.json").exists()

    def test_catalog_round_trips_into_documents(self, fetcher, tmp_path):
        import json

        from apps.api.management.commands.ingest_jcf import (
            _document_from_catalog_entry,
        )

        fetcher.run(download_documents=False)
        entries = json.loads((tmp_path / "catalog.json").read_text(encoding="utf-8"))
        rebuilt = [_document_from_catalog_entry(e) for e in entries]
        assert rebuilt == JCF_DOCUMENTS

    def test_by_type_tally(self, fetcher):
        result = fetcher.run(download_documents=False)
        assert result["by_type"]["reglas_de_operacion"] == 1
        assert result["by_type"]["acuerdo"] == 2


class TestJcfDocument:
    def test_text_filename_is_derived_from_official_id(self):
        doc = JcfDocument(
            official_id="jcf-test",
            name="Test",
            short_name="Test",
            dof_codigo="1234567",
            publication_date="2026-01-02",
            valid_from="2026-01-03",
            document_type="acuerdo",
            status="vigente",
        )
        assert doc.text_filename == "jcf-test.xml"
        assert doc.dof_url.endswith("fecha=02/01/2026")
