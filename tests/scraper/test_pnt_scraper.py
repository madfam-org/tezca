"""Tests for ``apps.scraper.municipal.pnt_scraper``.

PNT is the Plataforma Nacional de Transparencia. The scraper hits a
JSON API, so tests stub `_api_post` / `_api_get` at the boundary and
exercise the orchestration + extraction logic.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from apps.scraper.municipal.pnt_scraper import (
    INEGI_STATE_CODES,
    REGULATORY_KEYWORDS,
    PNTMunicipalScraper,
    _sanitize_filename,
)

# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------


def test_sanitize_filename_replaces_unsafe_chars():
    out = _sanitize_filename("Reglamento de Aguas/Drenaje (2024)")
    # Spaces, slashes, parentheses replaced with underscores
    assert "/" not in out
    assert "(" not in out
    assert " " not in out


def test_sanitize_filename_truncates():
    long_name = "x" * 200
    assert len(_sanitize_filename(long_name, max_length=50)) <= 50


def test_sanitize_filename_preserves_periods_and_hyphens():
    out = _sanitize_filename("file-name.v2.pdf")
    assert "." in out
    assert "-" in out


def test_regulatory_keywords_match():
    assert REGULATORY_KEYWORDS.search("Reglamento de obras")
    assert REGULATORY_KEYWORDS.search("Bando municipal")
    assert REGULATORY_KEYWORDS.search("Código fiscal")
    assert REGULATORY_KEYWORDS.search("Manual de procedimientos")
    assert not REGULATORY_KEYWORDS.search("Otro documento")


# ---------------------------------------------------------------------------
# __init__
# ---------------------------------------------------------------------------


def test_init_succeeds_for_known_state(tmp_path):
    s = PNTMunicipalScraper(state_key="jalisco")
    assert s.state_key == "jalisco"
    assert s.state_code == INEGI_STATE_CODES["jalisco"]
    assert s.municipality_filter is None


def test_init_with_municipality_filter():
    s = PNTMunicipalScraper(state_key="jalisco", municipality="Guadalajara")
    assert s.municipality_filter == "Guadalajara"


def test_init_raises_for_unknown_state():
    with pytest.raises(ValueError, match="Unknown state key"):
        PNTMunicipalScraper(state_key="not_a_state")


def test_init_uses_custom_obligation_id():
    s = PNTMunicipalScraper(state_key="jalisco", obligation_id="II")
    assert s.obligation_id == "II"


# ---------------------------------------------------------------------------
# Fixture: scraper without network setup
# ---------------------------------------------------------------------------


@pytest.fixture
def scraper():
    """Build a scraper without invoking the real session setup."""
    s = PNTMunicipalScraper.__new__(PNTMunicipalScraper)
    s.state_key = "jalisco"
    s.state_code = INEGI_STATE_CODES["jalisco"]
    s.municipality_filter = None
    s.obligation_id = "I"
    s.session = MagicMock()
    s.last_request_time = 0.0
    s.config = {"name": "PNT-jalisco", "state": "Jalisco"}
    s.min_request_interval = 2.0
    return s


# ---------------------------------------------------------------------------
# _api_post / _api_get
# ---------------------------------------------------------------------------


def test_api_post_returns_parsed_json(scraper):
    fake_resp = MagicMock()
    fake_resp.json.return_value = {"results": [{"id": 1}]}
    fake_resp.raise_for_status = MagicMock()
    scraper.session.post.return_value = fake_resp
    with patch.object(scraper, "_rate_limit"):
        out = scraper._api_post("subjects", {"q": "x"})
    assert out == {"results": [{"id": 1}]}


def test_api_post_returns_none_on_exception(scraper):
    scraper.session.post.side_effect = RuntimeError("boom")
    with patch.object(scraper, "_rate_limit"):
        assert scraper._api_post("subjects", {}) is None


def test_api_get_returns_parsed_json(scraper):
    fake_resp = MagicMock()
    fake_resp.json.return_value = [{"a": 1}]
    fake_resp.raise_for_status = MagicMock()
    scraper.session.get.return_value = fake_resp
    with patch.object(scraper, "_rate_limit"):
        out = scraper._api_get("https://x.com")
    assert out == [{"a": 1}]


def test_api_get_returns_none_on_exception(scraper):
    scraper.session.get.side_effect = RuntimeError("boom")
    with patch.object(scraper, "_rate_limit"):
        assert scraper._api_get("https://x.com") is None


# ---------------------------------------------------------------------------
# fetch_subjects
# ---------------------------------------------------------------------------


def test_fetch_subjects_returns_list(scraper):
    with patch.object(
        scraper,
        "_api_post",
        return_value={"results": [{"id": "s1", "name": "Guadalajara"}]},
    ):
        out = scraper.fetch_subjects()
    assert len(out) == 1
    assert out[0]["name"] == "Guadalajara"


def test_fetch_subjects_handles_list_response(scraper):
    """Some PNT endpoints return a bare list instead of a wrapper."""
    with patch.object(scraper, "_api_post", return_value=[{"id": "s1", "name": "x"}]):
        out = scraper.fetch_subjects()
    assert len(out) == 1


def test_fetch_subjects_returns_empty_on_failure(scraper):
    with patch.object(scraper, "_api_post", return_value=None):
        assert scraper.fetch_subjects() == []


# ---------------------------------------------------------------------------
# fetch_records / fetch_all_records
# ---------------------------------------------------------------------------


def test_fetch_records_passes_pagination_params(scraper):
    with patch.object(scraper, "_api_post", return_value={"results": []}) as m:
        scraper.fetch_records("s1", page=3, page_size=50)
    payload = m.call_args.args[1]
    assert payload["subjectId"] == "s1"
    assert payload["page"] == 3
    assert payload["pageSize"] == 50


def test_fetch_all_records_paginates_until_empty(scraper):
    """Stops when API returns fewer records than page_size."""
    page1 = {"results": [{"id": i} for i in range(100)], "totalCount": 150}
    page2 = {"results": [{"id": i} for i in range(50)], "totalCount": 150}
    with patch.object(scraper, "fetch_records", side_effect=[page1, page2]):
        out = scraper.fetch_all_records("s1")
    assert len(out) == 150


def test_fetch_all_records_stops_when_total_reached(scraper):
    page1 = {"results": [{"id": i} for i in range(100)], "totalCount": 100}
    with patch.object(scraper, "fetch_records", side_effect=[page1, {"results": []}]):
        out = scraper.fetch_all_records("s1")
    assert len(out) == 100


def test_fetch_all_records_handles_none_response(scraper):
    with patch.object(scraper, "fetch_records", return_value=None):
        out = scraper.fetch_all_records("s1")
    assert out == []


def test_fetch_all_records_handles_list_response(scraper):
    """List response (not dict) — extends and stops."""
    with patch.object(scraper, "fetch_records", return_value=[{"id": 1}]):
        out = scraper.fetch_all_records("s1")
    assert out == [{"id": 1}]


# ---------------------------------------------------------------------------
# _extract_document_url
# ---------------------------------------------------------------------------


def test_extract_document_url_finds_known_field(scraper):
    record = {"documentUrl": "https://example.com/doc.pdf"}
    assert scraper._extract_document_url(record) == "https://example.com/doc.pdf"


def test_extract_document_url_finds_alternate_field(scraper):
    record = {"hipervinculo": "https://x.com/doc.pdf"}
    assert scraper._extract_document_url(record) == "https://x.com/doc.pdf"


def test_extract_document_url_finds_nested_field(scraper):
    record = {
        "fields": [
            {"label": "URL", "value": "https://example.com/nested.pdf"},
            {"label": "title", "value": "Some Title"},
        ]
    }
    assert scraper._extract_document_url(record) == "https://example.com/nested.pdf"


def test_extract_document_url_returns_none_when_no_url(scraper):
    record = {"name": "no url here"}
    assert scraper._extract_document_url(record) is None


def test_extract_document_url_skips_non_http_values(scraper):
    record = {"url": "ftp://example.com/x"}
    assert scraper._extract_document_url(record) is None


# ---------------------------------------------------------------------------
# _extract_document_title
# ---------------------------------------------------------------------------


def test_extract_document_title_uses_known_field(scraper):
    record = {"denominacion": "Reglamento de Aguas"}
    assert scraper._extract_document_title(record) == "Reglamento de Aguas"


def test_extract_document_title_handles_alternate_field(scraper):
    record = {"name": "Some Document"}
    assert scraper._extract_document_title(record) == "Some Document"


def test_extract_document_title_uses_nested_field(scraper):
    record = {
        "fields": [
            {"label": "Denominación", "value": "Bando Municipal"},
            {"label": "Other", "value": "ignored"},
        ]
    }
    assert scraper._extract_document_title(record) == "Bando Municipal"


def test_extract_document_title_falls_back_to_id(scraper):
    record = {"id": "rec-123"}
    out = scraper._extract_document_title(record)
    assert "rec-123" in out


def test_extract_document_title_skips_short_values(scraper):
    """Values <= 3 chars long are skipped."""
    record = {"denominacion": "X", "name": "Real Title"}
    assert scraper._extract_document_title(record) == "Real Title"


# ---------------------------------------------------------------------------
# _extract_publication_date
# ---------------------------------------------------------------------------


def test_extract_publication_date_finds_known_field(scraper):
    record = {"fechaPublicacion": "2024-01-15"}
    assert scraper._extract_publication_date(record) == "2024-01-15"


def test_extract_publication_date_alternate_field(scraper):
    record = {"date": "2023-06-30"}
    assert scraper._extract_publication_date(record) == "2023-06-30"


def test_extract_publication_date_returns_none_when_missing(scraper):
    assert scraper._extract_publication_date({}) is None


def test_extract_publication_date_skips_short_strings(scraper):
    """Strings shorter than 8 chars are skipped (likely not a real date)."""
    record = {"date": "short"}
    assert scraper._extract_publication_date(record) is None


# ---------------------------------------------------------------------------
# _is_regulatory_document
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "title,expected",
    [
        ("Reglamento de obras", True),
        ("Bando municipal", True),
        ("Código fiscal", True),
        ("Decreto número 42", True),
        ("Lineamientos de transparencia", True),
        ("Convocatoria", False),
        ("Acta de sesión", False),
    ],
)
def test_is_regulatory_document(scraper, title, expected):
    assert scraper._is_regulatory_document(title) is expected


# ---------------------------------------------------------------------------
# _clean_municipality_name
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "raw,cleaned",
    [
        ("H. Ayuntamiento de Guadalajara", "Guadalajara"),
        ("Ayuntamiento de Monterrey", "Monterrey"),
        ("Municipio de Puebla", "Puebla"),
        ("Ayuntamiento Municipal de León", "León"),
        ("Gobierno Municipal de Mérida", "Mérida"),
        ("Just Plain Name", "Just Plain Name"),
    ],
)
def test_clean_municipality_name(raw, cleaned):
    assert PNTMunicipalScraper._clean_municipality_name(raw) == cleaned


# ---------------------------------------------------------------------------
# list_available_states
# ---------------------------------------------------------------------------


def test_list_available_states_returns_sorted_list():
    states = PNTMunicipalScraper.list_available_states()
    assert "jalisco" in states
    assert states == sorted(states)


# ---------------------------------------------------------------------------
# scrape_catalog — orchestration
# ---------------------------------------------------------------------------


def test_scrape_catalog_returns_empty_when_no_subjects(scraper):
    with patch.object(scraper, "fetch_subjects", return_value=[]):
        assert scraper.scrape_catalog() == []


def test_scrape_catalog_filters_to_municipality(scraper):
    """When municipality_filter is set, only matching subjects proceed."""
    scraper.municipality_filter = "Guadalajara"
    with patch.object(
        scraper,
        "fetch_subjects",
        return_value=[
            {"id": "s1", "name": "H. Ayuntamiento de Guadalajara"},
            {"id": "s2", "name": "H. Ayuntamiento de Zapopan"},
        ],
    ), patch.object(scraper, "fetch_all_records", return_value=[]) as mock_records:
        scraper.scrape_catalog()
    # Only the matching subject's records were fetched
    assert mock_records.call_count == 1


def test_scrape_catalog_returns_empty_when_filter_misses(scraper):
    scraper.municipality_filter = "DoesNotExist"
    with patch.object(
        scraper,
        "fetch_subjects",
        return_value=[{"id": "s1", "name": "Guadalajara"}],
    ):
        assert scraper.scrape_catalog() == []


def test_scrape_catalog_extracts_law_dicts(scraper):
    subjects = [{"id": "s1", "name": "Ayuntamiento de Guadalajara"}]
    records = [
        {
            "id": "rec1",
            "denominacion": "Reglamento de Aguas",
            "documentUrl": "https://example.com/aguas.pdf",
            "fechaPublicacion": "2024-01-15",
        }
    ]
    with patch.object(scraper, "fetch_subjects", return_value=subjects), patch.object(
        scraper, "fetch_all_records", return_value=records
    ), patch.object(scraper, "validate_law_data", return_value=True), patch.object(
        scraper, "extract_category", return_value="reglamento"
    ):
        laws = scraper.scrape_catalog()

    assert len(laws) == 1
    assert laws[0]["name"] == "Reglamento de Aguas"
    assert laws[0]["municipality"] == "Guadalajara"
    assert laws[0]["url"] == "https://example.com/aguas.pdf"
    assert laws[0]["is_regulatory"] is True


def test_scrape_catalog_dedupes_by_url(scraper):
    """Two records with the same doc URL produce one law entry."""
    subjects = [
        {"id": "s1", "name": "M1"},
        {"id": "s2", "name": "M2"},
    ]
    common_record = {
        "id": "rec1",
        "denominacion": "Reglamento X",
        "documentUrl": "https://example.com/same.pdf",
    }
    with patch.object(scraper, "fetch_subjects", return_value=subjects), patch.object(
        scraper, "fetch_all_records", return_value=[common_record]
    ), patch.object(scraper, "validate_law_data", return_value=True), patch.object(
        scraper, "extract_category", return_value="reglamento"
    ):
        laws = scraper.scrape_catalog()
    assert len(laws) == 1


def test_scrape_catalog_skips_records_without_url(scraper):
    subjects = [{"id": "s1", "name": "M1"}]
    records = [
        {"id": "rec1", "denominacion": "No URL"},
        {
            "id": "rec2",
            "denominacion": "Has URL",
            "documentUrl": "https://example.com/x.pdf",
        },
    ]
    with patch.object(scraper, "fetch_subjects", return_value=subjects), patch.object(
        scraper, "fetch_all_records", return_value=records
    ), patch.object(scraper, "validate_law_data", return_value=True), patch.object(
        scraper, "extract_category", return_value="reglamento"
    ):
        laws = scraper.scrape_catalog()
    assert len(laws) == 1


def test_scrape_catalog_regulatory_only_filters(scraper):
    laws_in = [
        {"name": "Reglamento X", "is_regulatory": True},
        {"name": "Acta", "is_regulatory": False},
    ]
    with patch.object(scraper, "scrape_catalog", return_value=laws_in):
        out = scraper.scrape_catalog_regulatory_only()
    assert len(out) == 1
    assert out[0]["name"] == "Reglamento X"


# ---------------------------------------------------------------------------
# save_catalog
# ---------------------------------------------------------------------------


def test_save_catalog_writes_json(scraper, tmp_path):
    out = tmp_path / "out" / "catalog.json"
    laws = [{"name": "X", "url": "y"}]
    scraper.save_catalog(laws, str(out))
    assert out.exists()
    assert json.loads(out.read_text(encoding="utf-8")) == laws
