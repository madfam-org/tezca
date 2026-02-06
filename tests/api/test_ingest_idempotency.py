"""
Tests for pipeline idempotency — running ingestion/indexing twice must not create duplicates.
"""

import uuid
from datetime import date
from unittest.mock import MagicMock, patch

import pytest

from apps.api.models import Law, LawVersion


@pytest.mark.django_db
class TestIngestStateIdempotency:
    """Test that ingest_state_laws management command is idempotent."""

    def _make_metadata(self, official_id, **overrides):
        defaults = {
            "official_id": official_id,
            "law_name": "Código Civil de Colima",
            "category": "codigo",
            "tier": "state",
            "state": "Colima",
            "publication_date": "2024-01-15",
            "text_file": "data/state/colima/text/codigo_civil.txt",
            "akn_file_path": "",
            "url": "https://example.com/colima/civil",
        }
        defaults.update(overrides)
        return defaults

    def _invoke_create(self, cmd, metadata, dry_run=False):
        """Call create_law_and_version on a Command instance."""
        return cmd.create_law_and_version(metadata, dry_run=dry_run)

    @patch(
        "apps.api.management.commands.ingest_state_laws.resolve_data_path_or_none",
    )
    def test_double_ingest_no_duplicate_versions(self, mock_resolve):
        """Running ingest twice on same data produces exactly 1 LawVersion."""
        from apps.api.management.commands.ingest_state_laws import Command

        uid = f"test_state_{uuid.uuid4().hex[:8]}"
        metadata = self._make_metadata(uid)

        # Mock resolve_data_path_or_none to return a fake path with text
        fake_path = MagicMock()
        fake_path.read_text.return_value = "Artículo 1.- Test content."
        mock_resolve.return_value = fake_path

        cmd = Command()

        # First run
        r1 = self._invoke_create(cmd, metadata)
        assert r1["success"] is True
        assert r1["action"] == "created"
        assert r1["version_created"] is True

        # Second run (same data)
        r2 = self._invoke_create(cmd, metadata)
        assert r2["success"] is True
        assert r2["action"] == "updated"
        assert r2["version_created"] is False

        # Exactly 1 LawVersion
        law = Law.objects.get(official_id=uid)
        assert LawVersion.objects.filter(law=law).count() == 1

    @patch(
        "apps.api.management.commands.ingest_state_laws.resolve_data_path_or_none",
    )
    def test_version_updated_on_rerun(self, mock_resolve):
        """Re-running updates metadata on existing LawVersion."""
        from apps.api.management.commands.ingest_state_laws import Command

        uid = f"test_state_{uuid.uuid4().hex[:8]}"
        metadata = self._make_metadata(uid, url="https://old.example.com")

        fake_path = MagicMock()
        fake_path.read_text.return_value = "Text content."
        mock_resolve.return_value = fake_path

        cmd = Command()
        self._invoke_create(cmd, metadata)

        # Re-run with different URL
        metadata["url"] = "https://new.example.com"
        self._invoke_create(cmd, metadata)

        law = Law.objects.get(official_id=uid)
        version = LawVersion.objects.get(law=law)
        assert version.dof_url == "https://new.example.com"


@pytest.mark.django_db
class TestIngestMunicipalIdempotency:
    """Test that ingest_municipal_laws management command is idempotent."""

    def _make_metadata(self, official_id, **overrides):
        defaults = {
            "official_id": official_id,
            "law_name": "Reglamento de Tránsito",
            "category": "reglamento",
            "state": "Jalisco",
            "municipality": "Guadalajara",
            "publication_date": "2024-03-01",
            "text_file": "data/municipal/guadalajara/text/transito.txt",
            "akn_file_path": "",
            "url": "https://example.com/gdl/transito",
        }
        defaults.update(overrides)
        return defaults

    @patch(
        "apps.api.management.commands.ingest_municipal_laws.resolve_data_path_or_none",
    )
    def test_double_ingest_no_duplicate_versions(self, mock_resolve):
        """Running municipal ingest twice produces exactly 1 LawVersion."""
        from apps.api.management.commands.ingest_municipal_laws import Command

        uid = f"test_muni_{uuid.uuid4().hex[:8]}"
        metadata = self._make_metadata(uid)

        fake_path = MagicMock()
        mock_resolve.return_value = fake_path

        cmd = Command()

        r1 = cmd.create_law_and_version(metadata)
        assert r1["success"] is True
        assert r1["action"] == "created"
        assert r1["version_created"] is True

        r2 = cmd.create_law_and_version(metadata)
        assert r2["success"] is True
        assert r2["action"] == "updated"
        assert r2["version_created"] is False

        law = Law.objects.get(official_id=uid)
        assert LawVersion.objects.filter(law=law).count() == 1

    @patch(
        "apps.api.management.commands.ingest_municipal_laws.resolve_data_path_or_none",
    )
    def test_version_updated_on_rerun(self, mock_resolve):
        """Re-running updates metadata on existing municipal LawVersion."""
        from apps.api.management.commands.ingest_municipal_laws import Command

        uid = f"test_muni_{uuid.uuid4().hex[:8]}"
        metadata = self._make_metadata(uid, url="https://old.example.com")

        fake_path = MagicMock()
        mock_resolve.return_value = fake_path

        cmd = Command()
        cmd.create_law_and_version(metadata)

        metadata["url"] = "https://new.example.com"
        cmd.create_law_and_version(metadata)

        law = Law.objects.get(official_id=uid)
        version = LawVersion.objects.get(law=law)
        assert version.dof_url == "https://new.example.com"


