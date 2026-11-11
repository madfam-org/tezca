"""Law names never carry Diputados-catalog debris.

The LeyesBiblio index prints the title, its DOF publication date and a status
marker in one table cell. Production stored the whole cell as ``Law.name``::

    LEY Federal de … Particulares \t\t\t\t \t\t\t\tDOF 20/03/2025 \t\t\t\t \t\t\t\tNueva reforma

Fixtures are the cell shapes found in ``data/law_registry.json``.
"""

import pytest

from apps.scraper.utils.law_name import (
    build_short_name,
    has_catalog_debris,
    normalize_law_name,
    normalize_short_name,
    parse_catalog_title,
)

TABS = " \t\t\t\t \t\t\t\t"
LFPDPPP_TITLE = (
    "LEY Federal de Protección de Datos Personales en Posesión de los Particulares"
)
LFPDPPP_CELL = f"{LFPDPPP_TITLE}{TABS}DOF 20/03/2025{TABS}Nueva reforma"


def test_lfpdppp_cell_splits_into_name_date_and_marker():
    parsed = parse_catalog_title(LFPDPPP_CELL)
    assert parsed.name == LFPDPPP_TITLE
    assert parsed.publication_date == "2025-03-20"
    assert parsed.notes == ["Nueva reforma"]


@pytest.mark.parametrize(
    "cell, name, date",
    [
        (f"LEY Aduanera{TABS}DOF 15/12/1995", "LEY Aduanera", "1995-12-15"),
        (
            f"LEY de Concursos Mercantiles{TABS}DOF 12/05/2000{TABS}En{TABS}actualización",
            "LEY de Concursos Mercantiles",
            "2000-05-12",
        ),
        (
            f"LEY General de Aguas{TABS}DOF 11/12/2025{TABS}Nueva Ley",
            "LEY General de Aguas",
            "2025-12-11",
        ),
        (
            "LEY de Ingresos de la Federación para el Ejercicio Fiscal de 2026"
            f"{TABS}DOF 07/11/2025{TABS}Nueva Ley en{TABS}vigor a partir del 01/01/2026",
            "LEY de Ingresos de la Federación para el Ejercicio Fiscal de 2026",
            "2025-11-07",
        ),
        (
            f"LEY sobre Elaboración y Venta de Café Tostado{TABS}DOF 25/05/1972"
            f"{TABS}Ley abrogada a{TABS}partir del 17/06/2026",
            "LEY sobre Elaboración y Venta de Café Tostado",
            "1972-05-25",
        ),
        (
            f"LEY de Seguridad Interior{TABS}DOF 21/12/2017"
            f"{TABS}(Declaratoria de Invalidez de la Ley DOF 30/05/2019)",
            "LEY de Seguridad Interior",
            "2017-12-21",
        ),
    ],
)
def test_date_and_status_markers_are_stripped(cell, name, date):
    parsed = parse_catalog_title(cell)
    assert parsed.name == name
    assert parsed.publication_date == date


def test_former_name_note_is_kept_out_of_the_name():
    parsed = parse_catalog_title(
        f'LEY de Fondos de Inversión{TABS}(Antes "Ley de Sociedades de Inversión")'
        f"{TABS}DOF 04/06/2001{TABS}Nueva reforma"
    )
    assert parsed.name == "LEY de Fondos de Inversión"
    assert parsed.notes == ['(Antes "Ley de Sociedades de Inversión")', "Nueva reforma"]


def test_title_wrapped_over_several_lines_is_joined():
    parsed = parse_catalog_title(
        "LEY General para Prevenir, Investigar y Sancionar la Tortura y Otros"
        f"{TABS}Tratos o Penas Crueles, Inhumanos o Degradantes{TABS}DOF 26/06/2017"
    )
    assert parsed.name == (
        "LEY General para Prevenir, Investigar y Sancionar la Tortura y Otros "
        "Tratos o Penas Crueles, Inhumanos o Degradantes"
    )


def test_parenthesis_that_belongs_to_the_title_is_kept():
    parsed = parse_catalog_title(
        f"IMPUESTO sobre Servicios{TABS}(LEY que establece, reforma"
        f"{TABS}y adiciona las disposiciones relativas a diversos impuestos)"
        f"{TABS}DOF 31/12/1968"
    )
    assert parsed.name.endswith("diversos impuestos)")
    assert parsed.publication_date == "1968-12-31"


def test_date_range_is_stripped_without_inventing_a_date():
    parsed = parse_catalog_title(
        f"ORDENANZA General de la Armada{TABS}DOF 01 al 08/01/1912"
    )
    assert parsed.name == "ORDENANZA General de la Armada"
    assert parsed.publication_date is None


def test_normalising_is_idempotent():
    once = normalize_law_name(LFPDPPP_CELL)
    assert normalize_law_name(once) == once
    assert has_catalog_debris(LFPDPPP_CELL)
    assert not has_catalog_debris(once)


@pytest.mark.parametrize(
    "name",
    [
        "Reglamento de la Ley Federal de Protección de Datos Personales "
        "en Posesión de los Particulares",
        # Mentions a DOF date in running text: not a catalog cell.
        "Acuerdo publicado en el DOF 01/01/2020 en materia de salud",
        # Ends in words that are also status markers, with no cell layout.
        "Reglamento de la Nueva Ley",
        "Ley Abrogada",
        "",
    ],
)
def test_clean_names_are_left_alone(name):
    assert normalize_law_name(name) == name


def test_marker_without_a_date_needs_the_cell_layout():
    assert normalize_law_name(f"LEY de Ejemplo{TABS}Nueva reforma") == "LEY de Ejemplo"


def test_short_name_cut_from_the_raw_cell_is_rebuilt():
    raw = f"LEY Aduanera{TABS}DOF 15/12/1995{TABS}Nueva reforma"
    assert normalize_short_name(build_short_name(raw), raw) == "LEY Aduanera"
    assert normalize_short_name(None, raw) == "LEY Aduanera"


def test_curated_short_name_is_kept():
    assert normalize_short_name("LFPDPPP", LFPDPPP_CELL) == "LFPDPPP"
