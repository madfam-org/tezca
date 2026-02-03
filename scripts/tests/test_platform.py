#!/usr/bin/env python3
"""
Comprehensive platform testing script.
Tests all components end-to-end with production data.
"""

import sys
from pathlib import Path
from typing import Dict, List

# Add apps to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'apps'))

from parsers.validators.schema import AKNSchemaValidator
from parsers.validators.completeness import CompletenessValidator
from parsers.quality import QualityCalculator
from parsers.akn_generator_v2 import AkomaNtosoGeneratorV2


def test_schema_validation(xml_dir: Path) -> Dict:
    """Test XML schema validation on all generated files."""
    print("\n" + "="*70)
    print("TESTING: XML Schema Validation")
    print("="*70)
    
    validator = AKNSchemaValidator()
    results = []
    
    xml_files = list(xml_dir.glob("*-v2.xml"))
    print(f"Found {len(xml_files)} XML files to validate\n")
    
    for xml_file in xml_files:
        law_name = xml_file.stem.replace('mx-fed-', '').replace('-v2', '')
        result = validator.validate(xml_file)
        
        status = "✅ VALID" if result.is_valid else "❌ INVALID"
        print(f"  {law_name:15s} {status}")
        
        if not result.is_valid:
            for error in result.errors[:3]:  # Show first 3 errors
                print(f"    ERROR: {error}")
        
        results.append({
            'law': law_name,
            'valid': result.is_valid,
            'errors': len(result.errors)
        })
    
    valid_count = sum(1 for r in results if r['valid'])
    print(f"\n📊 Schema Validation: {valid_count}/{len(results)} passed ({valid_count/len(results)*100:.1f}%)")
    
    return {'total': len(results), 'valid': valid_count, 'details': results}


def test_completeness_validation(xml_dir: Path) -> Dict:
    """Test completeness validation on all generated files."""
    print("\n" + "="*70)
    print("TESTING: Completeness Validation")
    print("="*70)
    
    validator = CompletenessValidator()
    results = []
    
    xml_files = list(xml_dir.glob("*-v2.xml"))
    print(f"Testing {len(xml_files)} XML files for completeness\n")
    
    for xml_file in xml_files:
        law_name = xml_file.stem.replace('mx-fed-', '').replace('-v2', '')
        report = validator.validate(xml_file)
        
        pass_pct = (report.passed_checks / report.total_checks * 100) if report.total_checks > 0 else 0
        status = "✅ PASS" if pass_pct >= 80 else "⚠️  WARN"
        
        print(f"  {law_name:15s} {status} ({report.passed_checks}/{report.total_checks} checks, {report.error_count} issues)")
        
        if report.issues:
            for issue in report.issues[:2]:  # Show first 2 issues
                print(f"    - {issue}")
        
        results.append({
            'law': law_name,
            'passed': report.passed_checks,
            'total': report.total_checks,
            'issues': report.error_count
        })
    
    avg_pass = sum(r['passed']/r['total'] for r in results if r['total'] > 0) / len(results) * 100
    print(f"\n📊 Completeness: {avg_pass:.1f}% average pass rate")
    
    return {'average': avg_pass, 'details': results}


def test_quality_metrics(xml_dir: Path) -> Dict:
    """Test quality metrics calculation."""
    print("\n" + "="*70)
    print("TESTING: Quality Metrics Calculation")
    print("="*70)
    
    calculator = QualityCalculator()
    results = []
    
    # Map of law slugs to expected article counts
    expected_articles = {
        'amparo': 300,
        'iva': 94,
        'cpeum': 136,
        'lisr': 351,
        'ccf': 3000,
        'lft': 1010,
        'lic': 150,
        'lfpc': 140,
        'lgsm': 400,
        'lgtoc': 400
    }
    
    xml_files = list(xml_dir.glob("*-v2.xml"))
    print(f"Calculating quality for {len(xml_files)} laws\n")
    
    for xml_file in xml_files:
        law_slug = xml_file.stem.replace('mx-fed-', '').replace('-v2', '')
        law_name = law_slug.upper()
        expected = expected_articles.get(law_slug, 100)
        
        metrics = calculator.calculate(
            xml_path=xml_file,
            law_name=law_name,
            law_slug=law_slug,
            articles_expected=expected
        )
        
        print(f"  {law_slug:15s} Grade {metrics.grade} ({metrics.overall_score:.1f}%) - {metrics.articles_found} articles")
        
        results.append({
            'law': law_slug,
            'grade': metrics.grade,
            'score': metrics.overall_score,
            'articles': metrics.articles_found
        })
    
    avg_score = sum(r['score'] for r in results) / len(results)
    grade_counts = {}
    for r in results:
        grade_counts[r['grade']] = grade_counts.get(r['grade'], 0) + 1
    
    print(f"\n📊 Quality Metrics: {avg_score:.1f}% average score")
    print(f"   Grade distribution: {dict(sorted(grade_counts.items()))}")
    
    return {'average': avg_score, 'grades': grade_counts, 'details': results}


