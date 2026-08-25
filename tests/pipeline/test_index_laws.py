import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# ── Temporarily mock Django/ES/models to import the management command,
#    then restore sys.modules so other test files see the real Django. ────
_saved_modules = {}
_modules_to_mock = [
    "django",
    "django.core",
    "django.core.management",
    "django.core.management.base",
    "elasticsearch",
    "apps.api.models",
]
for _m in _modules_to_mock:
    if _m in sys.modules:
        _saved_modules[_m] = sys.modules[_m]


class _FakeBaseCommand:
    """Minimal BaseCommand stub so the management command can be imported."""

    def add_arguments(self, parser):
        pass

    def handle(self, *args, **kwargs):
        pass


_mock_django = MagicMock()
_mock_django.core.management.base.BaseCommand = _FakeBaseCommand
sys.modules["django"] = _mock_django
sys.modules["django.core"] = _mock_django.core
sys.modules["django.core.management"] = _mock_django.core.management
sys.modules["django.core.management.base"] = _mock_django.core.management.base

sys.modules["elasticsearch"] = MagicMock()

_mock_models = MagicMock()
sys.modules["apps.api.models"] = _mock_models

# Import the command (requires mocked modules above)
from apps.api.management.commands.index_laws import Command  # noqa: E402

# Restore original sys.modules immediately to prevent leaking mocks
# to other test files (e.g., those using @pytest.mark.django_db).
for _m in _modules_to_mock:
    if _m in _saved_modules:
        sys.modules[_m] = _saved_modules[_m]
    elif _m in sys.modules:
        del sys.modules[_m]

# Keep a reference to the mock Law that the Command module uses internally.
_MockLaw = _mock_models.Law

MINIMAL_V2_XML = """<?xml version="1.0" encoding="UTF-8"?>
<akomaNtoso xmlns="http://docs.oasis-open.org/legaldocml/ns/akn/3.0">
    <act name="law">
        <body>
            <book eId="book_1">
                <num>LIBRO PRIMERO</num>
                <heading>Disposiciones Generales</heading>
                <title eId="title_1">
                    <num>TÍTULO I</num>
                    <heading>Del Ámbito de Validez</heading>
                    <chapter eId="chapter_1">
                        <num>CAPÍTULO I</num>
                        <heading>Objeto de la Ley</heading>
                        <article eId="art_1">
                            <num>Artículo 1.</num>
                            <heading>Objeto</heading>
                            <content>
                                <p>La presente ley es de orden público.</p>
                            </content>
                        </article>
                    </chapter>
                </title>
            </book>
            <article eId="art_2">
                <num>Artículo 2.</num>
                <content>
                    <p>Artículo suelto fuera de jerarquía.</p>
                </content>
            </article>
        </body>
    </act>
</akomaNtoso>
"""


# AKN XML reproducing the LFPDPPP transitorio-collision (Defect 1).
# Mirrors what apps/parsers/akn_generator_v2 emits: a substantive
# <article id="art-8"><num>Artículo 8.</num> AND an "Octavo" transitorio
# serialised as <article id="trans-8"><num>Octavo</num> inside a TRANSITORIOS
# section. Both previously derived article_id "8" and collided on the ES
# _id "{law}-8"; last-write-wins let the transitorio overwrite the real
# article. Post-fix they must be two distinct docs.
TRANSITORIO_COLLISION_XML = """<?xml version="1.0" encoding="UTF-8"?>
<akomaNtoso xmlns="http://docs.oasis-open.org/legaldocml/ns/akn/3.0">
    <act name="law">
        <body>
            <chapter id="capitulo-1">
                <num>CAPÍTULO I</num>
                <article id="art-8">
                    <num>Artículo 8.</num>
                    <content>
                        <p>Artículo 8. El consentimiento del titular es requisito para el tratamiento de datos personales.</p>
                    </content>
                </article>
            </chapter>
            <chapter id="capitulo-trans">
                <num>TRANSITORIOS</num>
                <article id="trans-1">
                    <num>Primero</num>
                    <content>
                        <p>El presente Decreto entrará en vigor al día siguiente de su publicación.</p>
                    </content>
                </article>
                <article id="trans-8">
                    <num>Octavo</num>
                    <content>
                        <p>El Instituto Nacional de Transparencia se extinguirá y la Plataforma Nacional migrará conforme al presente Decreto.</p>
                    </content>
                </article>
            </chapter>
        </body>
    </act>
</akomaNtoso>
"""

