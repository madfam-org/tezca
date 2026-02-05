"""
Akoma Ntoso XML Generator V2 - Enhanced Parser

Improvements over v1:
- Multi-pattern matching for better coverage
- TRANSITORIOS parsing
- Reform metadata extraction  
- Confidence scoring
- Better error reporting
"""

import re
from pathlib import Path
from datetime import date
from lxml import etree
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass, field
import sys
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import pattern library
from apps.parsers.patterns import (
    compile_article_patterns,
    compile_structure_patterns,  
    compile_transitorios_patterns,
    extract_reforms,
    is_derogated,
    roman_to_int,
)


@dataclass
class ParseResult:
    """Result of parsing operation with metadata."""
    elements: List[Dict] = field(default_factory=list)
    confidence: float = 0.0
    warnings: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def add_warning(self, message: str):
        """Add a warning message."""
        self.warnings.append(message)


class AkomaNtosoGeneratorV2:
    """
    Enhanced Akoma Ntoso XML generator with improved accuracy.
    
    Key improvements:
    - Multi-pattern matching for articles
    - LIBRO/TÍTULO/PARTE detection
    - TRANSITORIOS parsing
    - Reform metadata extraction
    - Confidence scoring
    """
    
    # Akoma Ntoso namespaces
    NS = {
        'akn': 'http://docs.oasis-open.org/legaldocml/ns/akn/3.0'
    }
    
    def __init__(self):
        self.nsmap = {None: self.NS['akn']}
        
        # Compile patterns
        self.article_patterns = compile_article_patterns()
        self.structure_patterns = compile_structure_patterns()
        self.transitorios_patterns = compile_transitorios_patterns()
    
    def create_frbr_metadata(
        self,
        law_type: str,
        date_str: str,
        slug: str,
        title: str
    ) -> Dict[str, Any]:
        """Create FRBR metadata for the law."""
        return {
            'work_uri': f"/mx/fed/{law_type}/{date_str}/{slug}/main",
            'expression_uri': f"/mx/fed/{law_type}/{date_str}/{slug}/spa@/main",
            'manifestation_uri': f"/mx/fed/{law_type}/{date_str}/{slug}/spa@/main.xml",
            'date': date_str,
            'title': title,
            'country': 'mx',
            'language': 'spa'
        }
    
    def _try_patterns(self, text: str, patterns: List, line_num: int = 0) -> Tuple[bool, Any]:
        """
        Try multiple patterns on text.
        
        Returns:
            (matched, match_object)
        """
        for pattern in patterns:
            match = pattern.match(text)
            if match:
                return True, match
        return False, None
    
    def _find_structure_elements(self, lines: List[str], element_type: str) -> List[Dict]:
        """
        Find structural elements (titles, books, chapters, etc).
        
        Args:
            lines: Text lines
            element_type: 'title', 'book', 'chapter', etc.
        
        Returns:
            List of element dicts
        """
        elements = []
        patterns = self.structure_patterns.get(element_type, [])
        
        for i, line in enumerate(lines):
            line = line.strip()
            matched, match = self._try_patterns(line, patterns)
            
            if matched:
                number = match.group(1)
                
                # Get description (often on next line)
                description = ""
                if i + 1 < len(lines):
                    next_line = lines[i + 1].strip()
                    # Check if next line is content, not another structure element
                    is_structure = any(self._try_patterns(next_line, self.structure_patterns[k])[0] 
                                     for k in self.structure_patterns.keys())
                    if next_line and not is_structure:
                        description = next_line
                
                elements.append({
                    'type': element_type,
                    'id': f"{element_type}-{len(elements) + 1}",
                    'number': number,
                    'description': description,
                    'line_number': i,
                    'full_text': f"{line} {description}".strip()
                })
        
        return elements
    
    def _find_articles(self, lines: List[str]) -> List[Dict]:
        """
        Find articles with enhanced pattern matching.
        
        Returns:
            List of article dicts
        """
        articles = []
        i = 0
        
        while i < len(lines):
            line = lines[i].strip()
            
            # Try all article patterns
            matched, match = self._try_patterns(line, self.article_patterns)
            
            if matched:
                # Extract article number (could be 5, 5A, 27-A, etc.)
                art_num = match.group(1)
                if match.lastindex > 1 and match.group(2):  # Lettered article
                    art_num = f"{art_num}-{match.group(2)}"
                
                # Collect content until next article/structure
                content_lines = [line]
                j = i + 1
                while j < len(lines):
                    next_line = lines[j].strip()
                    
                    # Stop at next article or major structure
                    if self._try_patterns(next_line, self.article_patterns)[0]:
                        break
                    if any(self._try_patterns(next_line, self.structure_patterns[k])[0] 
                          for k in ['book', 'title', 'chapter']):
                        break
                    
                    if next_line:
                        content_lines.append(next_line)
                    j += 1
                
                full_content = '\n'.join(content_lines)
                
                # Extract reform metadata
                cleaned_content, reforms = extract_reforms(full_content)
                
                # Check if derogated
                derogated = is_derogated(cleaned_content)
                
                articles.append({
                    'type': 'article',
                    'id': f"art-{art_num.lower().replace('-', '')}",
                    'number': art_num,
                    'content': cleaned_content,
                    'reforms': reforms,
                    'derogated': derogated,
                    'line_number': i,
                    'confidence': self._article_confidence(cleaned_content)
                })
                
                i = j - 1
            
            i += 1
        
        return articles
    
    def _find_transitorios(self, text: str) -> List[Dict]:
        """
        Parse TRANSITORIOS section.
        
        Returns:
            List of transitory article dicts
        """
        # Find TRANSITORIOS header
        trans_start = None
        for pattern in self.transitorios_patterns['header']:
            match = pattern.search(text)
            if match:
                trans_start = match.end()
                break
        
        if trans_start is None:
            return []
        
        transitorios = []
        trans_text = text[trans_start:]
        
        # Find ordinal articles
        from apps.parsers.patterns.structure import ORDINAL_PATTERNS
        
        for ordinal_pattern, number in ORDINAL_PATTERNS.items():
            pattern = re.compile(f'^({ordinal_pattern})\\.-\\s+(.+?)(?=^[A-ZÚÉÍÓÁ]+\\.-|\\Z)', 
                               re.MULTILINE | re.DOTALL | re.IGNORECASE)
            
            for match in pattern.finditer(trans_text):
                content = match.group(2).strip()
                
                transitorios.append({
                    'type': 'transitorio',
                    'id': f"trans-{number}",
                    'number': number,
                    'ordinal': match.group(1),
                    'content': content,
                    'confidence': 0.95  # High confidence for transitorios
                })
        
        # Sort by number
        transitorios.sort(key=lambda x: x['number'])
        
        return transitorios
    
    def _article_confidence(self, content: str) -> float:
        """
        Calculate confidence score for article parsing.
        
        Returns:
            Float between 0-1
        """
        score = 1.0
        
        # Reduce score for very short content
        if len(content) < 50:
            score -= 0.1
        
        # Reduce score if no punctuation (likely incomplete)
        if not re.search(r'[.;:]', content):
            score -= 0.2
        
        # Boost score for typical legal language
        if re.search(r'(en términos|conforme|de acuerdo|lo dispuesto)', content, re.IGNORECASE):
            score += 0.05
        
        return max(0.0, min(1.0, score))
    
    def _detect_gaps(self, article_numbers: List[str]) -> List[str]:
        """
        Detect gaps in article numbering.
        
        Returns:
            List of gap descriptions
        """
        gaps = []
        
        # Extract numeric parts
        nums = []
        for art_num in article_numbers:
            # Extract number part (before dash or letter)
            match = re.match(r'(\d+)', art_num)
            if match:
                nums.append(int(match.group(1)))
        
        nums.sort()
        
        # Find gaps
        for i in range(len(nums) - 1):
            if nums[i+1] - nums[i] > 1:
                gaps.append(f"Gap between Article {nums[i]} and {nums[i+1]}")
        
        return gaps
    
    def parse_structure_v2(self, text: str) -> ParseResult:
        """
        Enhanced structure parser with better accuracy.
        
        Returns:
            ParseResult with elements, confidence, warnings
        """
        result = ParseResult()
        lines = text.split('\n')
        
        # Find all structure types
        for struct_type in ['book', 'title', 'part', 'chapter', 'section']:
            elements = self._find_structure_elements(lines, struct_type)
            result.elements.extend(elements)
            
            if struct_type in ['book', 'title'] and len(elements) == 0:
                result.add_warning(f"No {struct_type.upper()} elements found - verify structure")
        
        # Find articles
        articles = self._find_articles(lines)
        result.elements.extend(articles)
        
        # Find TRANSITORIOS
        transitorios = self._find_transitorios(text)
        result.elements.extend(transitorios)
        
        if len(transitorios) == 0:
            result.add_warning("No TRANSITORIOS found - verify if law has transitory articles")
        
        # Detect gaps
        article_nums = [e['number'] for e in result.elements if e['type'] == 'article']
        gaps = self._detect_gaps(article_nums)
        for gap in gaps:
            result.add_warning(gap)
        
        # Calculate overall confidence
        if len(articles) > 0:
            avg_confidence = sum(a['confidence'] for a in articles) / len(articles)
            result.confidence = avg_confidence
        else:
            result.confidence = 0.0
            result.add_warning("No articles found!")
        
        # Store metadata
        result.metadata = {
            'total_elements': len(result.elements),
            'articles': len(articles),
            'transitorios': len(transitorios),
            'structure': {k: len([e for e in result.elements if e['type'] == k]) 
                         for k in ['book', 'title', 'chapter', 'section']}
        }
        
        return result
    
    def generate_xml(
        self,
        text: str,
        metadata: Dict[str, Any],
        output_path: Path
    ) -> Tuple[Path, ParseResult]:
        """
        Generate Akoma Ntoso XML from text.
        
        Returns:
            (output_path, parse_result)
        """
        # Parse structure
        result = self.parse_structure_v2(text)
        
        print(f"\n📊 Parsed {result.metadata['total_elements']} structural elements:")
        for struct_type, count in result.metadata['structure'].items():
            if count > 0:
                print(f"   - {struct_type.title()}s: {count}")
        print(f"   - Articles: {result.metadata['articles']}")
        print(f"   - Transitorios: {result.metadata['transitorios']}")
        print(f"\n🎯 Overall Confidence: {result.confidence:.1%}")
        
        if result.warnings:
            print(f"\n⚠️  Warnings ({len(result.warnings)}):")
            for warning in result.warnings[:5]:  # Show first 5
                print(f"   - {warning}")
        
        # Create XML structure (same as v1 for now)
        root = etree.Element('akomaNtoso', nsmap=self.nsmap)
        act = etree.SubElement(root, 'act', name='law')
        
        # Meta section
        meta = etree.SubElement(act, 'meta')
        identification = etree.SubElement(meta, 'identification', source='#antigravity')
        
        # FRBR Work
        work = etree.SubElement(identification, 'FRBRWork')
        etree.SubElement(work, 'FRBRthis', value=metadata['work_uri'])
        etree.SubElement(work, 'FRBRuri', value=metadata['work_uri'].rsplit('/', 1)[0])
        etree.SubElement(work, 'FRBRdate', date=metadata['date'], name='Generation')
        etree.SubElement(work, 'FRBRauthor', href='#congress')
        etree.SubElement(work, 'FRBRcountry', value=metadata['country'])
        
        # FRBR Expression
        expression = etree.SubElement(identification, 'FRBRExpression')
        etree.SubElement(expression, 'FRBRthis', value=metadata['expression_uri'])
        etree.SubElement(expression, 'FRBRuri', value=metadata['expression_uri'].rsplit('/', 1)[0])
        etree.SubElement(expression, 'FRBRdate', date=metadata['date'], name='Generation')
        etree.SubElement(expression, 'FRBRauthor', href='#antigravity')
        etree.SubElement(expression, 'FRBRlanguage', language=metadata['language'])
        
        # FRBR Manifestation
        manifestation = etree.SubElement(identification, 'FRBRManifestation')
        etree.SubElement(manifestation, 'FRBRthis', value=metadata['manifestation_uri'])
        etree.SubElement(manifestation, 'FRBRuri', value=metadata['manifestation_uri'].replace('.xml', '.akn'))
        etree.SubElement(manifestation, 'FRBRdate', date=str(date.today()), name='Generation')
        etree.SubElement(manifestation, 'FRBRauthor', href='#antigravity')
        
        # Body
        body = etree.SubElement(act, 'body')
        
        # Build hierarchical structure
        self._build_xml_hierarchy(body, result.elements)
        
        # Write to file
        tree = etree.ElementTree(root)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        tree.write(
            str(output_path),
            encoding='utf-8',
            xml_declaration=True,
            pretty_print=True
        )
        
        print(f"\n✅ Generated Akoma Ntoso XML: {output_path}")
        return output_path, result
    
    def _build_xml_hierarchy(self, body: etree.Element, elements: List[Dict]):
        """Build hierarchical XML structure from parsed elements."""
        current_book = None
        current_title = None
        current_chapter = None
        current_section = None
        
        for elem in elements:
            elem_type = elem['type']
            
            if elem_type == 'book':
                current_book = etree.SubElement(body, 'book', id=elem['id'])
                num = etree.SubElement(current_book, 'num')
                num.text = elem['full_text']
                current_title = None
                current_chapter = None
            
            elif elem_type == 'title':
                parent = current_book if current_book is not None else body
                current_title = etree.SubElement(parent, 'title', id=elem['id'])
                num = etree.SubElement(current_title, 'num')
                num.text = elem['full_text']
                current_chapter = None
            
            elif elem_type == 'chapter':
                if current_title is not None:
                    parent = current_title
                elif current_book is not None:
                    parent = current_book
                else:
                    parent = body
                
                current_chapter = etree.SubElement(parent, 'chapter', id=elem['id'])
                num = etree.SubElement(current_chapter, 'num')
                num.text = elem['full_text']
            
            elif elem_type in ['article', 'transitorio']:
                # Determine parent
                if current_chapter is not None:
                    parent = current_chapter
                elif current_title is not None:
                    parent = current_title
                elif current_book is not None:
                    parent = current_book
                else:
                    parent = body
                
                article_elem = etree.SubElement(parent, 'article', id=elem['id'])
                num_elem = etree.SubElement(article_elem, 'num')
                
                if elem_type == 'transitorio':
                    num_elem.text = elem['ordinal']
                else:
                    num_elem.text = f"Artículo {elem['number']}"
                
                # Content
                para = etree.SubElement(article_elem, 'paragraph', id=f"{elem['id']}-para-1")
                content = etree.SubElement(para, 'content')
                p = etree.SubElement(content, 'p')
                p.text = elem['content']
                
                # Add reform metadata as notes
                if elem.get('reforms'):
                    for reform in elem['reforms']:
                        note = etree.SubElement(article_elem, 'note', 
                                               placementBase=f"#{elem['id']}", 
                                               placement='bottom')
                        note_p = etree.SubElement(note, 'p')
                        note_p.text = reform['full_text']


def main():
    """Test v2 parser on Ley de Amparo."""
    
    # Load extracted text
    text_file = Path("data/raw/ley_amparo_extracted.txt")
    if not text_file.exists():
        print(f"❌ Text file not found: {text_file}")
        return
    
    print("📖 Loading extracted text...")
    text = text_file.read_text(encoding='utf-8')
    
    # Create v2 generator
    generator = AkomaNtosoGeneratorV2()
    
    # Metadata
    metadata = generator.create_frbr_metadata(
        law_type='ley',
        date_str='2013-04-02',
        slug='amparo',
        title='Ley de Amparo, Reglamentaria de los Artículos 103 y 107 de la Constitución Política de los Estados Unidos Mexicanos'
    )
    
    # Generate XML
    output_path = Path("data/federal/mx-fed-amparo-v2.xml")
    generator.generate_xml(text, metadata, output_path)
    
    print(f"\n🎉 V2 generation complete!")
    print(f"   Output: {output_path}")


if __name__ == "__main__":
    main()
