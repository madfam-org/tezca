"""
XSD Schema validator for Akoma Ntoso XML.

Validates generated XML against Akoma Ntoso 3.0 schema to ensure specification compliance.
"""

from lxml import etree
from pathlib import Path
from typing import Tuple, List, Dict, Any, Union
from dataclasses import dataclass
from datetime import datetime


@dataclass
class ValidationResult:
    """Result of schema validation."""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    file_path: Path
    timestamp: datetime
    
    @property
    def has_issues(self) -> bool:
        """Check if there are any errors or warnings."""
        return len(self.errors) > 0 or len(self.warnings) > 0
    
    def summary(self) -> str:
        """Get summary string."""
        if self.is_valid:
            return f"✅ Valid ({len(self.warnings)} warnings)"
        return f"❌ Invalid ({len(self.errors)} errors, {len(self.warnings)} warnings)"


class AKNSchemaValidator:
    """
    Validate XML against Akoma Ntoso 3.0 XSD schema.
    
    Usage:
        validator = AKNSchemaValidator('schemas/akn-3.0.xsd')
        result = validator.validate('data/federal/mx-fed-amparo.xml')
        
        if result.is_valid:
            print("✅ Valid XML")
        else:
            for error in result.errors:
                print(f"❌ {error}")
    """
    
    def __init__(self, schema_path: Path = None):
        """
        Initialize validator.
        
        Args:
            schema_path: Path to AKN XSD schema file.
                        If None, uses basic well-formedness check only.
        """
        self.schema_path = schema_path
        self.schema = None
        
        if schema_path and schema_path.exists():
            try:
                schema_doc = etree.parse(str(schema_path))
                self.schema = etree.XMLSchema(schema_doc)
            except Exception as e:
                print(f"⚠️  Could not load schema: {e}")
                print("   Will use well-formedness validation only")
    
    def validate(self, xml_path: Union[Path, str]) -> ValidationResult:
        """
        Validate XML file.
        
        Args:
            xml_path: Path to XML file to validate
        
        Returns:
            ValidationResult with validation status and issues
        """
        xml_path = Path(xml_path)
        errors = []
        warnings = []
        
        # Check file exists
        if not xml_path.exists():
            return ValidationResult(
                is_valid=False,
                errors=[f"File not found: {xml_path}"],
                warnings=[],
                file_path=xml_path,
                timestamp=datetime.now()
            )
        
        try:
            # Parse XML
            doc = etree.parse(str(xml_path))
            
            # Well-formedness check passed
            if self.schema is None:
                # No schema available, just check well-formedness
                warnings.append("No XSD schema available - well-formedness check only")
                return ValidationResult(
                    is_valid=True,
                    errors=[],
                    warnings=warnings,
                    file_path=xml_path,
                    timestamp=datetime.now()
                )
            
            # Schema validation
            is_valid = self.schema.validate(doc)
            
            if not is_valid:
                # Collect errors from schema
                for error in self.schema.error_log:
                    errors.append(f"Line {error.line}: {error.message}")
            
            # Additional checks
            root = doc.getroot()
            
            # Check namespace
            if root.tag != '{http://docs.oasis-open.org/legaldocml/ns/akn/3.0}akomaNtoso':
                warnings.append(f"Root element is {root.tag}, expected akomaNtoso")
            
            # Check for required meta elements
            meta = root.find('.//{http://docs.oasis-open.org/legaldocml/ns/akn/3.0}meta')
            if meta is None:
                errors.append("Missing required <meta> element")
            
            body = root.find('.//{http://docs.oasis-open.org/legaldocml/ns/akn/3.0}body')
            if body is None:
                errors.append("Missing required <body> element")
            
            return ValidationResult(
                is_valid=(is_valid and len(errors) == 0),
                errors=errors,
                warnings=warnings,
                file_path=xml_path,
                timestamp=datetime.now()
            )
            
        except etree.XMLSyntaxError as e:
            return ValidationResult(
                is_valid=False,
                errors=[f"XML Syntax Error: {e}"],
                warnings=[],
                file_path=xml_path,
                timestamp=datetime.now()
            )
        except Exception as e:
            return ValidationResult(
                is_valid=False,
                errors=[f"Validation Error: {e}"],
                warnings=[],
                file_path=xml_path,
                timestamp=datetime.now()
            )
    
    def validate_batch(self, xml_paths: List[Path]) -> Dict[str, ValidationResult]:
        """
        Validate multiple XML files.
        
        Args:
            xml_paths: List of XML file paths
        
        Returns:
            Dictionary mapping file paths to validation results
        """
        results = {}
        
        for xml_path in xml_paths:
            result = self.validate(xml_path)
            results[str(xml_path)] = result
        
        return results
    
    def print_report(self, result: ValidationResult):
        """Print formatted validation report."""
        print("=" * 70)
        print(f"SCHEMA VALIDATION: {result.file_path.name}")
        print("=" * 70)
        
        print(f"\nStatus: {result.summary()}")
        print(f"Timestamp: {result.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        
        if result.errors:
            print(f"\n❌ Errors ({len(result.errors)}):")
            for i, error in enumerate(result.errors, 1):
                print(f"   {i}. {error}")
        
        if result.warnings:
            print(f"\n⚠️  Warnings ({len(result.warnings)}):")
            for i, warning in enumerate(result.warnings, 1):
                print(f"   {i}. {warning}")
        
        if not result.has_issues:
            print("\n✅ No issues found - XML is valid!")
        
        print("=" * 70)


def main():
    """Test schema validator on existing XMLs."""
    
    print("🔍 Akoma Ntoso Schema Validator")
    print()
    
    # Initialize validator (no schema file yet, will use well-formedness)
    validator = AKNSchemaValidator()
    
    # Find all XML files
    xml_dir = Path("data/federal")
    xml_files = list(xml_dir.glob("*.xml"))
    
    if not xml_files:
        print("❌ No XML files found in data/federal/")
        return
    
    print(f"Found {len(xml_files)} XML file(s) to validate\n")
    
    # Validate each
    results = validator.validate_batch(xml_files)
    
    # Print summary
    valid_count = sum(1 for r in results.values() if r.is_valid)
    
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Total files: {len(results)}")
    print(f"Valid: {valid_count}")
    print(f"Invalid: {len(results) - valid_count}")
    
    print("\nFile Results:")
    for file_path, result in results.items():
        print(f"  {Path(file_path).name}: {result.summary()}")
    
    print("=" * 70)
    
    # Detailed report for any invalid files
    invalid_results = [r for r in results.values() if not r.is_valid]
    if invalid_results:
        print("\nDETAILED ERROR REPORTS:")
        for result in invalid_results:
            validator.print_report(result)


if __name__ == "__main__":
    main()