# AKN XML reproducing the real-world amparo case where a DOF reform decree,
# appended after the body, re-uses substantive article numbers with the same
# <num>Artículo N</num> shape (no ordinal, no "trans-" id). This is the harder
# variant the source XML does not cleanly mark as transitorio; the defensive
# de-dup pass must still keep both docs distinct.
REFORM_DECREE_COLLISION_XML = """<?xml version="1.0" encoding="UTF-8"?>
<akomaNtoso xmlns="http://docs.oasis-open.org/legaldocml/ns/akn/3.0">
    <act name="law">
        <body>
            <chapter id="capitulo-4">
                <num>CAPÍTULO IV</num>
                <article id="art-27">
                    <num>Artículo 27</num>
                    <content>
                        <p>Artículo 27. Las notificaciones personales se harán de acuerdo con las siguientes reglas.</p>
                    </content>
                </article>
            </chapter>
            <chapter id="capitulo-reform">
                <num>CAPÍTULO III</num>
                <article id="art-27">
                    <num>Artículo 27</num>
                    <content>
                        <p>artículo 27; párrafos tercero y cuarto, a la fracción II del artículo 28, del decreto de reforma.</p>
                    </content>
                </article>
            </chapter>
        </body>
    </act>
</akomaNtoso>
"""


class TestIndexLawsCommand:

    @pytest.fixture
    def command(self):
        cmd = Command()
        cmd.stdout = MagicMock()
        cmd.stderr = MagicMock()
        cmd.style = MagicMock()
        return cmd

    def test_extract_articles_hierarchy(self, command):
        """Verify extraction of Book/Title/Chapter structure."""
        articles = command.extract_articles_from_xml(MINIMAL_V2_XML, "test_law")

        assert len(articles) == 2

        # Test Article 1 (Deep Hierarchy)
        art1 = articles[0]
        assert art1["article_id"] == "1"
        assert "orden público" in art1["text"]

        # Check hierarchy matches
        assert art1["book"]["num"] == "LIBRO PRIMERO"
        assert art1["book"]["heading"] == "Disposiciones Generales"

        assert art1["title"]["num"] == "TÍTULO I"
        assert art1["title"]["heading"] == "Del Ámbito de Validez"

        assert art1["chapter"]["num"] == "CAPÍTULO I"
        assert art1["chapter"]["heading"] == "Objeto de la Ley"

    def test_extract_articles_flat(self, command):
        """Verify extraction of an article with no hierarchy."""
        articles = command.extract_articles_from_xml(MINIMAL_V2_XML, "test_law")
        art2 = articles[1]

        assert art2["article_id"] == "2"
        assert art2["book"] is None
        assert art2["title"] is None
        assert art2["title"] is None
        assert art2["chapter"] is None

    # ── Defect 1: transitorio / substantive-article id collision ────────────

    def test_transitorio_and_substantive_article_coexist(self, command):
        """A transitorio and a same-numbered substantive article must BOTH
        survive extraction with DISTINCT ids and their own correct text.

        This is the regression test that was missing: pre-fix the "Octavo"
        transitorio and substantive article 8 both derived article_id "8" and
        the transitorio overwrote the real article in Elasticsearch.
        """
        articles = command.extract_articles_from_xml(
            TRANSITORIO_COLLISION_XML, "lfpdppp"
        )

        by_id = {a["article_id"]: a for a in articles}

        # All three provisions survive as separate entries.
        assert len(articles) == 3, f"expected 3 distinct articles, got {by_id.keys()}"

        # The substantive article 8 keeps the bare number and its real text.
        assert "8" in by_id, f"substantive article 8 missing: {list(by_id)}"
        assert by_id["8"]["is_transitorio"] is False
        assert "consentimiento del titular" in by_id["8"]["text"]

        # The "Octavo" transitorio lives at a namespaced, non-colliding id.
        assert "8" != "T-8"
        assert "T-8" in by_id, f"transitorio Octavo missing/collided: {list(by_id)}"
        assert by_id["T-8"]["is_transitorio"] is True
        assert "Plataforma Nacional" in by_id["T-8"]["text"]

        # The substantive text must NOT have been overwritten by the transitorio.
        assert "Plataforma Nacional" not in by_id["8"]["text"]

        # The "Primero" transitorio is likewise namespaced.
        assert "T-1" in by_id
        assert by_id["T-1"]["is_transitorio"] is True

        # The resulting Elasticsearch _ids are all unique.
        es_ids = [f"lfpdppp-{a['article_id']}" for a in articles]
        assert len(es_ids) == len(set(es_ids)), f"duplicate ES _ids: {es_ids}"
        assert "lfpdppp-8" in es_ids
        assert "lfpdppp-T-8" in es_ids

    def test_reform_decree_reused_numbers_do_not_overwrite(self, command):
        """Even when the source XML does NOT cleanly mark a reform decree as
        transitorio (same <num>Artículo N</num>, no ordinal, no trans- id),
        the defensive de-dup pass must keep both occurrences as distinct docs
        rather than silently overwriting the substantive article.
        """
        articles = command.extract_articles_from_xml(
            REFORM_DECREE_COLLISION_XML, "amparo"
        )

        assert len(articles) == 2, "both art-27 occurrences must be retained"
        ids = [a["article_id"] for a in articles]
        assert len(set(ids)) == 2, f"ids must be distinct, got {ids}"

        # First occurrence keeps the canonical number; the substantive text is
        # served from it.
        assert ids[0] == "27"
        assert "notificaciones personales" in articles[0]["text"]

        # Second occurrence is suffixed so it cannot clobber the first in ES.
        assert ids[1].startswith("27-")
        es_ids = [f"amparo-{a['article_id']}" for a in articles]
        assert len(set(es_ids)) == 2

    # ── Defect 2: newest LawVersion must be indexed ─────────────────────────

    def test_indexes_newest_version_not_oldest(self, command):
        """index_law must index the NEWEST version. LawVersion.Meta.ordering is
        ["-publication_date"] (descending), so the queryset's .first() is the
        newest. Regression: the code used .last() and indexed the OLDEST
        (superseded) version.
        """
        newest_version = MagicMock()
        newest_version.xml_file_path = "path/to/newest.xml"
        newest_version.publication_date.isoformat.return_value = "2025-03-20"

        oldest_version = MagicMock()
        oldest_version.xml_file_path = "path/to/oldest.xml"
        oldest_version.publication_date.isoformat.return_value = "2010-07-05"

        mock_law = MagicMock()
        mock_law.official_id = "lfpdppp"
        mock_law.name = "LFPDPPP"
        mock_law.category = "Ley"
        mock_law.tier = "federal"
        mock_law.municipality = ""
        mock_law.state = ""
        mock_law.status = "vigente"
        mock_law.domains = []
        mock_law.law_type = "legislative"
        mock_law.short_name = None

        # Simulate the Meta.ordering=["-publication_date"] queryset:
        #   .first() → newest, .last() → oldest.
        mock_law.versions.first.return_value = newest_version
        mock_law.versions.last.return_value = oldest_version

        mock_es = MagicMock()

        with pytest.MonkeyPatch.context() as m:
            from apps.api.management.commands import index_laws

            captured = {}

            def _fake_read(path):
                captured["path"] = path
                return MINIMAL_V2_XML

            m.setattr(index_laws, "read_data_content", _fake_read)
            m.setattr(index_laws, "helpers", MagicMock())

            command.index_law(mock_law, mock_es, dry_run=False)

        # The file that was read must be the newest version's, never the oldest.
        assert captured["path"] == "path/to/newest.xml"
        assert captured["path"] != "path/to/oldest.xml"

    def test_handle_indexing_municipality(self, command):
        """Verify municipality field is added to ES document."""
        # Mock Law object
        mock_law = MagicMock()
        mock_law.official_id = "reglamento_gdl"
        mock_law.name = "Reglamento GDL"
        mock_law.category = "Reglamento"
        mock_law.tier = "municipal"
        mock_law.municipality = "Guadalajara"
        mock_law.status = "active"

        # Mock Version
        mock_version = MagicMock()
        mock_version.xml_file_path = "path/to/xml"
        mock_version.publication_date.isoformat.return_value = "2023-01-01"
        mock_law.versions.first.return_value = mock_version

        # Use the mock Law bound in the Command module (not a fresh import)
        mock_qs = MagicMock()
        mock_qs.__iter__.return_value = iter([mock_law])
        mock_qs.count.return_value = 1
        _MockLaw.objects.filter.return_value = mock_qs

        # Mock Path/File Operations
        with MagicMock() as mock_path_cls:
            mock_cwd = MagicMock()
            mock_xml_file = MagicMock()
            mock_xml_file.exists.return_value = True
            mock_xml_file.read_text.return_value = MINIMAL_V2_XML

            mock_cwd.__truediv__.return_value = mock_xml_file

            # Patch Path in the command module
            with pytest.MonkeyPatch.context() as m:
                m.setattr("pathlib.Path.cwd", lambda: mock_cwd)

                # Mock helpers.bulk via monkeypatch (properly cleaned up)
                mock_helpers = MagicMock()
                from apps.api.management.commands import index_laws

                m.setattr(index_laws, "helpers", mock_helpers)

                # Run handle
                command.handle(
                    law_id="reglamento_gdl",
                    dry_run=False,
                    limit=None,
                    create_indices=False,
                    tier="all",
                    reindex=False,
                    migrate_alias=False,
                )

                # Verify bulk called
                assert mock_helpers.bulk.called
                call_args = mock_helpers.bulk.call_args
                actions = call_args[0][1]

                # Check first doc
                doc = actions[0]
                assert doc["_source"]["municipality"] == "Guadalajara"
                assert doc["_source"]["tier"] == "municipal"

    def test_with_embeddings_adds_text_embedding(self, command):
        """When embedding_generator is provided, articles get text_embedding field."""
        # Fixed 768-dim vector for deterministic assertion
        fake_vector = [0.01] * 768

        mock_embedding_gen = MagicMock()
        mock_embedding_gen.generate.return_value = fake_vector

        # Mock Law object
        mock_law = MagicMock()
        mock_law.official_id = "test_embed_law"
        mock_law.name = "Ley de Prueba Embeddings"
        mock_law.category = "Ley"
        mock_law.tier = "federal"
        mock_law.municipality = ""
        mock_law.state = ""
        mock_law.status = "vigente"
        mock_law.domains = []
        mock_law.law_type = "legislative"
        mock_law.short_name = None

        # Mock Version
        mock_version = MagicMock()
        mock_version.xml_file_path = "path/to/embed_xml"
        mock_version.publication_date.isoformat.return_value = "2024-06-01"
        mock_law.versions.first.return_value = mock_version

        # Mock ES client
        mock_es = MagicMock()

        with pytest.MonkeyPatch.context() as m:
            # Mock read_data_content to return our test XML
            from apps.api.management.commands import index_laws

            m.setattr(index_laws, "read_data_content", lambda path: MINIMAL_V2_XML)

            mock_helpers = MagicMock()
            m.setattr(index_laws, "helpers", mock_helpers)

            # Call index_law directly with embedding_generator
            count = command.index_law(
                mock_law, mock_es, dry_run=False, embedding_generator=mock_embedding_gen
            )

            # Should have indexed 2 articles
            assert count == 2

            # Verify embedding generator was called for each article
            assert mock_embedding_gen.generate.call_count == 2

            # Verify bulk was called; first call is article actions, second is law doc
            assert mock_helpers.bulk.call_count == 2
            article_call_args = mock_helpers.bulk.call_args_list[0]
            actions = article_call_args[0][1]

            assert len(actions) == 2
            for doc in actions:
                assert (
                    "text_embedding" in doc["_source"]
                ), f"Article {doc['_id']} missing text_embedding"
                assert doc["_source"]["text_embedding"] == fake_vector
                assert len(doc["_source"]["text_embedding"]) == 768

    def test_without_embeddings_no_text_embedding_field(self, command):
        """When no embedding_generator is provided, articles lack text_embedding."""
        # Mock Law object
        mock_law = MagicMock()
        mock_law.official_id = "test_no_embed"
        mock_law.name = "Ley Sin Embeddings"
        mock_law.category = "Ley"
        mock_law.tier = "federal"
        mock_law.municipality = ""
        mock_law.state = ""
        mock_law.status = "vigente"
        mock_law.domains = []
        mock_law.law_type = "legislative"
        mock_law.short_name = None

        # Mock Version
        mock_version = MagicMock()
        mock_version.xml_file_path = "path/to/xml"
        mock_version.publication_date.isoformat.return_value = "2024-06-01"
        mock_law.versions.first.return_value = mock_version

        mock_es = MagicMock()

        with pytest.MonkeyPatch.context() as m:
            from apps.api.management.commands import index_laws

            m.setattr(index_laws, "read_data_content", lambda path: MINIMAL_V2_XML)

            mock_helpers = MagicMock()
            m.setattr(index_laws, "helpers", mock_helpers)

            # Call index_law WITHOUT embedding_generator
            count = command.index_law(mock_law, mock_es, dry_run=False)

            assert count == 2
            assert mock_helpers.bulk.call_count == 2

            # First bulk call is article actions
            article_call_args = mock_helpers.bulk.call_args_list[0]
            actions = article_call_args[0][1]

            for doc in actions:
                assert (
                    "text_embedding" not in doc["_source"]
                ), f"Article {doc['_id']} should not have text_embedding"

    def test_embedding_failure_skips_gracefully(self, command):
        """When embedding generation fails for an article, it is still indexed without embedding."""
        mock_embedding_gen = MagicMock()
        mock_embedding_gen.generate.side_effect = RuntimeError("Model error")

        # Mock Law object
        mock_law = MagicMock()
        mock_law.official_id = "test_embed_fail"
        mock_law.name = "Ley Embed Failure"
        mock_law.category = "Ley"
        mock_law.tier = "federal"
        mock_law.municipality = ""
        mock_law.state = ""
        mock_law.status = "vigente"
        mock_law.domains = []
        mock_law.law_type = "legislative"
        mock_law.short_name = None

        mock_version = MagicMock()
        mock_version.xml_file_path = "path/to/xml"
        mock_version.publication_date.isoformat.return_value = "2024-06-01"
        mock_law.versions.first.return_value = mock_version

        mock_es = MagicMock()

        with pytest.MonkeyPatch.context() as m:
            from apps.api.management.commands import index_laws

            m.setattr(index_laws, "read_data_content", lambda path: MINIMAL_V2_XML)

            mock_helpers = MagicMock()
            m.setattr(index_laws, "helpers", mock_helpers)

            # Call index_law with a failing embedding generator
            count = command.index_law(
                mock_law, mock_es, dry_run=False, embedding_generator=mock_embedding_gen
            )

            # Articles should still be indexed despite embedding failures
            assert count == 2
            assert mock_helpers.bulk.call_count == 2

            # First bulk call is article actions
            article_call_args = mock_helpers.bulk.call_args_list[0]
            actions = article_call_args[0][1]

            # Embedding generation failed, so text_embedding should NOT be present
            for doc in actions:
                assert "text_embedding" not in doc["_source"]
