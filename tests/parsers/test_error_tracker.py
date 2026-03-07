"""
Tests for the ErrorTracker used in the ingestion pipeline.

Verifies error recording, categorization, JSON log output, and summary.
"""

import json
import tempfile
from pathlib import Path

import pytest

from apps.parsers.error_tracker import ErrorRecord, ErrorTracker


@pytest.mark.spotcheck
class TestErrorTracker:
    """Tests for ErrorTracker functionality."""

    def test_records_errors_with_full_context(self):
        """ErrorTracker should capture law_id, category, message, stage, and context."""
        tracker = ErrorTracker()

        try:
            raise ValueError("XML parse failed at line 42")
        except Exception as e:
            tracker.track(
                law_id="cpeum",
                category="PARSE_ERROR",
                exception=e,
                stage="parse",
                context={"line": 42, "file": "cpeum.xml"},
            )

        assert len(tracker.errors) == 1
        record = tracker.errors[0]
        assert record.law_id == "cpeum"
        assert record.category == "PARSE_ERROR"
        assert "XML parse failed" in record.message
        assert record.stage == "parse"
        assert record.context["line"] == 42
        assert "Traceback" in record.stack_trace

    def test_categorizes_exceptions_correctly(self):
        """categorize_exception should map exception types and messages to categories."""
        tracker = ErrorTracker()

        # Download errors
        cat = tracker.categorize_exception(
            ConnectionError("Failed to connect"), stage="download"
        )
        assert cat == "DOWNLOAD_ERROR"

        # Parse errors
        cat = tracker.categorize_exception(
            RuntimeError("XML generation failed"), stage="parse"
        )
        assert cat == "PARSE_ERROR"

        # Extraction errors
        cat = tracker.categorize_exception(
            RuntimeError("pdf extraction issue"), stage="extract"
        )
        assert cat == "EXTRACTION_ERROR"

        # Validation errors
        cat = tracker.categorize_exception(
            AssertionError("schema validation failed"), stage="validate"
        )
        assert cat == "VALIDATION_ERROR"

        # Unknown fallback
        cat = tracker.categorize_exception(
            RuntimeError("something unexpected"), stage=None
        )
        assert cat == "UNKNOWN_ERROR"

    def test_writes_readable_json_log(self):
        """ErrorTracker should write JSONL log file when configured."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "errors.jsonl"
            tracker = ErrorTracker(log_file=log_file)

            try:
                raise IOError("Disk full")
            except Exception as e:
                tracker.track(
                    law_id="ley-amparo",
                    category="UNKNOWN_ERROR",
                    exception=e,
                    stage="storage_sync",
                    context={"disk": "/dev/sda1"},
                )

            try:
                raise ValueError("Bad date format")
            except Exception as e:
                tracker.track(
                    law_id="ley-iva",
                    category="VALIDATION_ERROR",
                    exception=e,
                    stage="validate",
                )

            assert log_file.exists()
            lines = log_file.read_text().strip().split("\n")
            assert len(lines) == 2

            record1 = json.loads(lines[0])
            assert record1["law_id"] == "ley-amparo"
            assert record1["category"] == "UNKNOWN_ERROR"
            assert "Disk full" in record1["message"]

            record2 = json.loads(lines[1])
            assert record2["law_id"] == "ley-iva"

    def test_summary_produces_correct_counts(self):
        """get_summary should group errors by category, law, and stage."""
        tracker = ErrorTracker()

        errors_to_add = [
            ("law-a", "PARSE_ERROR", "parse"),
            ("law-a", "PARSE_ERROR", "parse"),
            ("law-b", "DOWNLOAD_ERROR", "download"),
            ("law-c", "VALIDATION_ERROR", "validate"),
        ]

        for law_id, category, stage in errors_to_add:
            try:
                raise RuntimeError(f"Error in {law_id}")
            except Exception as e:
                tracker.track(
                    law_id=law_id, category=category, exception=e, stage=stage
                )

        summary = tracker.get_summary()

        assert summary["total_errors"] == 4
        assert summary["by_category"]["PARSE_ERROR"] == 2
        assert summary["by_category"]["DOWNLOAD_ERROR"] == 1
        assert summary["by_category"]["VALIDATION_ERROR"] == 1
        assert summary["by_law"]["law-a"] == 2
        assert summary["by_law"]["law-b"] == 1
        assert summary["by_stage"]["parse"] == 2
        assert len(summary["recent"]) <= 5

    def test_empty_tracker_summary(self):
        """get_summary on empty tracker returns zero counts."""
        tracker = ErrorTracker()
        summary = tracker.get_summary()
        assert summary["total_errors"] == 0
        assert summary["by_category"] == {}

    def test_error_record_summary_format(self):
        """ErrorRecord.summary() should produce a readable one-liner."""
        record = ErrorRecord(
            law_id="cpeum",
            category="PARSE_ERROR",
            message="Bad XML",
            stack_trace="",
            context={},
            timestamp="2026-03-07T12:00:00",
            stage="parse",
        )
        assert record.summary() == "[PARSE_ERROR] cpeum: Bad XML"
