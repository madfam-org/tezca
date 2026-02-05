"""
Completeness validation for parsed Akoma Ntoso XML.

Checks for missing content, gaps, and structural issues.
"""

import re
from lxml import etree
from pathlib import Path
from typing import List, Dict, Any, Union
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class CompletenessReport:
    """Report on completeness validation."""
    file_path: Path
    timestamp: datetime
    checks_run: int = 0
    issues: Dict[str, List[str]] = field(default_factory=dict)
    
    def add_issue(self, check_name: str, issue: str):
        """Add an issue to the report."""
        if check_name not in self.issues:
            self.issues[check_name] = []
        self.issues[check_name].append(issue)
    
    @property
    def total_issues(self) -> int:
        """Total number of issues found."""
        return sum(len(issues) for issues in self.issues.values())
    
    @property
    def is_complete(self) -> bool:
        """Check if no issues found."""
        return self.total_issues == 0
    
    def summary(self) -> str:
        """Get summary string."""
        if self.is_complete:
            return f"✅ Complete ({self.checks_run} checks passed)"
        return f"⚠️  {self.total_issues} issue(s) found across {len(self.issues)} check(s)"


class CompletenessValidator:
    """
    Validate completeness of parsed law.
    
    Checks:
    - Article sequence (no gaps)
    - FRBR metadata complete
    - Content length (not suspiciously short)
    - Hierarchy makes sense
    """
    
    NS = {'akn': 'http://docs.oasis-open.org/legaldocml/ns/akn/3.0'}
    
    def __init__(self):
        self.checks = [
            self.check_article_sequence,
            self.check_frbr_metadata,
            self.check_content_length,
            self.check_hierarchy,
            self.check_structure_elements,
        ]
    
    def validate(self, xml_path: Union[Path, str]) -> CompletenessReport:
        """
        Run all completeness checks.
        
        Args:
            xml_path: Path to XML file
        
        Returns:
            CompletenessReport with all issues found
        """
        xml_path = Path(xml_path)
        report = CompletenessReport(
            file_path=xml_path,
            timestamp=datetime.now()
        )
        
        if not xml_path.exists():
            report.add_issue('file_check', f"File not found: {xml_path}")
            return report
        
        try:
            tree = etree.parse(str(xml_path))
            root = tree.getroot()
            
            # Run all checks
            for check in self.checks:
                check_name = check.__name__.replace('check_', '')
                issues = check(root, xml_path)
                report.checks_run += 1
                
                for issue in issues:
                    report.add_issue(check_name, issue)
            
        except Exception as e:
            report.add_issue('parse_error', f"Failed to parse XML: {e}")
        
        return report
    
    def check_article_sequence(self, root: etree.Element, xml_path: Path) -> List[str]:
        """Check for gaps in article numbering."""
        issues = []
        
        # Find all articles
        articles = root.findall('.//akn:article', self.NS)
        
        if len(articles) == 0:
            issues.append("No articles found in document")
            return issues
        
        # Extract article numbers
        article_numbers = []
        for article in articles:
            num_elem = article.find('akn:num', self.NS)
            if num_elem is not None and num_elem.text:
                # Extract number from "Artículo 5" or just "5"
                match = re.search(r'\d+', num_elem.text)
                if match:
                    article_numbers.append((int(match.group()), num_elem.text))
        
        if not article_numbers:
            issues.append("Could not extract article numbers")
            return issues
        
        # Sort by number
        article_numbers.sort(key=lambda x: x[0])
        
        # Check for gaps (allowing some flexibility for lettered articles)
        prev_num = None
        for num, text in article_numbers:
            if prev_num is not None:
                gap = num - prev_num
                # Gap > 5 is suspicious (allows for A, B, C variations)
                if gap > 5:
                    issues.append(f"Large gap: Article {prev_num} → {num} (gap of {gap})")
            prev_num = num
        
        return issues
    
    def check_frbr_metadata(self, root: etree.Element, xml_path: Path) -> List[str]:
        """Ensure all required FRBR elements are present."""
        issues = []
        
        meta = root.find('.//akn:meta', self.NS)
        if meta is None:
            issues.append("Missing <meta> element")
            return issues
        
        # Check for FRBR Work, Expression, Manifestation
        required_frbr = ['FRBRWork', 'FRBRExpression', 'FRBRManifestation']
        
        for frbr_type in required_frbr:
            frbr_elem = meta.find(f'.//akn:{frbr_type}', self.NS)
            if frbr_elem is None:
                issues.append(f"Missing <{frbr_type}> element")
                continue
            
            # Check sub-elements
            required_sub = ['FRBRthis', 'FRBRuri', 'FRBRdate']
            for sub_elem in required_sub:
                if frbr_elem.find(f'akn:{sub_elem}', self.NS) is None:
                    issues.append(f"Missing <{sub_elem}> in <{frbr_type}>")
        
        return issues
    
    def check_content_length(self, root: etree.Element, xml_path: Path) -> List[str]:
        """Flag suspiciously short articles."""
        issues = []
        
        articles = root.findall('.//akn:article', self.NS)
        short_articles = []
        
        for article in articles:
            # Get article ID
            art_id = article.get('id', 'unknown')
            
            # Find content
            content_elems = article.findall('.//akn:p', self.NS)
            total_content = ''.join(
                elem.text or '' for elem in content_elems
            )
            
            # Flag if < 20 characters (likely incomplete)
            if len(total_content) < 20:
                short_articles.append((art_id, len(total_content)))
        
        if short_articles:
            # Only report if > 5% of articles are short
            if len(short_articles) > len(articles) * 0.05:
                issues.append(
                    f"{len(short_articles)} articles with < 20 characters "
                    f"({len(short_articles)/len(articles)*100:.1f}% of total)"
                )
            
            # Always report if any are suspiciously empty
            empty = [art for art, length in short_articles if length < 5]
            if empty:
                issues.append(f"Suspiciously empty articles: {', '.join(empty[:5])}")
        
        return issues
    
    def check_hierarchy(self, root: etree.Element, xml_path: Path) -> List[str]:
        """Validate structural hierarchy makes sense."""
        issues = []
        
        body = root.find('.//akn:body', self.NS)
        if body is None:
            issues.append("Missing <body> element")
            return issues
        
        # Count structure elements
        structure_counts = {
            'book': len(body.findall('.//akn:book', self.NS)),
            'title': len(body.findall('.//akn:title', self.NS)),
            'chapter': len(body.findall('.//akn:chapter', self.NS)),
            'section': len(body.findall('.//akn:section', self.NS)),
            'article': len(body.findall('.//akn:article', self.NS)),
        }
        
        # Check for orphaned articles (directly under body with no intermediate structure)
        direct_articles = len(body.findall('./akn:article', self.NS))
        if direct_articles > 0 and structure_counts['chapter'] == 0:
            # This is OK - some laws have flat structure
            pass
        
        # Check article/chapter ratio
        if structure_counts['chapter'] > 0:
            articles_per_chapter = structure_counts['article'] / structure_counts['chapter']
            if articles_per_chapter < 1:
                issues.append(
                    f"Low article/chapter ratio: {articles_per_chapter:.1f} "
                    f"(expected each chapter to have articles)"
                )
        
        return issues
    
    def check_structure_elements(self, root: etree.Element, xml_path: Path) -> List[str]:
        """Check structural elements have proper numbering."""
        issues = []
        
        # Check chapters have numbering
        chapters = root.findall('.//akn:chapter', self.NS)
        for chapter in chapters:
            num_elem = chapter.find('akn:num', self.NS)
            if num_elem is None or not num_elem.text:
                chapter_id = chapter.get('id', 'unknown')
                issues.append(f"Chapter {chapter_id} missing <num> element")
        
        # Check titles have numbering
        titles = root.findall('.//akn:title', self.NS)
        for title in titles:
            num_elem = title.find('akn:num', self.NS)
            if num_elem is None or not num_elem.text:
                title_id = title.get('id', 'unknown')
                issues.append(f"Title {title_id} missing <num> element")
        
        return issues
    
    def print_report(self, report: CompletenessReport):
        """Print formatted completeness report."""
        print("=" * 70)
        print(f"COMPLETENESS VALIDATION: {report.file_path.name}")
        print("=" * 70)
        
        print(f"\nStatus: {report.summary()}")
        print(f"Checks run: {report.checks_run}")
        print(f"Timestamp: {report.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        
        if report.issues:
            print(f"\n⚠️  Issues found:")
            for check_name, issues in report.issues.items():
                print(f"\n  {check_name.replace('_', ' ').title()} ({len(issues)}):")
                for issue in issues:
                    print(f"    • {issue}")
        else:
            print("\n✅ No issues found - document is complete!")
        
        print("=" * 70)


def main():
    """Test completeness validator on existing XMLs."""
    
    print("🔍 Akoma Ntoso Completeness Validator\n")
    
    validator = CompletenessValidator()
    
    # Find all v2 XMLs (most recently generated)
    xml_dir = Path("data/federal")
    xml_files = [
        xml_dir / "mx-fed-amparo-v2.xml",
        xml_dir / "mx-fed-iva-v2.xml",
    ]
    
    xml_files = [f for f in xml_files if f.exists()]
    
    if not xml_files:
        print("❌ No V2 XML files found")
        return
    
    print(f"Found {len(xml_files)} XML file(s) to validate\n")
    
    # Validate each
    reports = []
    for xml_file in xml_files:
        report = validator.validate(xml_file)
        reports.append(report)
        validator.print_report(report)
        print()
    
    # Summary
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    complete_count = sum(1 for r in reports if r.is_complete)
    print(f"Total files: {len(reports)}")
    print(f"Complete: {complete_count}")
    print(f"With issues: {len(reports) - complete_count}")
    
    print("\nFile Results:")
    for report in reports:
        print(f"  {report.file_path.name}: {report.summary()}")
    
    print("=" * 70)


if __name__ == "__main__":
    main()
