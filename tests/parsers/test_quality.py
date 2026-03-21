"""Tests for quality metrics calculator -- pure unit tests.

Covers QualityMetrics dataclass properties (overall_score, grade,
total_issues, summary) and QualityCalculator private scoring methods
(_calculate_accuracy, _calculate_completeness).

No Django DB or filesystem access required.  When lxml is not installed
(e.g. lightweight CI environments), the module is shimmed via
``sys.modules`` so that ``apps.parsers.quality`` can be imported without
pulling in the native XML library.
"""

import sys
from pathlib import Path
from types import ModuleType
from unittest.mock import MagicMock, patch

import pytest

# ------------------------------------------------------------------
# Shim lxml if it is not installed so the quality module can be
# imported without the native C extension.  The shim is only active
# for tests in this file; no production behaviour changes.
# ------------------------------------------------------------------
_lxml_shimmed = False
if "lxml" not in sys.modules:
    _lxml_stub = ModuleType("lxml")
    _etree_stub = ModuleType("lxml.etree")

    # Provide the names that validators reference at class-definition
    # time (type annotations in method signatures, exception classes).
    _etree_stub.Element = type("Element", (), {})  # type: ignore[attr-defined]
    _etree_stub.XMLSchema = type("XMLSchema", (), {})  # type: ignore[attr-defined]
    _etree_stub.XMLSyntaxError = type(  # type: ignore[attr-defined]
        "XMLSyntaxError", (Exception,), {}
    )
    _etree_stub.parse = MagicMock()  # type: ignore[attr-defined]

    _lxml_stub.etree = _etree_stub  # type: ignore[attr-defined]
    sys.modules["lxml"] = _lxml_stub
    sys.modules["lxml.etree"] = _etree_stub
    _lxml_shimmed = True

from apps.parsers.quality import QualityCalculator, QualityMetrics  # noqa: E402


class TestQualityMetrics:
    """Tests for the QualityMetrics dataclass properties."""

    def _make_metrics(self, **kwargs):
        """Create a QualityMetrics with sensible defaults."""
        defaults = {
            "law_name": "Test Law",
            "law_slug": "test-law",
            "file_path": Path("/tmp/test.xml"),
        }
        defaults.update(kwargs)
        return QualityMetrics(**defaults)

    def test_overall_score_formula(self):
        """overall_score = accuracy*0.5 + completeness*0.3 + schema*0.2.

        accuracy=80, completeness=90, schema_valid=True
        -> 80*0.5 + 90*0.3 + 100*0.2 = 40 + 27 + 20 = 87.0
        """
        m = self._make_metrics(
            accuracy_score=80.0,
            completeness_score=90.0,
            schema_valid=True,
        )
        assert m.overall_score == pytest.approx(87.0)

    def test_overall_score_schema_invalid(self):
        """Schema invalid contributes 0 to the 20% weight.

        accuracy=80, completeness=90, schema_valid=False
        -> 80*0.5 + 90*0.3 + 0*0.2 = 40 + 27 + 0 = 67.0
        """
        m = self._make_metrics(
            accuracy_score=80.0,
            completeness_score=90.0,
            schema_valid=False,
        )
        assert m.overall_score == pytest.approx(67.0)

    def test_grade_a(self):
        """Score >= 95 yields grade A."""
        m = self._make_metrics(
            accuracy_score=100.0,
            completeness_score=100.0,
            schema_valid=True,
        )
        # 100*0.5 + 100*0.3 + 100*0.2 = 100.0
        assert m.grade == "A"

    def test_grade_b(self):
        """90 <= score < 95 yields grade B."""
        # 84*0.5 + 100*0.3 + 100*0.2 = 42 + 30 + 20 = 92.0
        m = self._make_metrics(
            accuracy_score=84.0,
            completeness_score=100.0,
            schema_valid=True,
        )
        assert m.overall_score == pytest.approx(92.0)
        assert m.grade == "B"

    def test_grade_c(self):
        """80 <= score < 90 yields grade C."""
        # 80*0.5 + 80*0.3 + 100*0.2 = 40 + 24 + 20 = 84.0
        m = self._make_metrics(
            accuracy_score=80.0,
            completeness_score=80.0,
            schema_valid=True,
        )
        assert m.overall_score == pytest.approx(84.0)
        assert m.grade == "C"

    def test_grade_d(self):
        """70 <= score < 80 yields grade D."""
        # 60*0.5 + 80*0.3 + 100*0.2 = 30 + 24 + 20 = 74.0
        m = self._make_metrics(
            accuracy_score=60.0,
            completeness_score=80.0,
            schema_valid=True,
        )
        assert m.overall_score == pytest.approx(74.0)
        assert m.grade == "D"

    def test_grade_f(self):
        """Score < 70 yields grade F."""
        m = self._make_metrics(
            accuracy_score=50.0,
            completeness_score=50.0,
            schema_valid=False,
        )
        # 50*0.5 + 50*0.3 + 0*0.2 = 25 + 15 + 0 = 40.0
        assert m.overall_score == pytest.approx(40.0)
        assert m.grade == "F"

    def test_total_issues_counting(self):
        """total_issues sums schema_errors + all completeness_issues values."""
        m = self._make_metrics(
            schema_errors=["err1", "err2"],
            completeness_issues={
                "articles": ["missing art 1", "missing art 2", "missing art 3"],
                "structure": ["no chapters"],
            },
        )
        # 2 schema + 3 articles + 1 structure = 6
        assert m.total_issues == 6

    def test_total_issues_zero(self):
        """No errors or issues yields total_issues == 0."""
        m = self._make_metrics(
            schema_errors=[],
            completeness_issues={},
        )
        assert m.total_issues == 0

    def test_summary_format(self):
        """summary() returns the expected formatted string."""
        m = self._make_metrics(
            law_name="Ley de Amparo",
            accuracy_score=80.0,
            completeness_score=90.0,
            schema_valid=True,
            articles_found=250,
            schema_errors=["e1"],
            completeness_issues={"gaps": ["g1", "g2"]},
        )
        result = m.summary()
        # overall = 80*0.5 + 90*0.3 + 100*0.2 = 87.0, grade = C
        # total_issues = 1 + 2 = 3
        assert result == "Ley de Amparo: Grade C (87.0%) - 250 articles, 3 issues"


