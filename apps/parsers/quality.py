"""
Quality metrics calculator for parsed Akoma Ntoso XML.

Calculates accuracy scores, completeness grades, and overall quality metrics.
"""

from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, Union
from dataclasses import dataclass, field
import time

# Import validators
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from parsers.validators import (
    AKNSchemaValidator,
    ValidationResult,
    CompletenessValidator,
    CompletenessReport,
)


@dataclass
class QualityMetrics:
    """Comprehensive quality metrics for a parsed law."""
    
    # Identification
    law_name: str
    law_slug: str
    file_path: Path
    timestamp: datetime = field(default_factory=datetime.now)
    
    # Counts
    articles_found: int = 0
    articles_expected: int = 0
    chapters: int = 0
    titles: int = 0
    transitorios: int = 0
    metadata_annotations: int = 0
    
    # Scores (0-100)
    accuracy_score: float = 0.0
    completeness_score: float = 0.0
    confidence: float = 0.0  # Parser confidence (0-1)
    
    # Validation
    schema_valid: bool = False
    schema_errors: list = field(default_factory=list)
    completeness_issues: Dict[str, list] = field(default_factory=dict)
    warnings: list = field(default_factory=list)
    
    # Performance
    parse_time_seconds: float = 0.0
    file_size_mb: float = 0.0
    parser_version: str = "v2"
    
    @property
    def overall_score(self) -> float:
        """
        Overall quality score (0-100).
        
        Weighted average:
        - Accuracy: 50%
        - Completeness: 30%
        - Schema validity: 20%
        """
        schema_score = 100 if self.schema_valid else 0
        return (
            self.accuracy_score * 0.5 +
            self.completeness_score * 0.3 +
            schema_score * 0.2
        )
    
    @property
    def grade(self) -> str:
        """Letter grade based on overall score."""
        score = self.overall_score
        if score >= 95: return 'A'
        if score >= 90: return 'B'
        if score >= 80: return 'C'
        if score >= 70: return 'D'
        return 'F'
    
    @property
    def total_issues(self) -> int:
        """Total validation issues."""
        return (
            len(self.schema_errors) +
            sum(len(issues) for issues in self.completeness_issues.values())
        )
    
    def summary(self) -> str:
        """Human-readable summary."""
        return (
            f"{self.law_name}: Grade {self.grade} "
            f"({self.overall_score:.1f}%) - "
            f"{self.articles_found} articles, "
            f"{self.total_issues} issues"
        )


