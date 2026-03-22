"""Shared constants for the API app."""

# Domain-to-category mapping for data consumers.
# Generic domains (backward-compatible):
#   finance, criminal, labor, civil, administrative, constitutional
# SCIAN 2023-aligned sectors (Secretaría de Economía / INEGI):
#   manufacturing (31-33), commerce (43+46), foreign_trade,
#   financial_services (52), professional_services (54)
DOMAIN_MAP = {
    # Generic domains — values must match actual Law.category in the DB.
    # Production categories: ley, acuerdo, reglamento, decreto, codigo,
    # constitucion, ley_organica, manual, lineamientos, circular, otros,
    # plus English branch names: fiscal, labor, commercial, environmental,
    # administrative, criminal, civil, constitutional, etc.
    "finance": ["fiscal", "financial", "commercial"],
    "criminal": ["criminal"],
    "labor": ["labor"],
    "civil": ["civil"],
    "administrative": ["administrative"],
    "constitutional": ["constitutional", "constitucion"],
    # SCIAN 2023-aligned
    "manufacturing": ["labor", "administrative", "commercial"],
    "commerce": ["commercial", "fiscal", "administrative"],
    "foreign_trade": ["fiscal", "commercial", "administrative"],
    "financial_services": ["fiscal", "financial", "commercial"],
    "professional_services": ["civil", "administrative", "labor"],
    # Consumer-facing composite domains
    "training": ["labor", "administrative"],
    "customs": ["fiscal", "commercial", "administrative"],
    "safety": ["labor", "administrative", "environmental"],
}

KNOWN_STATES = {
    "aguascalientes": "Aguascalientes",
    "baja_california_sur": "Baja California Sur",
    "baja_california": "Baja California",
    "campeche": "Campeche",
    "chiapas": "Chiapas",
    "chihuahua": "Chihuahua",
    "ciudad_de_mexico": "Ciudad de México",
    "coahuila": "Coahuila",
    "colima": "Colima",
    "durango": "Durango",
    "estado_de_mexico": "Estado de México",
    "guanajuato": "Guanajuato",
    "guerrero": "Guerrero",
    "hidalgo": "Hidalgo",
    "jalisco": "Jalisco",
    "michoacan": "Michoacán",
    "morelos": "Morelos",
    "nayarit": "Nayarit",
    "nuevo_leon": "Nuevo León",
    "oaxaca": "Oaxaca",
    "puebla": "Puebla",
    "queretaro": "Querétaro",
    "quintana_roo": "Quintana Roo",
    "san_luis_potosi": "San Luis Potosí",
    "sinaloa": "Sinaloa",
    "sonora": "Sonora",
    "tabasco": "Tabasco",
    "tamaulipas": "Tamaulipas",
    "tlaxcala": "Tlaxcala",
    "veracruz": "Veracruz",
    "yucatan": "Yucatán",
    "zacatecas": "Zacatecas",
}