class TestQualityCalculatorAccuracy:
    """Tests for QualityCalculator._calculate_accuracy private method."""

    def setup_method(self):
        """Create a QualityCalculator with mocked validators."""
        with patch("apps.parsers.quality.AKNSchemaValidator"), patch(
            "apps.parsers.quality.CompletenessValidator"
        ):
            self.calc = QualityCalculator()

    def test_perfect_coverage(self):
        """found=expected with full confidence yields 100.0."""
        score = self.calc._calculate_accuracy(found=100, expected=100, confidence=1.0)
        # coverage = min(100/100, 1.0) = 1.0
        # not over 110% so no penalty
        # score = (1.0*0.7 + 1.0*0.3)*100 = 100.0
        assert score == pytest.approx(100.0)

    def test_over_expected_penalty(self):
        """Finding >110% of expected applies a 0.95 coverage multiplier."""
        score = self.calc._calculate_accuracy(found=120, expected=100, confidence=1.0)
        # coverage = min(120/100, 1.0) = 1.0 (capped at 1.0)
        # 120 > 100*1.1=110 -> coverage *= 0.95 -> 0.95
        # score = (0.95*0.7 + 1.0*0.3)*100 = (0.665 + 0.3)*100 = 96.5
        assert score == pytest.approx(96.5)

    def test_zero_expected_returns_zero(self):
        """When expected articles is 0, accuracy is 0.0 regardless of found."""
        score = self.calc._calculate_accuracy(found=50, expected=0, confidence=1.0)
        assert score == 0.0

    def test_partial_coverage(self):
        """found=50, expected=100 with full confidence."""
        score = self.calc._calculate_accuracy(found=50, expected=100, confidence=1.0)
        # coverage = min(50/100, 1.0) = 0.5
        # not over 110% so no penalty
        # score = (0.5*0.7 + 1.0*0.3)*100 = (0.35 + 0.3)*100 = 65.0
        assert score == pytest.approx(65.0)

    def test_low_confidence_reduces_score(self):
        """Lower confidence reduces the 30% confidence component."""
        score = self.calc._calculate_accuracy(found=100, expected=100, confidence=0.5)
        # coverage = 1.0, no penalty
        # score = (1.0*0.7 + 0.5*0.3)*100 = (0.7 + 0.15)*100 = 85.0
        assert score == pytest.approx(85.0)


