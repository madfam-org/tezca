"""Cámara de Diputados page furniture never reaches article text.

Fixtures are short hand-written excerpts modelled on the LFPDPPP text served
in production, where the footer of one page and the header of the next sat in
the middle of the article that straddled the page break::

    …utilización comercial.
    1 de 24
    LEY FEDERAL DE … PARTICULARES CÁMARA DE DIPUTADOS DEL H. CONGRESO DE LA
    UNIÓN Última Reforma DOF 14-11-2025
    Secretaría General Secretaría de Servicios Parlamentarios
"""

from datetime import date

from apps.parsers.diputados_pdf import (
    extract_last_reform_date,
    find_page_totals,
    join_pages,
    strip_furniture,
    strip_page_furniture,
    strip_trailing_decree_stubs,
    trim_decree_tail,
)

TITLE = "LEY FEDERAL DE PROTECCIÓN DE DATOS PERSONALES EN POSESIÓN DE LOS PARTICULARES"
CHAMBER = "CÁMARA DE DIPUTADOS DEL H. CONGRESO DE LA UNIÓN"
REFORM = "Última Reforma DOF 14-11-2025"

# The header as pdfplumber extracts it from one page: four lines.
PAGE_HEADER = (
    f"{TITLE}\n{CHAMBER} {REFORM}\nSecretaría General\n"
    "Secretaría de Servicios Parlamentarios\n"
)
# The header as it sits inside article text read back from a stored XML.
EMBEDDED_HEADER = (
    f"{TITLE} {CHAMBER} {REFORM}\n"
    "Secretaría General Secretaría de Servicios Parlamentarios"
)


def _page(body, number, total=24):
    return f"{PAGE_HEADER}{body}\n{number} de {total}"


# ── extraction time: one page at a time ──────────────────────────────────────


def test_page_header_and_footer_are_removed():
    page = _page("Artículo 1.- La presente Ley es de orden público.", 1)
    assert (
        strip_page_furniture(page, page_total=24)
        == "Artículo 1.- La presente Ley es de orden público."
    )


def test_pages_join_back_into_one_sentence_across_the_break():
    pages = [
        _page("Décimo.- Los procedimientos iniciados con anterioridad, se", 19),
        _page("sustanciarán conforme a las disposiciones vigentes.", 20),
    ]
    assert join_pages(pages) == (
        "Décimo.- Los procedimientos iniciados con anterioridad, se\n"
        "sustanciarán conforme a las disposiciones vigentes."
    )


def test_article_heading_on_a_new_page_stays_on_its_own_line():
    pages = [
        _page("Artículo 3.- Texto del artículo tres.", 1, 2),
        _page("Artículo 4.- Texto del artículo cuatro.", 2, 2),
    ]
    assert join_pages(pages).split("\n") == [
        "Artículo 3.- Texto del artículo tres.",
        "Artículo 4.- Texto del artículo cuatro.",
    ]


def test_date_wording_that_looks_like_a_counter_is_kept():
    body = (
        "Artículo 5.- El aviso se publicará el 21 de enero de 2025, a más tardar\n"
        "1 de 24 horas después de recibido, en los términos del artículo\n"
        "24 de esta Ley."
    )
    assert strip_page_furniture(_page(body, 3), page_total=24) == body


def test_last_line_that_is_not_this_pages_counter_is_kept():
    # "3 de 5" closes the text of a page in a 24-page document.
    page = f"{PAGE_HEADER}Se integrará por los miembros siguientes:\n3 de 5"
    cleaned = strip_page_furniture(page, page_total=24)
    assert cleaned.endswith("3 de 5")


def test_footers_are_kept_when_pages_do_not_share_a_total():
    pages = ["Artículo 1.- Texto.\n1 de 3", "Artículo 2.- Otro texto.", "Fin."]
    assert join_pages(pages) == "\n".join(pages)


def test_missing_pages_do_not_stop_footer_removal():
    # Page 2 had no extractable text, so only pages 1 and 3 of 3 are present.
    pages = [_page("Artículo 1.- Texto.", 1, 3), None, _page("Artículo 2.- Fin.", 3, 3)]
    assert join_pages(pages) == "Artículo 1.- Texto.\nArtículo 2.- Fin."


def test_page_of_another_source_is_untouched():
    page = "PERIÓDICO OFICIAL\nSecretaría General de Gobierno\nArtículo 1.- Texto."
    assert strip_page_furniture(page, page_total=3) == page


# ── index time: furniture already embedded in the text ───────────────────────


def test_embedded_furniture_at_the_end_of_an_article_is_removed():
    text = (
        "II. Las personas que lleven a cabo la recolección de datos personales, "
        "sin fines de divulgación o utilización comercial.\n"
        f"1 de 24\n{EMBEDDED_HEADER}"
    )
    assert strip_furniture(text).endswith("utilización comercial.")
    assert "Parlamentarios" not in strip_furniture(text)


def test_embedded_furniture_mid_sentence_joins_the_sentence_back():
    text = (
        "Los procedimientos iniciados con anterioridad, en materia de datos "
        "personales o cualquier otra distinta a la mencionada, se\n"
        f"19 de 24\n{EMBEDDED_HEADER} sustanciarán conforme a las disposiciones "
        "vigentes al momento de su inicio."
    )
    assert strip_furniture(text) == (
        "Los procedimientos iniciados con anterioridad, en materia de datos "
        "personales o cualquier otra distinta a la mencionada, se sustanciarán "
        "conforme a las disposiciones vigentes al momento de su inicio."
    )


