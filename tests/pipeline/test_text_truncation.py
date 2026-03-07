"""
Tests for text truncation behavior during ES indexing.

The index_laws command applies text[:50000] on line 324 for raw text fallback,
but AKN-extracted articles do NOT have this cap. These tests verify that
boundary and document the asymmetry.
"""

from datetime import date
from unittest.mock import MagicMock, patch

import pytest

from apps.api.management.commands.index_laws import Command
from apps.api.models import Law, LawVersion

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

AKN_NS = "http://docs.oasis-open.org/legaldocml/ns/akn/3.0"
RAW_TEXT_TRUNCATION_LIMIT = 50_000


def _make_command() -> Command:
    """Instantiate the management Command with silenced I/O."""
    from django.core.management.color import no_style

    cmd = Command()
    cmd.style = no_style()
    cmd.stdout = MagicMock()
    cmd.stderr = MagicMock()
    return cmd


def _build_akn_xml(article_text: str) -> str:
    """Return minimal AKN XML wrapping *article_text* in a single article."""
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<akomaNtoso xmlns="{AKN_NS}">\n'
        '  <act name="test">\n'
        "    <body>\n"
        '      <article eId="art_1">\n'
        "        <num>Articulo 1.</num>\n"
        "        <content>\n"
        f"          <p>{article_text}</p>\n"
        "        </content>\n"
        "      </article>\n"
        "    </body>\n"
        "  </act>\n"
        "</akomaNtoso>"
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
@pytest.mark.spotcheck
class TestTextTruncation:
    """Verify truncation rules for raw-text vs AKN article indexing."""

    # -- 1. Raw text is capped at 50 000 chars ---------------------------------

    def test_raw_text_truncated_at_50k(self):
        """_index_raw_text must truncate the text field to 50 000 chars."""
        law = Law.objects.create(
            official_id="test-trunc-50k",
            name="Ley de Truncamiento",
            tier="state",
        )
        version = LawVersion.objects.create(
            law=law,
            publication_date=date(2023, 1, 1),
        )

        oversized_text = "A" * 60_000  # 10 000 chars over limit

        cmd = _make_command()
        captured_actions: list[dict] = []

        def _capture_bulk(_es, actions):
            captured_actions.extend(actions)

        with patch(
            "apps.api.management.commands.index_laws.helpers.bulk",
            side_effect=_capture_bulk,
        ):
            cmd._index_raw_text(law, version, oversized_text, es=MagicMock())

        # The first bulk call is the article doc; the second is the law-level doc
        article_doc = captured_actions[0]
        indexed_text = article_doc["_source"]["text"]

        assert len(indexed_text) == RAW_TEXT_TRUNCATION_LIMIT
        assert indexed_text == "A" * RAW_TEXT_TRUNCATION_LIMIT

    # -- 2. AKN articles are NOT truncated -------------------------------------

    def test_akn_articles_not_truncated(self):
        """extract_articles_from_xml must preserve article text without any cap."""
        long_body = "B" * 60_000  # well over the 50 000 raw-text limit
        xml = _build_akn_xml(long_body)

        cmd = _make_command()
        articles = cmd.extract_articles_from_xml(xml, "test-akn-no-trunc")

        assert len(articles) == 1
        assert len(articles[0]["text"]) == 60_000, (
            "AKN article text must NOT be truncated -- "
            "only the raw-text fallback path applies the 50 000-char cap"
        )

    # -- 3. Python slicing is codepoint-safe for multi-byte chars ---------------

    def test_truncation_preserves_utf8(self):
        """text[:50000] operates on Unicode codepoints, not bytes.

        Placing a multi-byte character (e.g. 'a' U+00E1, 2 bytes in UTF-8)
        right at the boundary must NOT corrupt the string.  Python 3 strings
        are sequences of codepoints, so slicing is always safe regardless of
        the underlying byte width.
        """
        # Build a string where position 49 999 is a multi-byte char
        prefix = "X" * 49_999
        text = prefix + "a" * 20_000  # total 69 999 chars

        truncated = text[:RAW_TEXT_TRUNCATION_LIMIT]

        assert len(truncated) == RAW_TEXT_TRUNCATION_LIMIT
        assert truncated[-1] == "a"
        # Round-trip through UTF-8 encoding must succeed without errors
        encoded = truncated.encode("utf-8")
        decoded = encoded.decode("utf-8")
        assert decoded == truncated

    # -- 4. Raw-text fallback sets article field to "full_text" -----------------

    def test_full_text_articles_are_raw_fallback(self):
        """_index_raw_text must set the article field to 'full_text'."""
        law = Law.objects.create(
            official_id="test-fulltext-marker",
            name="Ley Marcador",
            tier="federal",
        )
        version = LawVersion.objects.create(
            law=law,
            publication_date=date(2023, 6, 15),
        )

        cmd = _make_command()
        captured_actions: list[dict] = []

        def _capture_bulk(_es, actions):
            captured_actions.extend(actions)

        with patch(
            "apps.api.management.commands.index_laws.helpers.bulk",
            side_effect=_capture_bulk,
        ):
            cmd._index_raw_text(law, version, "contenido de ejemplo", es=MagicMock())

        article_doc = captured_actions[0]
        assert article_doc["_source"]["article"] == "full_text"
        assert article_doc["_id"] == "test-fulltext-marker-full_text"
        assert "raw_text" in article_doc["_source"]["tags"]