class TestQualityCalculatorCompleteness:
    """Tests for QualityCalculator._calculate_completeness private method."""

    def setup_method(self):
        """Create a QualityCalculator with mocked validators."""
        with patch("apps.parsers.quality.AKNSchemaValidator"), patch(
            "apps.parsers.quality.CompletenessValidator"
        ):
            self.calc = QualityCalculator()

    def _make_metrics(self, **kwargs):
        """Create a QualityMetrics with sensible defaults."""
        defaults = {
            "law_name": "Test Law",
            "law_slug": "test-law",
            "file_path": Path("/tmp/test.xml"),
        }
        defaults.update(kwargs)
        return QualityMetrics(**defaults)

    def _make_report(self, is_complete=True, issues=None):
        """Create a mock CompletenessReport."""
        report = MagicMock()
        report.is_complete = is_complete
        report.issues = issues if issues is not None else {}
        return report

    def test_full_marks_all_present(self):
        """All structural elements present and no issues yields 100."""
        metrics = self._make_metrics(
            articles_found=10,
            chapters=5,
            titles=2,
            transitorios=3,
        )
        report = self._make_report(is_complete=True)
        score = self.calc._calculate_completeness(metrics, report)
        # articles>0: +40, chapters>0: +20, transitorios>0: +20, complete: +20 = 100
        assert score == pytest.approx(100.0)

    def test_no_articles_loses_40pts(self):
        """articles_found=0 means no +40 points, max possible is 60."""
        metrics = self._make_metrics(
            articles_found=0,
            chapters=5,
            titles=2,
            transitorios=3,
        )
        report = self._make_report(is_complete=True)
        score = self.calc._calculate_completeness(metrics, report)
        # articles=0: +0, chapters>0: +20, transitorios>0: +20, complete: +20 = 60
        assert score == pytest.approx(60.0)

    def test_no_structure_loses_20pts(self):
        """chapters=0 and titles=0 means no +20 structure points."""
        metrics = self._make_metrics(
            articles_found=10,
            chapters=0,
            titles=0,
            transitorios=3,
        )
        report = self._make_report(is_complete=True)
        score = self.calc._calculate_completeness(metrics, report)
        # articles>0: +40, no structure: +0, transitorios>0: +20, complete: +20 = 80
        assert score == pytest.approx(80.0)

    def test_no_transitorios_loses_20pts(self):
        """transitorios=0 means no +20 transitorios points."""
        metrics = self._make_metrics(
            articles_found=10,
            chapters=5,
            titles=0,
            transitorios=0,
        )
        report = self._make_report(is_complete=True)
        score = self.calc._calculate_completeness(metrics, report)
        # articles>0: +40, chapters>0: +20, transitorios=0: +0, complete: +20 = 80
        assert score == pytest.approx(80.0)

    def test_incomplete_with_issues_partial_credit(self):
        """is_complete=False with 2 issue types deducts 10 from the 20-point pool."""
        metrics = self._make_metrics(
            articles_found=10,
            chapters=5,
            titles=0,
            transitorios=3,
        )
        report = self._make_report(
            is_complete=False,
            issues={
                "missing_articles": ["art 1 missing"],
                "gaps": ["gap between art 5 and art 7"],
            },
        )
        score = self.calc._calculate_completeness(metrics, report)
        # articles>0: +40, chapters>0: +20, transitorios>0: +20
        # incomplete: penalty = min(2*5, 20) = 10, partial = max(0, 20-10) = 10
        # total = 40 + 20 + 20 + 10 = 90
        assert score == pytest.approx(90.0)

    def test_incomplete_many_issues_zero_partial_credit(self):
        """4+ issue types exhaust the 20-point pool entirely."""
        metrics = self._make_metrics(
            articles_found=10,
            chapters=5,
            titles=0,
            transitorios=3,
        )
        report = self._make_report(
            is_complete=False,
            issues={
                "missing_articles": ["a"],
                "gaps": ["b"],
                "structure": ["c"],
                "metadata": ["d"],
            },
        )
        score = self.calc._calculate_completeness(metrics, report)
        # penalty = min(4*5, 20) = 20, partial = max(0, 20-20) = 0
        # total = 40 + 20 + 20 + 0 = 80
        assert score == pytest.approx(80.0)

    def test_nothing_present_and_incomplete(self):
        """Worst case: no articles, no structure, no transitorios, incomplete."""
        metrics = self._make_metrics(
            articles_found=0,
            chapters=0,
            titles=0,
            transitorios=0,
        )
        report = self._make_report(
            is_complete=False,
            issues={
                "critical": ["no content found"],
                "structure": ["no body element"],
                "articles": ["zero articles"],
                "transitorios": ["missing transitorios"],
            },
        )
        score = self.calc._calculate_completeness(metrics, report)
        # 0 + 0 + 0 + max(0, 20 - min(4*5, 20)) = 0
        assert score == pytest.approx(0.0)

    def test_titles_alone_satisfy_structure(self):
        """Having titles but no chapters still earns the 20 structure points."""
        metrics = self._make_metrics(
            articles_found=10,
            chapters=0,
            titles=3,
            transitorios=2,
        )
        report = self._make_report(is_complete=True)
        score = self.calc._calculate_completeness(metrics, report)
        # articles: +40, titles>0: +20, transitorios: +20, complete: +20 = 100
        assert score == pytest.approx(100.0)