@pytest.mark.django_db
class TestIndexLawsIdempotency:
    """Test that index_laws produces deterministic ES document IDs."""

    def test_raw_text_doc_has_deterministic_id(self):
        """_index_raw_text produces a doc with _id = '{official_id}-full_text'."""
        from apps.api.management.commands.index_laws import Command

        uid = f"test_idx_{uuid.uuid4().hex[:8]}"
        law = Law.objects.create(
            official_id=uid, name="Test Law", tier="state", category="ley"
        )
        version = LawVersion.objects.create(law=law, publication_date=date(2024, 1, 1))

        cmd = Command()
        cmd.stdout = MagicMock()
        cmd.stderr = MagicMock()

        mock_es = MagicMock()
        captured_actions = []

        def capture_bulk(es_client, actions):
            captured_actions.extend(actions)

        with patch(
            "apps.api.management.commands.index_laws.helpers.bulk",
            side_effect=capture_bulk,
        ):
            cmd._index_raw_text(law, version, "Test text content", mock_es)

        # Find the article doc (not the law-level doc)
        article_docs = [a for a in captured_actions if a["_index"] == "articles"]
        assert len(article_docs) == 1
        assert article_docs[0]["_id"] == f"{uid}-full_text"

    def test_article_docs_have_deterministic_id(self):
        """Article docs from AKN XML get _id = '{official_id}-{article_id}'."""
        from apps.api.management.commands.index_laws import Command

        uid = f"test_idx_{uuid.uuid4().hex[:8]}"
        law = Law.objects.create(
            official_id=uid, name="Test Law", tier="federal", category="ley"
        )
        version = LawVersion.objects.create(
            law=law,
            publication_date=date(2024, 1, 1),
            xml_file_path="fake.xml",
        )

        akn_xml = """<?xml version="1.0" encoding="UTF-8"?>
<akomaNtoso xmlns="http://docs.oasis-open.org/legaldocml/ns/akn/3.0">
  <act name="test">
    <meta>
      <identification source="#source">
        <FRBRWork>
          <FRBRthis value="/mx/act/2024/test"/>
          <FRBRuri value="/mx/act/2024/test"/>
          <FRBRdate date="2024-01-01" name="Generation"/>
        </FRBRWork>
      </identification>
    </meta>
    <body>
      <article eId="art_1">
        <num>Artículo 1</num>
        <content><p>Primera disposición.</p></content>
      </article>
      <article eId="art_2">
        <num>Artículo 2</num>
        <content><p>Segunda disposición.</p></content>
      </article>
    </body>
  </act>
</akomaNtoso>"""

        cmd = Command()
        cmd.stdout = MagicMock()
        cmd.stderr = MagicMock()

        mock_es = MagicMock()
        captured_actions = []

        def capture_bulk(es_client, actions):
            captured_actions.extend(actions)

        with patch(
            "apps.api.management.commands.index_laws.helpers.bulk",
            side_effect=capture_bulk,
        ), patch(
            "apps.api.management.commands.index_laws.resolve_data_path_or_none",
        ) as mock_resolve:
            fake_path = MagicMock()
            fake_path.read_text.return_value = akn_xml
            mock_resolve.return_value = fake_path

            cmd.index_law(law, mock_es)

        article_docs = [a for a in captured_actions if a["_index"] == "articles"]
        assert len(article_docs) == 2

        ids = {doc["_id"] for doc in article_docs}
        assert f"{uid}-Artículo 1" in ids
        assert f"{uid}-Artículo 2" in ids
