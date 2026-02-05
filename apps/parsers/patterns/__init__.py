"""Pattern library package for Mexican legal document parsing."""

from .articles import (
    compile_article_patterns,
    is_derogated,
)

from .structure import (
    compile_structure_patterns,
    compile_transitorios_patterns,
    compile_fraction_patterns,
    roman_to_int,
)

from .metadata import (
    extract_reforms,
    extract_effective_date,
    extract_cross_references,
    parse_dof_date,
)

__all__ = [
    # Structure
    'compile_article_patterns',
    'compile_structure_patterns',
    'compile_transitorios_patterns',
    'compile_fraction_patterns',
    'roman_to_int',
    # Metadata
    'extract_reforms',
    'extract_effective_date',
    'extract_cross_references',
    'is_derogated',
    'parse_dof_date',
]