class QualityCalculator:
    """
    Calculate quality metrics for parsed laws.
    
    Usage:
        calc = QualityCalculator()
        metrics = calc.calculate(
            xml_path='data/federal/mx-fed-amparo-v2.xml',
            law_name='Ley de Amparo',
            articles_expected=300,
            parse_time=23.5
        )
        print(f"Grade: {metrics.grade}")
    """
    
    def __init__(self, schema_path: Optional[Path] = None):
        """Initialize calculator with validators."""
        self.schema_validator = AKNSchemaValidator(schema_path)
        self.completeness_validator = CompletenessValidator()
    
    def calculate(
        self,
        xml_path: Union[Path, str],
        law_name: str,
        law_slug: str = None,
        articles_expected: int = None,
        parse_time: float = 0.0,
        parser_confidence: float = 1.0
    ) -> QualityMetrics:
        """
        Calculate all quality metrics for a law.
        
        Args:
            xml_path: Path to XML file
            law_name: Name of the law
            law_slug: URL-safe slug
            articles_expected: Expected number of articles (for accuracy calc)
            parse_time: Time taken to parse (seconds)
            parser_confidence: Confidence score from parser (0-1)
        
        Returns:
            QualityMetrics object with all calculated scores
        """
        xml_path = Path(xml_path)
        
        if law_slug is None:
            law_slug = law_name.lower().replace(' ', '-')[:50]
        
        metrics = QualityMetrics(
            law_name=law_name,
            law_slug=law_slug,
            file_path=xml_path,
            parse_time_seconds=parse_time,
            confidence=parser_confidence
        )
        
        # File size
        if xml_path.exists():
            metrics.file_size_mb = xml_path.stat().st_size / (1024 * 1024)
        
        # Schema validation
        schema_result = self.schema_validator.validate(xml_path)
        metrics.schema_valid = schema_result.is_valid
        metrics.schema_errors = schema_result.errors
        metrics.warnings = schema_result.warnings
        
        # Completeness validation
        completeness_result = self.completeness_validator.validate(xml_path)
        metrics.completeness_issues = completeness_result.issues
        
        # Extract counts from XML
        from lxml import etree
        try:
            tree = etree.parse(str(xml_path))
            root = tree.getroot()
            ns = {'akn': 'http://docs.oasis-open.org/legaldocml/ns/akn/3.0'}
            
            # Count elements
            metrics.articles_found = len(root.findall('.//akn:article', ns))
            metrics.chapters = len(root.findall('.//akn:chapter', ns))
            metrics.titles = len(root.findall('.//akn:title', ns))
            
            # Estimate TRANSITORIOS (articles with 'trans-' in ID)
            articles = root.findall('.//akn:article', ns)
            metrics.transitorios = len([a for a in articles if 'trans-' in a.get('id', '')])
            
            # Count metadata annotations (notes)
            metrics.metadata_annotations = len(root.findall('.//akn:note', ns))
            
        except Exception as e:
            metrics.warnings.append(f"Could not parse XML for metrics: {e}")
        
        # Set expected articles if not provided
        if articles_expected is None:
            # Use found articles as baseline
            articles_expected = metrics.articles_found
        
        metrics.articles_expected = articles_expected
        
        # Calculate scores
        metrics.accuracy_score = self._calculate_accuracy(
            metrics.articles_found,
            articles_expected,
            parser_confidence
        )
        
        metrics.completeness_score = self._calculate_completeness(
            metrics,
            completeness_result
        )
        
        return metrics
    
    def _calculate_accuracy(
        self,
        found: int,
        expected: int,
        confidence: float
    ) -> float:
        """
        Calculate accuracy score (0-100).
        
        Combines article coverage with parser confidence.
        """
        if expected == 0:
            return 0.0
        
        # Article coverage (0-1)
        coverage = min(found / expected, 1.0)
        
        # Penalize if way over expected (suggests false positives)
        if found > expected * 1.1:
            coverage *= 0.95
        
        # Weighted score
        # 70% coverage, 30% confidence
        score = (coverage * 0.7 + confidence * 0.3) * 100
        
        return min(100.0, score)
    
    def _calculate_completeness(
        self,
        metrics: QualityMetrics,
        completeness_result: CompletenessReport
    ) -> float:
        """
        Calculate completeness score (0-100).
        
        Based on:
        - Has articles: 40%
        - Has structure (chapters/titles): 20%
        - Has TRANSITORIOS: 20%
        - No completeness issues: 20%
        """
        score = 0.0
        
        # Has articles (40 points)
        if metrics.articles_found > 0:
            score += 40
        
        # Has structure (20 points)
        if metrics.chapters > 0 or metrics.titles > 0:
            score += 20
        
        # Has TRANSITORIOS (20 points)
        if metrics.transitorios > 0:
            score += 20
        
        # No completeness issues (20 points)
        if completeness_result.is_complete:
            score += 20
        else:
            # Partial credit - deduct points per issue type
            issue_penalty = min(len(completeness_result.issues) * 5, 20)
            score += max(0, 20 - issue_penalty)
        
        return score
    
    def print_report(self, metrics: QualityMetrics):
        """Print formatted quality report."""
        print("=" * 70)
        print(f"QUALITY REPORT: {metrics.law_name}")
        print("=" * 70)
        
        print(f"\n📊 Overall Grade: {metrics.grade} ({metrics.overall_score:.1f}%)")
        print(f"Timestamp: {metrics.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        
        print("\n📈 Scores:")
        print(f"  Accuracy:     {metrics.accuracy_score:.1f}%")
        print(f"  Completeness: {metrics.completeness_score:.1f}%")
        print(f"  Confidence:   {metrics.confidence*100:.1f}%")
        print(f"  Schema Valid: {'✅ Yes' if metrics.schema_valid else '❌ No'}")
        
        print("\n📊 Structure:")
        print(f"  TÍTULOs:      {metrics.titles}")
        print(f"  Chapters:     {metrics.chapters}")
        print(f"  Articles:     {metrics.articles_found} / {metrics.articles_expected}")
        print(f"  TRANSITORIOS: {metrics.transitorios}")
        print(f"  Reforms:      {metrics.metadata_annotations}")
        
        print("\n⚠️  Validation:")
        if metrics.total_issues == 0:
            print("  ✅ No issues found")
        else:
            print(f"  {metrics.total_issues} total issues:")
            if metrics.schema_errors:
                print(f"    • {len(metrics.schema_errors)} schema errors")
            for check, issues in metrics.completeness_issues.items():
                print(f"    • {len(issues)} {check} issues")
        
        print("\n⏱️  Performance:")
        print(f"  Parse time:   {metrics.parse_time_seconds:.1f}s")
        print(f"  File size:    {metrics.file_size_mb:.2f} MB")
        print(f"  Speed:        {metrics.file_size_mb/metrics.parse_time_seconds if metrics.parse_time_seconds > 0 else 0:.2f} MB/s")
        print(f"  Parser:       {metrics.parser_version}")
        
        print("\n" + "=" * 70)


def main():
    """Calculate metrics for all v2 XMLs."""
    
    print("📊 Quality Metrics Calculator\n")
    
    calc = QualityCalculator()
    
    # Test cases with expected article counts
    test_cases = [
        {
            'file': 'data/federal/mx-fed-amparo-v2.xml',
            'name': 'Ley de Amparo',
            'slug': 'amparo',
            'expected': 300,
            'parse_time': 23.0,
            'confidence': 0.999,
        },
        {
            'file': 'data/federal/mx-fed-iva-v2.xml',
            'name': 'Ley del IVA',
            'slug': 'iva',
            'expected': 94,
            'parse_time': 20.0,
            'confidence': 0.998,
        },
    ]
    
    all_metrics = []
    
    for test in test_cases:
        file_path = Path(test['file'])
        if not file_path.exists():
            print(f"⚠️  Skipping {test['name']} - file not found\n")
            continue
        
        metrics = calc.calculate(
            xml_path=file_path,
            law_name=test['name'],
            law_slug=test['slug'],
            articles_expected=test.get('expected'),
            parse_time=test.get('parse_time', 0),
            parser_confidence=test.get('confidence', 1.0)
        )
        
        calc.print_report(metrics)
        print()
        
        all_metrics.append(metrics)
    
    # Summary
    if all_metrics:
        print("=" * 70)
        print("SUMMARY - ALL LAWS")
        print("=" * 70)
        
        avg_accuracy = sum(m.accuracy_score for m in all_metrics) / len(all_metrics)
        avg_overall = sum(m.overall_score for m in all_metrics) / len(all_metrics)
        
        print(f"\nTotal laws: {len(all_metrics)}")
        print(f"Average accuracy: {avg_accuracy:.1f}%")
        print(f"Average overall: {avg_overall:.1f}%")
        
        grade_dist = {}
        for m in all_metrics:
            grade_dist[m.grade] = grade_dist.get(m.grade, 0) + 1
        
        print(f"\nGrade distribution:")
        for grade in ['A', 'B', 'C', 'D', 'F']:
            count = grade_dist.get(grade, 0)
            if count > 0:
                print(f"  {grade}: {count}")
        
        print("\nIndividual results:")
        for m in all_metrics:
            print(f"  {m.summary()}")
        
        print("=" * 70)


if __name__ == "__main__":
    main()