def test_embedded_furniture_between_fractions_keeps_the_line_break():
    text = (
        "XI. Ley: Ley Federal de Protección de Datos Personales;\n"
        f"2 de 24\n{EMBEDDED_HEADER} XII. Persona encargada: Persona física."
    )
    assert strip_furniture(text) == (
        "XI. Ley: Ley Federal de Protección de Datos Personales;\n"
        "XII. Persona encargada: Persona física."
    )


def test_last_page_counter_needs_a_known_page_total():
    closing = "Secretaria de Gobernación.- Rúbrica.\n24 de 24"
    # Alone, "24 de 24" is not provably a page counter.
    assert strip_furniture(closing) == closing
    # The total seen above a header elsewhere in the same law proves it.
    totals = find_page_totals([f"Texto.\n1 de 24\n{EMBEDDED_HEADER}"])
    assert totals == {24}
    assert strip_furniture(closing, totals) == "Secretaria de Gobernación.- Rúbrica."


def test_real_text_resembling_furniture_is_kept():
    text = (
        "El dictamen se publicará el 21 de enero de 2025.\n"
        "Corresponde a la Cámara de Diputados del H. Congreso de la Unión "
        "aprobar el presupuesto.\n"
        "3 de 5"
    )
    assert strip_furniture(text, {24}) == text


def test_strip_furniture_is_idempotent():
    text = f"Primero.- Entrará en vigor.\n17 de 24\n{EMBEDDED_HEADER}"
    once = strip_furniture(text)
    assert once == "Primero.- Entrará en vigor."
    assert strip_furniture(once) == once


# ── «Última Reforma DOF» ─────────────────────────────────────────────────────


def test_last_reform_date_is_read_from_the_header():
    assert extract_last_reform_date(_page("Artículo 1.- Texto.", 1)) == date(
        2025, 11, 14
    )


def test_last_reform_variants():
    assert extract_last_reform_date(
        "Últimas reformas publicadas DOF 20-05-2021\nTexto"
    ) == date(2021, 5, 20)
    assert extract_last_reform_date("ÚLTIMA REFORMA PUBLICADA EN EL DOF 1-4-2024") == (
        date(2024, 4, 1)
    )


def test_no_reform_stated_means_no_date():
    assert extract_last_reform_date(f"{CHAMBER} Nueva Ley DOF 20-03-2025") is None
    assert extract_last_reform_date("Última Reforma DOF 31-02-2025") is None
    assert extract_last_reform_date("") is None


# ── decree closing after the last transitorio ────────────────────────────────

LAST_TRANSITORIO = (
    "El Poder Judicial de la Federación deberá habilitar juzgados de Distrito.\n"
    "Para efectos de lo previsto en este transitorio, se suspenden los plazos."
)


def test_signature_block_is_cut_off_the_last_transitorio():
    text = (
        f"{LAST_TRANSITORIO}\n"
        "Ciudad de México, a 20 de marzo de 2025.- Sen. Imelda Castro Castro, "
        'Vicepresidenta.- Dip. Sergio Carlos Gutiérrez Luna, Presidente.- Rúbricas."\n'
        "En cumplimiento de lo dispuesto por la fracción I del Artículo 89 de la "
        "Constitución Política de los Estados Unidos Mexicanos, expido el presente "
        "Decreto.\n"
        "ARTÍCULOS TRANSITORIOS DE DECRETOS DE REFORMA DECRETO por el que se "
        "reforman diversas disposiciones.\n"
        "Publicado en el Diario Oficial de la Federación el 14 de noviembre de 2025\n"
        "Artículo Trigésimo Octavo.- Se reforma el artículo 4, para quedar como "
        "sigue:\n……..\nTransitorios"
    )
    assert trim_decree_tail(text) == LAST_TRANSITORIO


def test_old_style_signature_block_is_cut():
    text = (
        "Segundo.- Se derogan las disposiciones que se opongan.\n"
        "México, D.F., a 27 de abril de 2010.- Dip. Francisco Javier Ramírez "
        "Acuña, Presidente.- Rúbricas."
    )
    assert trim_decree_tail(text) == (
        "Segundo.- Se derogan las disposiciones que se opongan."
    )


def test_next_decree_title_is_cut():
    text = (
        "Se abroga la ley anterior.\n"
        "DECRETO por el que se reforma el artículo 2 de la Ley."
    )
    assert trim_decree_tail(text) == "Se abroga la ley anterior."


def test_wrapped_reference_to_a_decree_is_kept():
    text = (
        "Las referencias se entenderán hechas a lo previsto en el\n"
        "DECRETO por el que se expide la Ley, publicado el 20 de marzo de 2025."
    )
    assert trim_decree_tail(text) == text


def test_place_and_date_inside_a_sentence_are_kept():
    text = (
        "El Comité sesionará en la sede del Instituto.\n"
        "Las sesiones se celebrarán en la Ciudad de México, a más tardar el 30 "
        "de junio de 2025."
    )
    assert trim_decree_tail(text) == text


def test_tail_marker_on_the_first_line_never_empties_a_provision():
    text = "En cumplimiento de lo dispuesto por la fracción I del Artículo 89."
    assert trim_decree_tail(text) == text


# ── stubs after the last body article ────────────────────────────────────────


def test_decree_stub_and_transitorios_heading_are_dropped():
    text = (
        "Tratándose de datos personales sensibles, las penas se duplicarán.\n"
        "Artículo Cuarto.- ……..\n"
        "Transitorios"
    )
    assert strip_trailing_decree_stubs(text) == (
        "Tratándose de datos personales sensibles, las penas se duplicarán."
    )


def test_decree_article_with_text_is_kept():
    text = (
        "Artículo 5.- Texto.\n" "Artículo Segundo.- Se reforma el artículo 9 de la Ley."
    )
    assert strip_trailing_decree_stubs(text) == text
