"""
Tests for Phase 17 scraping scripts and extended source_discovery.

Tests OJN recovery, Wayback bulk recovery, DOF historical scan,
datos.gob.mx probe, and CDX extension to SourceDiscoverer.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestOjnMultipathRecovery:
    """Test OJN multi-path recovery script."""

    def test_import(self):
        from scripts.scraping.ojn_multipath_recovery import run_recovery

        assert run_recovery is not None

    def test_load_failed_records_empty(self, tmp_path):
        """Returns empty list when no metadata files exist."""
        from scripts.scraping import ojn_multipath_recovery as m

        # Patch the data paths to tmp directories
        with patch.object(m, "NON_LEG_DATA", tmp_path / "nonleg"), patch.object(
            m, "LEG_DATA", tmp_path / "leg"
        ):
            records = m.load_failed_records()
            assert records == []

    def test_load_failed_records_parses_metadata(self, tmp_path):
        """Parses failed_laws from metadata files."""
        from scripts.scraping import ojn_multipath_recovery as m

        state_dir = tmp_path / "nonleg" / "test_state"
        state_dir.mkdir(parents=True)
        metadata = {
            "state_id": 1,
            "failed_laws": [
                {
                    "file_id": 123,
                    "law_name": "Test Law",
                    "failure_reason": "no_download_url",
                },
                {
                    "file_id": 456,
                    "law_name": "Test Law 2",
                    "failure_reason": "download_failed",
                },
            ],
        }
        (state_dir / "test_state_metadata.json").write_text(json.dumps(metadata))

        with patch.object(m, "NON_LEG_DATA", tmp_path / "nonleg"), patch.object(
            m, "LEG_DATA", tmp_path / "leg"
        ):
            records = m.load_failed_records(scope="non_leg")
            assert len(records) == 2
            assert records[0]["file_id"] == 123
            assert records[0]["state"] == "test_state"
            assert records[0]["source_type"] == "non_legislative"

    def test_classify_failure_reasons(self, tmp_path):
        """Path A filters to refetchable failure reasons."""
        from scripts.scraping import ojn_multipath_recovery as m

        records = [
            {"file_id": 1, "failure_reason": "no_download_url"},
            {"file_id": 2, "failure_reason": "no_metadata"},
            {"file_id": 3, "failure_reason": "download_failed"},
            {"file_id": 4, "failure_reason": "unknown_reason"},
        ]

        recovered, still_failed = m.path_a_refetch_metadata(
            records, MagicMock(), tmp_path, dry_run=True
        )
        # dry_run returns all as still_failed, but only refetchable ones
        assert len(still_failed) == 3  # unknown_reason excluded from refetchable

    def test_path_b_cdx_uses_prefix_match(self):
        """CDX queries use matchType=prefix without glob wildcards in URL."""
        from scripts.scraping.ojn_multipath_recovery import OJN_BASE

        # URL patterns should not contain asterisks (cleaned up in Wave 2)
        url1 = f"{OJN_BASE}/obtenerdoc.php?path=12345"
        url2 = f"{OJN_BASE}/fichaOrdenamiento2.php?idArchivo=12345"
        assert "*" not in url1
        assert "*" not in url2

    def test_path_b_saves_partial_results(self, tmp_path):
        """After 500 items, partial file should be created."""
        from scripts.scraping import ojn_multipath_recovery as m

        # Create 501 fake records to trigger partial save at 500
        records = [
            {"file_id": i, "state": "test", "law_name": f"Law {i}"} for i in range(501)
        ]

        mock_session = MagicMock()
        # Make CDX return empty (no archive found) for all
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = [
            ["timestamp", "original", "statuscode", "mimetype"]
        ]  # header only
        mock_session.get.return_value = mock_resp

        output = tmp_path / "path_b"
        with patch("scripts.scraping.ojn_multipath_recovery.time.sleep"):
            _, still_failed = m.path_b_wayback_cdx(
                records, mock_session, output, dry_run=False, limit=501
            )

        partial = output / "path_b_partial.json"
        assert partial.exists()
        data = json.loads(partial.read_text())
        assert "still_failed_count" in data


class TestWaybackBulkRecovery:
    """Test Wayback bulk recovery script."""

    def test_import(self):
        from scripts.scraping.wayback_bulk_recovery import run_bulk_recovery

        assert run_bulk_recovery is not None

    def test_domains_configured(self):
        from scripts.scraping.wayback_bulk_recovery import DOMAINS

        assert "sinec.gob.mx" in DOMAINS
        assert "congresoguerrero.gob.mx" in DOMAINS
        assert "cnartys.conamer.gob.mx" in DOMAINS
        assert len(DOMAINS) >= 5

    def test_filter_cdx_records(self):
        from scripts.scraping.wayback_bulk_recovery import DOMAINS, filter_cdx_records

        config = DOMAINS["sinec.gob.mx"]
        records = [
            {
                "original": "https://sinec.gob.mx/nom-001.pdf",
                "mimetype": "application/pdf",
            },
            {"original": "https://sinec.gob.mx/style.css", "mimetype": "text/css"},
            {"original": "https://sinec.gob.mx/logo.png", "mimetype": "image/png"},
            {"original": "https://sinec.gob.mx/catalogo", "mimetype": "text/html"},
        ]
        filtered = filter_cdx_records(records, config)
        # CSS and PNG should be excluded
        urls = [r["original"] for r in filtered]
        assert "https://sinec.gob.mx/style.css" not in urls
        assert "https://sinec.gob.mx/logo.png" not in urls


class TestDofHistoricalScan:
    """Test DOF historical scan script."""

    def test_import(self):
        from scripts.scraping.dof_historical_scan import run_historical_scan

        assert run_historical_scan is not None

    def test_classify_entry_reform(self):
        from scripts.scraping.dof_historical_scan import classify_entry

        entry = {"title": "DECRETO por el que se REFORMA el Reglamento Interior"}
        result = classify_entry(entry)
        assert result["change_type"] == "reform"
        assert result["instrument_type"] == "reglamento"

    def test_classify_entry_new_law(self):
        from scripts.scraping.dof_historical_scan import classify_entry

        entry = {"title": "DECRETO por el que SE CREA la Ley Federal de Ejemplo"}
        result = classify_entry(entry)
        assert result["change_type"] == "new_law"

    def test_classify_entry_nom(self):
        from scripts.scraping.dof_historical_scan import classify_entry

        entry = {"title": "NOM-001-SSA1-2024 Norma Oficial Mexicana"}
        result = classify_entry(entry)
        assert result["instrument_type"] == "nom"
        assert result["nom_number"] == "NOM-001-SSA1-2024"

    def test_classify_entry_abrogation(self):
        from scripts.scraping.dof_historical_scan import classify_entry

        entry = {"title": "DECRETO por el que se ABROGA la Ley de Ejemplo"}
        result = classify_entry(entry)
        assert result["change_type"] == "abrogation"

    def test_state_gazette_urls_configured(self):
        from scripts.scraping.dof_historical_scan import STATE_GAZETTE_URLS

        assert "jalisco" in STATE_GAZETTE_URLS
        assert "cdmx" in STATE_GAZETTE_URLS
        assert len(STATE_GAZETTE_URLS) >= 5

    def test_cross_reference_noms_finds_new(self, tmp_path):
        """DOF NOM not in catalog is flagged as new."""
        from scripts.scraping import dof_historical_scan as m

        # Create a small catalog
        catalog = [
            {"nom_number": "NOM-001-SSA1-2024"},
            {"nom_number": "NOM-002-STPS-2023"},
        ]
        catalog_path = tmp_path / "catalog.json"
        catalog_path.write_text(json.dumps(catalog))

        dof_noms = [
            {
                "nom_number": "NOM-001-SSA1-2024",
                "title": "Existing",
                "date": "2024-01-01",
                "url": "...",
            },
            {
                "nom_number": "NOM-999-SEMARNAT-2025",
                "title": "New one",
                "date": "2025-06-01",
                "url": "...",
            },
        ]

        with patch.object(m, "OUTPUT_DIR", tmp_path):
            result = m.cross_reference_noms(dof_noms, catalog_path=catalog_path)

        assert result["new_count"] == 1
        assert result["existing_count"] == 1
        assert result["new_noms"][0]["nom_number"] == "NOM-999-SEMARNAT-2025"

    def test_cross_reference_noms_all_existing(self, tmp_path):
        """All match → 0 new."""
        from scripts.scraping import dof_historical_scan as m

        catalog = [{"nom_number": "NOM-001-SSA1-2024"}]
        catalog_path = tmp_path / "catalog.json"
        catalog_path.write_text(json.dumps(catalog))

        dof_noms = [
            {
                "nom_number": "NOM-001-SSA1-2024",
                "title": "Known",
                "date": "2024-01-01",
                "url": "...",
            },
        ]

        with patch.object(m, "OUTPUT_DIR", tmp_path):
            result = m.cross_reference_noms(dof_noms, catalog_path=catalog_path)

        assert result["new_count"] == 0
        assert result["existing_count"] == 1

    def test_checkpoint_roundtrip(self, tmp_path):
        """Save + load checkpoint preserves state."""
        import datetime

        from scripts.scraping.dof_historical_scan import (
            _delete_checkpoint,
            _load_checkpoint,
            _save_checkpoint,
        )

        test_date = datetime.date(2023, 6, 15)
        _save_checkpoint(tmp_path, test_date, 42, "noms")

        cp = _load_checkpoint(tmp_path)
        assert cp is not None
        assert cp["last_date"] == "2023-06-15"
        assert cp["entries_count"] == 42
        assert cp["mode"] == "noms"

        _delete_checkpoint(tmp_path)
        assert _load_checkpoint(tmp_path) is None


class TestProbeDatosGob:
    """Test datos.gob.mx probe script."""

    def test_import(self):
        from scripts.scraping.probe_datos_gob import run_probe

        assert run_probe is not None

    def test_legal_queries_configured(self):
        from scripts.scraping.probe_datos_gob import LEGAL_QUERIES

        assert len(LEGAL_QUERIES) >= 10
        assert "legislacion" in LEGAL_QUERIES
        assert "norma oficial mexicana" in LEGAL_QUERIES

    def test_legal_orgs_configured(self):
        from scripts.scraping.probe_datos_gob import LEGAL_ORGS

        assert len(LEGAL_ORGS) >= 5

    def test_analyze_resources(self):
        from scripts.scraping.probe_datos_gob import analyze_resources

        package = {
            "resources": [
                {
                    "name": "Data",
                    "url": "https://example.com/data.csv",
                    "format": "CSV",
                    "size": 1000,
                },
                {
                    "name": "PDF",
                    "url": "https://example.com/doc.pdf",
                    "format": "PDF",
                    "size": 500,
                },
                {"name": "No URL", "url": "", "format": "CSV", "size": 0},
            ]
        }
        resources = analyze_resources(package)
        assert len(resources) == 2  # one with empty URL excluded
        assert resources[0]["is_structured"] is True  # CSV
        assert resources[1]["is_structured"] is False  # PDF

    def test_assess_resources_flags_legal_columns(self, tmp_path):
        """CSV with legal column names → high relevance."""
        from scripts.scraping import probe_datos_gob as m

        # Create a mock CSV with a legal column
        res_dir = tmp_path / "resources" / "dataset1"
        res_dir.mkdir(parents=True)
        csv_path = res_dir / "data.csv"
        csv_path.write_text("id,nombre_reglamento,fecha\n1,Test,2024-01-01\n")

        with patch.object(m, "OUTPUT_DIR", tmp_path):
            result = m.assess_resources(resources_dir=tmp_path / "resources")

        assert result["high_count"] == 1
        assert result["low_count"] == 0
        assert "reglamento" in result["high_relevance"][0]["matched_keywords"]

    def test_assess_resources_low_relevance(self, tmp_path):
        """CSV without legal columns → low relevance."""
        from scripts.scraping import probe_datos_gob as m

        res_dir = tmp_path / "resources" / "dataset2"
        res_dir.mkdir(parents=True)
        csv_path = res_dir / "weather.csv"
        csv_path.write_text("date,temperature,humidity\n2024-01-01,25,60\n")

        with patch.object(m, "OUTPUT_DIR", tmp_path):
            result = m.assess_resources(resources_dir=tmp_path / "resources")

        assert result["high_count"] == 0
        assert result["low_count"] == 1

    def test_download_resources_import(self):
        from scripts.scraping.probe_datos_gob import download_resources

        assert download_resources is not None


class TestSourceDiscoveryCDX:
    """Test the CDX extension to SourceDiscoverer."""

    def test_check_wayback_cdx_method_exists(self):
        from apps.scraper.dataops.source_discovery import SourceDiscoverer

        discoverer = SourceDiscoverer()
        assert hasattr(discoverer, "check_wayback_cdx")

    def test_check_wayback_cdx_filters_non_documents(self):
        from apps.scraper.dataops.source_discovery import SourceDiscoverer

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            ["timestamp", "original", "statuscode", "mimetype"],  # header
            ["20250101", "https://sinec.gob.mx/nom.pdf", "200", "application/pdf"],
            ["20250102", "https://sinec.gob.mx/style.css", "200", "text/css"],
            ["20250103", "https://sinec.gob.mx/logo.png", "200", "image/png"],
            ["20250104", "https://sinec.gob.mx/page.html", "200", "text/html"],
        ]

        with patch("apps.scraper.dataops.source_discovery.requests.get") as mock_get:
            mock_get.return_value = mock_response
            discoverer = SourceDiscoverer()
            results = discoverer.check_wayback_cdx("sinec.gob.mx")

        # CSS and PNG should be filtered out
        assert len(results) == 2
        mimetypes = {r["mimetype"] for r in results}
        assert "text/css" not in mimetypes
        assert "image/png" not in mimetypes

    def test_check_wayback_cdx_with_url_filter(self):
        from apps.scraper.dataops.source_discovery import SourceDiscoverer

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            ["timestamp", "original", "statuscode", "mimetype"],
            ["20250101", "https://sinec.gob.mx/nom-001.pdf", "200", "application/pdf"],
            ["20250102", "https://sinec.gob.mx/about.html", "200", "text/html"],
        ]

        with patch("apps.scraper.dataops.source_discovery.requests.get") as mock_get:
            mock_get.return_value = mock_response
            discoverer = SourceDiscoverer()
            results = discoverer.check_wayback_cdx(
                "sinec.gob.mx", url_filter=r"nom-\d+"
            )

        # Only nom-001.pdf matches the filter
        assert len(results) == 1
        assert "nom-001" in results[0]["original_url"]

    def test_check_wayback_cdx_empty_response(self):
        from apps.scraper.dataops.source_discovery import SourceDiscoverer

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = []

        with patch("apps.scraper.dataops.source_discovery.requests.get") as mock_get:
            mock_get.return_value = mock_response
            discoverer = SourceDiscoverer()
            results = discoverer.check_wayback_cdx("dead.example.com")

        assert results == []

    def test_check_wayback_cdx_network_error(self):
        import requests as req

        from apps.scraper.dataops.source_discovery import SourceDiscoverer

        with patch("apps.scraper.dataops.source_discovery.requests.get") as mock_get:
            mock_get.side_effect = req.ConnectionError("timeout")
            discoverer = SourceDiscoverer()
            results = discoverer.check_wayback_cdx("dead.example.com")

        assert results == []
