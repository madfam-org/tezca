"""Tests for ``apps.scraper.federal.dof_api_client``.

The DOFAPIClient is a thin requests wrapper for the DOF and Chamber of
Deputies download endpoints. Tests stub the session at the boundary.
"""

from __future__ import annotations

import datetime
from unittest.mock import MagicMock, patch

import pytest
import requests

from apps.scraper.federal.dof_api_client import DOFAPIClient

# ---------------------------------------------------------------------------
# __init__
# ---------------------------------------------------------------------------


def test_init_creates_session_with_user_agent():
    client = DOFAPIClient()
    assert client.session is not None
    assert "Tezca" in client.session.headers["User-Agent"]


# ---------------------------------------------------------------------------
# get_daily_pdf
# ---------------------------------------------------------------------------


@pytest.fixture
def client():
    c = DOFAPIClient()
    c.session = MagicMock()
    return c


def test_get_daily_pdf_writes_default_path(client, tmp_path, monkeypatch):
    fake_resp = MagicMock(content=b"PDFCONTENT")
    fake_resp.raise_for_status = MagicMock()
    client.session.get.return_value = fake_resp

    monkeypatch.chdir(tmp_path)  # default save path is relative
    out = client.get_daily_pdf(date=datetime.date(2024, 3, 15))
    assert out is not None
    assert out.exists()
    assert out.read_bytes() == b"PDFCONTENT"
    # Default filename includes the date and edition
    assert "2024-03-15" in out.name
    assert "MAT" in out.name


def test_get_daily_pdf_uses_explicit_save_path(client, tmp_path):
    fake_resp = MagicMock(content=b"PDF")
    fake_resp.raise_for_status = MagicMock()
    client.session.get.return_value = fake_resp

    target = tmp_path / "out" / "edition.pdf"
    out = client.get_daily_pdf(date=datetime.date(2024, 1, 1), save_path=target)
    assert out == target
    assert target.read_bytes() == b"PDF"


def test_get_daily_pdf_url_includes_date_components(client, tmp_path):
    fake_resp = MagicMock(content=b"")
    fake_resp.raise_for_status = MagicMock()
    client.session.get.return_value = fake_resp

    client.get_daily_pdf(
        date=datetime.date(2024, 3, 15),
        edition="VES",
        save_path=tmp_path / "x.pdf",
    )
    called_url = client.session.get.call_args.args[0]
    assert "day=15" in called_url
    assert "month=03" in called_url
    assert "year=2024" in called_url
    assert "edicion=VES" in called_url


def test_get_daily_pdf_returns_none_on_request_exception(client, tmp_path):
    client.session.get.side_effect = requests.RequestException("boom")
    out = client.get_daily_pdf(
        date=datetime.date(2024, 1, 1), save_path=tmp_path / "x.pdf"
    )
    assert out is None


def test_get_daily_pdf_returns_none_on_http_error(client, tmp_path):
    fake_resp = MagicMock()
    fake_resp.raise_for_status.side_effect = requests.HTTPError
    client.session.get.return_value = fake_resp
    out = client.get_daily_pdf(
        date=datetime.date(2024, 1, 1), save_path=tmp_path / "x.pdf"
    )
    assert out is None


# ---------------------------------------------------------------------------
# download_law_from_diputados
# ---------------------------------------------------------------------------


def test_download_law_from_diputados_writes_file(client, tmp_path):
    fake_resp = MagicMock(content=b"LAWPDF")
    fake_resp.raise_for_status = MagicMock()
    client.session.get.return_value = fake_resp

    out = client.download_law_from_diputados(
        law_slug="Ley_de_Amparo", save_path=tmp_path / "amparo.pdf"
    )
    assert out is not None
    assert out.read_bytes() == b"LAWPDF"


def test_download_law_from_diputados_default_path(client, tmp_path, monkeypatch):
    fake_resp = MagicMock(content=b"X")
    fake_resp.raise_for_status = MagicMock()
    client.session.get.return_value = fake_resp

    monkeypatch.chdir(tmp_path)
    out = client.download_law_from_diputados(law_slug="Foo_Bar")
    assert out.name == "Foo_Bar.pdf"


def test_download_law_from_diputados_url_uses_chamber(client, tmp_path):
    fake_resp = MagicMock(content=b"")
    fake_resp.raise_for_status = MagicMock()
    client.session.get.return_value = fake_resp

    client.download_law_from_diputados(
        law_slug="Some_Law", save_path=tmp_path / "x.pdf"
    )
    called_url = client.session.get.call_args.args[0]
    assert "diputados.gob.mx" in called_url
    assert "Some_Law" in called_url


def test_download_law_from_diputados_returns_none_on_failure(client, tmp_path):
    client.session.get.side_effect = requests.RequestException
    out = client.download_law_from_diputados(law_slug="X", save_path=tmp_path / "x.pdf")
    assert out is None
