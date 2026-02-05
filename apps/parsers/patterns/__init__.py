"""Pattern library package for Mexican legal document parsing."""

from .articles import compile_article_patterns, is_derogated
from .metadata import (
    extract_cross_references,
    extract_effective_date,
    extract_reforms,
    parse_dof_date,
)
from .structure import (
    compile_fraction_patterns,
    compile_structure_patterns,
    compile_transitorios_patterns,
    roman_to_int,
)

__all__ = [
    # Structure
    "compile_article_patterns",
    "compile_structure_patterns",
    "compile_transitorios_patterns",
    "compile_fraction_patterns",
    "roman_to_int",
    # Metadata
    "extract_reforms",
    "extract_effective_date",
    "extract_cross_references",
    "is_derogated",
    "parse_dof_date",
]
