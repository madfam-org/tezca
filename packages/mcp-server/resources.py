"""MCP resources — static reference data for Mexican legal taxonomy."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

TAXONOMY = """\
# Mexican Legal Taxonomy

## Tiers (jurisdiction levels)
- **federal**: National laws from the federal Congress and executive
- **state**: Laws from 32 state legislatures and governors
- **municipal**: Regulations from 2,468 municipalities

## Law Types
- **legislative**: Laws, codes, and organic statutes from legislative bodies
- **non_legislative**: Reglamentos, NOMs, treaties, decrees from executive/agencies

## Categories (legal domains)
- civil: Private relationships, property, contracts, family
- penal: Criminal law, sanctions, criminal procedure
- fiscal: Tax law, revenue codes, customs
- mercantil: Commercial law, corporations, banking
- laboral: Employment, social security, labor rights
- administrativo: Government organization, public administration
- constitucional: Constitutional law, fundamental rights, amparo

## Special Sources
- NOMs (Normas Oficiales Mexicanas): Technical standards
- Treaties: International agreements ratified by Mexico
- Reglamentos: Executive regulations implementing laws
- SCJN Jurisprudencia: Binding judicial precedent
- Tesis Aisladas: Non-binding judicial interpretations

## Status Values
- vigente: Currently in force
- abrogada/abrogado: Repealed, no longer in effect
"""

DOMAINS = """\
# Domain-to-Category Mapping

Domains are convenience groupings that map to one or more legal categories.

## Generic domains (backward-compatible)

| Domain | Categories |
|--------|-----------|
| finance | fiscal, mercantil |
| criminal | penal |
| labor | laboral |
| civil | civil |
| administrative | administrativo |
| constitutional | constitucional |

## SCIAN 2023-aligned sectors (Secretaría de Economía / INEGI)

| Domain | SCIAN Codes | Categories |
|--------|-------------|-----------|
| manufacturing | 31-33 (Industrias manufactureras) | laboral, administrativo, mercantil |
| commerce | 43+46 (Comercio al por mayor/menor) | mercantil, fiscal, administrativo |
| foreign_trade | Comercio exterior | fiscal, mercantil, administrativo |
| financial_services | 52 (Servicios financieros) | fiscal, mercantil |
| professional_services | 54 (Servicios profesionales) | civil, administrativo, laboral |

Use domain parameters as shortcuts when you want to search across related categories.
For example, `domain="manufacturing"` searches laboral, administrativo, and mercantil law.
"""

STATES = """\
# Mexican States (32)

Aguascalientes, Baja California, Baja California Sur, Campeche, Chiapas,
Chihuahua, Ciudad de México, Coahuila, Colima, Durango, Estado de México,
Guanajuato, Guerrero, Hidalgo, Jalisco, Michoacán, Morelos, Nayarit,
Nuevo León, Oaxaca, Puebla, Querétaro, Quintana Roo, San Luis Potosí,
Sinaloa, Sonora, Tabasco, Tamaulipas, Tlaxcala, Veracruz, Yucatán, Zacatecas.

Use these exact names (with accents) when filtering by state in search_laws
or list_laws. State names are case-insensitive.
"""


def register_resources(mcp: FastMCP) -> None:
    @mcp.resource("tezca://taxonomy")
    def taxonomy() -> str:
        """Mexican legal hierarchy: tiers, law types, categories, special sources, status values."""
        return TAXONOMY

    @mcp.resource("tezca://domains")
    def domains() -> str:
        """Domain-to-category mapping for convenience search groupings."""
        return DOMAINS

    @mcp.resource("tezca://states")
    def states() -> str:
        """All 32 Mexican states with canonical names for filtering."""
        return STATES
