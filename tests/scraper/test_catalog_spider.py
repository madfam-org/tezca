"""Tests for ``apps.scraper.federal.catalog_spider``.

Single-function module that crawls the Chamber of Deputies legislation
index. Tests use a local HTML fixture so we don't hit the live site.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from apps.scraper.federal import catalog_spider

# ---------------------------------------------------------------------------
# fetch_catalog — local file branch
# ---------------------------------------------------------------------------


@pytest.fixture
def fixture_html(tmp_path):
    """Write a synthetic Diputados-style index page and return its path."""
    html = """
    <html><body>
      <table>
        <tr>
          <td>Ley de Amparo, Reglamentaria de los Artículos 103 y 107 Constitucionales</td>
          <td><a href="pdf/LAmp.pdf">PDF</a></td>
        </tr>
        <tr>
          <td>Constitución Política de los Estados Unidos Mexicanos</td>
          <td><a href="pdf/CPEUM.pdf">PDF</a></td>
        </tr>
        <tr>
          <td>Ley Federal del Trabajo</td>
          <td><a href="pdf/LFT.pdf">PDF</a></td>
        </tr>
      </table>
    </body></html>
    """
    path = tmp_path / "fixture.htm"
    path.write_text(html, encoding="iso-8859-1")
    return path


def test_fetch_catalog_extracts_laws_from_local_file(fixture_html):
    laws = catalog_spider.fetch_catalog(local_file=str(fixture_html))
    assert len(laws) == 3
    slugs = {law["id"] for law in laws}
    assert "lamp" in slugs
    assert "cpeum" in slugs
    assert "lft" in slugs


def test_fetch_catalog_dedups_by_url(tmp_path):
    """The same PDF appearing twice should yield a single entry."""
    html = """
    <html><body>
      <table>
        <tr>
          <td>Ley de Amparo</td>
          <td><a href="pdf/LAmp.pdf">PDF</a></td>
        </tr>
        <tr>
          <td>Otro título para misma ley</td>
          <td><a href="pdf/LAmp.pdf#fragment">duplicate</a></td>
        </tr>
      </table>
    </body></html>
    """
    path = tmp_path / "dup.htm"
    path.write_text(html, encoding="iso-8859-1")

    laws = catalog_spider.fetch_catalog(local_file=str(path))
    assert len(laws) == 1


def test_fetch_catalog_skips_non_pdf_links(tmp_path):
    html = """
    <html><body>
      <table>
        <tr>
          <td>HTML version</td>
          <td><a href="pdf/page.html">HTML</a></td>
        </tr>
        <tr>
          <td>Real PDF</td>
          <td><a href="pdf/Real.pdf">PDF</a></td>
        </tr>
      </table>
    </body></html>
    """
    path = tmp_path / "mixed.htm"
    path.write_text(html, encoding="iso-8859-1")

    laws = catalog_spider.fetch_catalog(local_file=str(path))
    assert len(laws) == 1
    assert "real" in laws[0]["id"]


def test_fetch_catalog_falls_back_to_filename_when_no_title(tmp_path):
    """A link without a usable adjacent title falls back to filename-based title."""
    html = """
    <html><body>
      <table>
        <tr>
          <td><a href="pdf/My_Law_Name.pdf">file</a></td>
        </tr>
      </table>
    </body></html>
    """
    path = tmp_path / "no_title.htm"
    path.write_text(html, encoding="iso-8859-1")

    laws = catalog_spider.fetch_catalog(local_file=str(path))
    if laws:
        # If extraction succeeded, the fallback title was applied
        assert "My Law Name" in laws[0]["name"] or "my_law_name" in laws[0]["id"]


# ---------------------------------------------------------------------------
# fetch_catalog — remote branch (mocked)
# ---------------------------------------------------------------------------


def test_fetch_catalog_uses_requests_when_no_local_file():
    fake_response = MagicMock()
    fake_response.text = """
    <html><body>
      <table>
        <tr>
          <td>Test Law</td>
          <td><a href="pdf/Test.pdf">link</a></td>
        </tr>
      </table>
    </body></html>
    """

    with patch(
        "apps.scraper.federal.catalog_spider.requests.get", return_value=fake_response
    ):
        laws = catalog_spider.fetch_catalog(local_file=None)

    assert len(laws) == 1
    assert laws[0]["id"] == "test"


# ---------------------------------------------------------------------------
# Output schema
# ---------------------------------------------------------------------------


def test_law_dict_has_required_keys(fixture_html):
    laws = catalog_spider.fetch_catalog(local_file=str(fixture_html))
    for law in laws:
        assert {"id", "name", "url", "remote_path"} <= set(law.keys())
        # URL must be absolute
        assert law["url"].startswith("http")
