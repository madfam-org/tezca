"""RMF PDF line model: font style, alignment and page-furniture removal."""

from apps.parsers.rmf.lines import (
    ALIGN_BODY,
    ALIGN_HANGING,
    ALIGN_INSET,
    STYLE_BOLD,
    STYLE_BOLD_ITALIC,
    STYLE_ITALIC,
    STYLE_REGULAR,
    SourceLine,
    classify_align,
    drop_page_furniture,
    dump_jsonl,
    extract_lines,
    lines_from_raw,
    load_jsonl,
    style_from_fonts,
)


def test_style_from_font_names_of_both_editions():
    # SAT compiled edition (Noto Sans) and DOF edition (Arial).
    assert style_from_fonts(["BCDFEE+NotoSans-Bold"] * 5) == STYLE_BOLD
    assert style_from_fonts(["BCDIEE+NotoSans-Italic"] * 5) == STYLE_ITALIC
    assert style_from_fonts(["BCDGEE+NotoSans-BoldItalic"] * 5) == STYLE_BOLD_ITALIC
    assert style_from_fonts(["Arial-BoldMT"] * 3) == STYLE_BOLD
    assert style_from_fonts(["Arial-ItalicMT"] * 3) == STYLE_ITALIC
    # Majority wins: one bold word inside a regular line stays regular.
    assert style_from_fonts(["ArialMT"] * 40 + ["Arial-BoldMT"] * 4) == STYLE_REGULAR
    assert style_from_fonts([]) == STYLE_REGULAR


def test_alignment_against_measured_indents():
    # Compiled edition: body 128, rule numbers 70, fracciones 170.
    assert classify_align(70, 128) == ALIGN_HANGING
    assert classify_align(128, 128) == ALIGN_BODY
    assert classify_align(129, 128) == ALIGN_BODY
    assert classify_align(170, 128) == ALIGN_INSET
    # DOF edition: body 156, rule numbers 99.
    assert classify_align(99, 156) == ALIGN_HANGING
    assert classify_align(156, 156) == ALIGN_BODY


def test_page_furniture_is_dropped():
    page = [
        SourceLine("Domingo 28 de diciembre de 2025 DIARIO OFICIAL", page=426),
        SourceLine("deberá constar la fecha de recepción.", page=426),
        SourceLine("DIARIO OFICIAL Domingo 28 de diciembre de 2025", page=426),
        SourceLine("LISR 94, CFF 30, RMF 2.5.8.", STYLE_ITALIC, page=426),
        SourceLine(
            "NOTA: Este documento constituye una compilación de las resoluciones "
            "publicadas en el Diario Oficial de la Federación, con la finalidad",
            page=426,
        ),
        SourceLine("de dar a conocer el texto actualizado de la RMF", page=426),
        SourceLine("Página 543 de 859", page=426),
    ]
    assert [line.text for line in drop_page_furniture(page)] == [
        "deberá constar la fecha de recepción.",
        "LISR 94, CFF 30, RMF 2.5.8.",
    ]


def test_jsonl_round_trip(tmp_path):
    lines = [
        SourceLine("Pagos mensuales del RESICO", STYLE_BOLD, ALIGN_BODY, 544),
        SourceLine("3.13.7. Para los efectos…", STYLE_REGULAR, ALIGN_HANGING, 544),
    ]
    path = tmp_path / "lines.jsonl"
    dump_jsonl(lines, path)
    assert load_jsonl(path) == lines


def test_lines_from_raw_uses_one_document_wide_body_indent():
    raw = [
        (1, "Opción de pago", STYLE_BOLD, 128.0),
        (1, "3.13.7. Para los efectos del artículo 113-E", STYLE_REGULAR, 70.0),
        (1, "las personas físicas que tributen", STYLE_REGULAR, 128.0),
        (1, "en el Régimen Simplificado de Confianza", STYLE_REGULAR, 128.0),
        (1, "Página 1 de 2", STYLE_REGULAR, 267.0),
        (2, "I. Fracción", STYLE_REGULAR, 170.0),
        (2, "II. Fracción", STYLE_REGULAR, 170.0),
        (2, "cierre del párrafo", STYLE_REGULAR, 128.0),
    ]
    lines = lines_from_raw(raw)
    assert [(line.text, line.align) for line in lines] == [
        ("Opción de pago", ALIGN_BODY),
        ("3.13.7. Para los efectos del artículo 113-E", ALIGN_HANGING),
        ("las personas físicas que tributen", ALIGN_BODY),
        ("en el Régimen Simplificado de Confianza", ALIGN_BODY),
        ("I. Fracción", ALIGN_INSET),
        ("II. Fracción", ALIGN_INSET),
        ("cierre del párrafo", ALIGN_BODY),
    ]
    assert lines_from_raw([]) == []


def test_extract_lines_reopens_the_pdf_per_chunk(monkeypatch):
    """Memory stays bounded: each chunk is read from a fresh open."""
    import apps.parsers.rmf.lines as module

    calls = []
    monkeypatch.setattr(module, "page_count", lambda _path: 95)

    def fake_raw(_path, first, last):
        calls.append((first, last))
        return [(first, f"página {first}", STYLE_REGULAR, 128.0)]

    monkeypatch.setattr(module, "extract_raw", fake_raw)
    lines = extract_lines("rmf.pdf", chunk_pages=40)
    assert calls == [(1, 40), (41, 80), (81, 120)]
    assert [line.page for line in lines] == [1, 41, 81]
