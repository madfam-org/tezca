"""Multiple transitorios blocks (one per decree) are all captured (#222).

A consolidated law carries the transitorios of its own decree followed by one
block per reform decree, each restarting at "Primero". The parser used to keep
only the first occurrence of each number, silently dropping every reform
block (LFPDPPP lost the DOF 14-11-2025 reform's transitorios this way).
"""

from apps.parsers.akn_generator_v2 import AkomaNtosoGeneratorV2

BODY = "Artículo 1.- Objeto de la ley.\nArtículo 2.- Definiciones.\n"


def _transitorios(text):
    return AkomaNtosoGeneratorV2()._find_transitorios(text)


def test_reform_block_after_second_header_gets_distinct_ids():
    text = (
        BODY + "TRANSITORIOS\n"
        "PRIMERO.- Entra en vigor al día siguiente.\n"
        "SEGUNDO.- Se abroga la ley anterior.\n"
        "DECRETO por el que se reforma el artículo 2.\n"
        "Transitorios\n"
        "Primero. El decreto de reforma entra en vigor.\n"
        "Segundo. Se derogan las disposiciones que se opongan.\n"
    )
    trans = _transitorios(text)
    assert [t["id"] for t in trans] == [
        "trans-1",
        "trans-2",
        "trans-r2-1",
        "trans-r2-2",
    ]
    assert [t["block"] for t in trans] == [1, 1, 2, 2]
    by_id = {t["id"]: t for t in trans}
    assert by_id["trans-r2-1"]["content"].startswith("El decreto de reforma")
    # The second header closes block 1's last provision.
    assert "Transitorios" not in by_id["trans-2"]["content"]
    assert "reforma entra en vigor" not in by_id["trans-2"]["content"]


def test_numbering_restart_without_header_opens_new_block():
    text = BODY + "TRANSITORIOS\nPRIMERO.- A.\nSEGUNDO.- B.\nPRIMERO.- C.\n"
    trans = _transitorios(text)
    assert [t["id"] for t in trans] == ["trans-1", "trans-2", "trans-r2-1"]
    assert trans[2]["content"] == "C."


def test_repeated_non_first_number_in_block_keeps_first():
    text = BODY + "TRANSITORIOS\nPRIMERO.- A.\nSEGUNDO.- B.\nSEGUNDO.- B bis.\n"
    trans = _transitorios(text)
    assert [t["id"] for t in trans] == ["trans-1", "trans-2"]


def test_earliest_header_opens_section_regardless_of_pattern_order():
    """«ARTÍCULOS TRANSITORIOS» is the first header pattern; when it appears
    only AFTER a plain "TRANSITORIOS", the earlier block must not be skipped."""
    text = (
        BODY + "TRANSITORIOS\n"
        "PRIMERO.- Primer decreto.\n"
        "ARTÍCULOS TRANSITORIOS\n"
        "PRIMERO.- Segundo decreto.\n"
    )
    trans = _transitorios(text)
    assert [t["id"] for t in trans] == ["trans-1", "trans-r2-1"]
    assert trans[0]["content"] == "Primer decreto."


def test_single_block_ids_unchanged():
    text = BODY + "TRANSITORIOS\nPRIMERO.- A.\nDÉCIMO TERCERO.- B.\n"
    trans = _transitorios(text)
    assert [t["id"] for t in trans] == ["trans-1", "trans-13"]
    assert all(t["block"] == 1 for t in trans)