def test_parser_functionality() -> Dict:
    """Test parser with sample text."""
    print("\n" + "="*70)
    print("TESTING: Parser Functionality")
    print("="*70)
    
    parser = AkomaNtosoGeneratorV2()
    
    # Test sample law text
    sample_text = """
TÍTULO PRIMERO
Disposiciones Generales

CAPÍTULO I
Del Objeto de la Ley

Artículo 1.- Esta ley regula las materias de interés público.

Artículo 2.- Las disposiciones son de orden público e interés social.

I. Primera fracción.
II. Segunda fracción.
III. Tercera fracción.

Artículo 3.- Se deroga.

TRANSITORIOS

PRIMERO.- Esta ley entrará en vigor al día siguiente de su publicación.

SEGUNDO.- Se abrogan todas las disposiciones contrarias.
""".strip()
    
    print("Testing parser with sample text...\n")
    
    result = parser.parse_structure_v2(sample_text)
    
    print(f"  Articles found: {result.metadata['articles']}")
    print(f"  TÍTULOs found: {result.metadata['titles']}")
    print(f"  Chapters found: {result.metadata['chapters']}")
    print(f"  TRANSITORIOS found: {len([a for a in result.articles if 'trans-' in a['id']])}")
    print(f"  Confidence: {result.metadata['confidence']*100:.1f}%")
    
    # Test FRBR metadata creation
    metadata = parser.create_frbr_metadata(
        law_type='ley',
        date_str='2024-01-01',
        slug='test',
        title='Test Law'
    )
    
    print(f"\n  FRBR Work URI: {metadata['work']['uri']}")
    print(f"  FRBR Expression URI: {metadata['expression']['uri']}")
    
    success = (
        result.metadata['articles'] >= 3 and
        result.metadata['titles'] >= 1 and
        result.metadata['confidence'] > 0.9
    )
    
    status = "✅ PASS" if success else "❌ FAIL"
    print(f"\n📊 Parser Test: {status}")
    
    return {
        'success': success,
        'articles': result.metadata['articles'],
        'confidence': result.metadata['confidence']
    }


def test_cli_tools() -> Dict:
    """Test CLI tools."""
    print("\n" + "="*70)
    print("TESTING: CLI Tools")
    print("="*70)
    
    import subprocess
    
    tests = []
    
    # Test ingestion status script
    print("\n1. Testing ingestion_status.py...")
    try:
        result = subprocess.run(
            ['python', 'scripts/ingestion_status.py', '--last', '48'],
            cwd=Path(__file__).parent.parent,
            capture_output=True,
            text=True,
            timeout=10
        )
        success = result.returncode == 0
        print(f"   {'✅ PASS' if success else '❌ FAIL'}")
        if not success:
            print(f"   Error: {result.stderr[:200]}")
        tests.append({'tool': 'ingestion_status', 'success': success})
    except Exception as e:
        print(f"   ❌ FAIL: {str(e)}")
        tests.append({'tool': 'ingestion_status', 'success': False})
    
    # Test bulk_ingest help
    print("\n2. Testing bulk_ingest.py --help...")
    try:
        result = subprocess.run(
            ['python', 'scripts/bulk_ingest.py', '--help'],
            cwd=Path(__file__).parent.parent,
            capture_output=True,
            text=True,
            timeout=5
        )
        success = result.returncode == 0 and '--laws' in result.stdout
        print(f"   {'✅ PASS' if success else '❌ FAIL'}")
        tests.append({'tool': 'bulk_ingest', 'success': success})
    except Exception as e:
        print(f"   ❌ FAIL: {str(e)}")
        tests.append({'tool': 'bulk_ingest', 'success': False})
    
    passed = sum(1 for t in tests if t['success'])
    print(f"\n📊 CLI Tools: {passed}/{len(tests)} passed")
    
    return {'total': len(tests), 'passed': passed, 'details': tests}


def main():
    """Run all platform tests."""
    print("\n" + "="*70)
    print("LEYES COMO CÓDIGO - COMPREHENSIVE PLATFORM TEST")
    print("="*70)
    print("Testing all components with production data...")
    
    # Setup paths
    base_dir = Path(__file__).parent.parent
    xml_dir = base_dir / 'data' / 'federal'
    
    if not xml_dir.exists():
        print(f"❌ ERROR: XML directory not found: {xml_dir}")
        return 1
    
    # Run all tests
    results = {}
    
    try:
        results['schema'] = test_schema_validation(xml_dir)
        results['completeness'] = test_completeness_validation(xml_dir)
        results['quality'] = test_quality_metrics(xml_dir)
        results['parser'] = test_parser_functionality()
        results['cli'] = test_cli_tools()
        
        # Final summary
        print("\n" + "="*70)
        print("FINAL TEST SUMMARY")
        print("="*70)
        
        print(f"\n✅ Schema Validation: {results['schema']['valid']}/{results['schema']['total']} valid")
        print(f"✅ Completeness Checks: {results['completeness']['average']:.1f}% average")
        print(f"✅ Quality Metrics: {results['quality']['average']:.1f}% average")
        print(f"✅ Parser Functionality: {'PASS' if results['parser']['success'] else 'FAIL'}")
        print(f"✅ CLI Tools: {results['cli']['passed']}/{results['cli']['total']} working")
        
        # Overall assessment
        overall_success = (
            results['schema']['valid'] == results['schema']['total'] and
            results['completeness']['average'] >= 80 and
            results['quality']['average'] >= 90 and
            results['parser']['success'] and
            results['cli']['passed'] == results['cli']['total']
        )
        
        print("\n" + "="*70)
        if overall_success:
            print("🎉 ALL TESTS PASSED - PLATFORM FULLY FUNCTIONAL")
        else:
            print("⚠️  SOME TESTS FAILED - REVIEW RESULTS ABOVE")
        print("="*70 + "\n")
        
        return 0 if overall_success else 1
        
    except Exception as e:
        print(f"\n❌ TEST ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
