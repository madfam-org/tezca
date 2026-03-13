"""Tests for Elasticsearch index alias manager.

Tests all functions in apps.api.es_index_manager using a mock ES client.
"""

import unittest
from io import StringIO
from unittest.mock import MagicMock, call, patch

from elastic_transport import ApiResponseMeta, HttpHeaders
from elasticsearch import NotFoundError

from apps.api.es_index_manager import (
    cleanup_old_indices,
    create_versioned_index,
    ensure_alias_exists,
    get_current_index,
    get_index_stats,
    swap_alias,
)


def _make_mock_client():
    """Create a mock ES client with indices namespace."""
    client = MagicMock()
    client.indices = MagicMock()
    return client


def _not_found_error(message="not found"):
    """Create a NotFoundError compatible with ES 8.x client."""
    meta = ApiResponseMeta(
        status=404,
        http_version="1.1",
        headers=HttpHeaders(),
        duration=0.0,
        node=None,
    )
    return NotFoundError(message, meta=meta, body={"error": message})


class TestGetCurrentIndex(unittest.TestCase):
    def test_returns_concrete_index_behind_alias(self):
        client = _make_mock_client()
        client.indices.get_alias.return_value = {"articles_v1710000000": {}}
        result = get_current_index(client)
        self.assertEqual(result, "articles_v1710000000")
        client.indices.get_alias.assert_called_once_with(name="articles")

    def test_returns_none_when_alias_missing(self):
        client = _make_mock_client()
        client.indices.get_alias.side_effect = _not_found_error("alias not found")
        result = get_current_index(client)
        self.assertIsNone(result)

    def test_returns_none_when_alias_has_no_indices(self):
        client = _make_mock_client()
        client.indices.get_alias.return_value = {}
        result = get_current_index(client)
        self.assertIsNone(result)


class TestCreateVersionedIndex(unittest.TestCase):
    @patch("apps.api.es_index_manager.time")
    def test_creates_index_with_timestamp_prefix(self, mock_time):
        mock_time.time.return_value = 1710000000
        client = _make_mock_client()

        result = create_versioned_index(client)

        self.assertEqual(result, "articles_v1710000000")
        client.indices.create.assert_called_once_with(
            index="articles_v1710000000", body={}
        )

    @patch("apps.api.es_index_manager.time")
    def test_passes_mappings_and_settings(self, mock_time):
        mock_time.time.return_value = 1710000001
        client = _make_mock_client()
        mappings = {"properties": {"law_id": {"type": "keyword"}}}
        settings = {"number_of_replicas": 0}

        result = create_versioned_index(client, mappings=mappings, settings=settings)

        self.assertEqual(result, "articles_v1710000001")
        client.indices.create.assert_called_once_with(
            index="articles_v1710000001",
            body={"mappings": mappings, "settings": settings},
        )


class TestSwapAlias(unittest.TestCase):
    def test_swaps_alias_from_old_to_new(self):
        client = _make_mock_client()

        swap_alias(client, old_index="articles_v1", new_index="articles_v2")

        client.indices.update_aliases.assert_called_once_with(
            body={
                "actions": [
                    {"remove": {"index": "articles_v1", "alias": "articles"}},
                    {"add": {"index": "articles_v2", "alias": "articles"}},
                ]
            }
        )

    def test_adds_alias_without_remove_when_no_old_index(self):
        client = _make_mock_client()

        swap_alias(client, old_index=None, new_index="articles_v1")

        client.indices.update_aliases.assert_called_once_with(
            body={
                "actions": [
                    {"add": {"index": "articles_v1", "alias": "articles"}},
                ]
            }
        )


class TestCleanupOldIndices(unittest.TestCase):
    def test_keeps_n_most_recent_indices(self):
        client = _make_mock_client()
        # 4 versioned indices, alias points to v4
        client.indices.get.return_value = {
            "articles_v1": {},
            "articles_v2": {},
            "articles_v3": {},
            "articles_v4": {},
        }
        client.indices.get_alias.return_value = {"articles_v4": {}}

        deleted = cleanup_old_indices(client, keep_n=2)

        # v4 is protected (current alias). Candidates: v1, v2, v3.
        # Keep 2 most recent candidates (v2, v3). Delete v1.
        self.assertEqual(deleted, ["articles_v1"])
        client.indices.delete.assert_called_once_with(index="articles_v1")

    def test_does_not_delete_current_alias_target(self):
        client = _make_mock_client()
        client.indices.get.return_value = {
            "articles_v1": {},
            "articles_v2": {},
        }
        client.indices.get_alias.return_value = {"articles_v2": {}}

        deleted = cleanup_old_indices(client, keep_n=2)

        # Only v1 is a candidate, keep_n=2 means don't delete any
        self.assertEqual(deleted, [])
        client.indices.delete.assert_not_called()

    def test_returns_empty_when_no_versioned_indices(self):
        client = _make_mock_client()
        client.indices.get.side_effect = _not_found_error("no indices")

        deleted = cleanup_old_indices(client, keep_n=2)

        self.assertEqual(deleted, [])


class TestEnsureAliasExists(unittest.TestCase):
    def test_returns_false_when_alias_already_exists(self):
        client = _make_mock_client()
        client.indices.exists_alias.return_value = True

        result = ensure_alias_exists(client)

        self.assertFalse(result)

    def test_returns_false_when_no_index_or_alias(self):
        client = _make_mock_client()
        client.indices.exists_alias.return_value = False
        client.indices.exists.return_value = False

        result = ensure_alias_exists(client)

        self.assertFalse(result)

    @patch("apps.api.es_index_manager.time")
    def test_migrates_concrete_index_to_alias(self, mock_time):
        mock_time.time.return_value = 1710000000
        client = _make_mock_client()

        # Alias does not exist, but concrete index does
        client.indices.exists_alias.return_value = False
        client.indices.exists.return_value = True
        client.indices.get.return_value = {
            "articles": {
                "mappings": {"properties": {"law_id": {"type": "keyword"}}},
                "settings": {
                    "index": {
                        "creation_date": "123",
                        "uuid": "abc",
                        "number_of_replicas": "1",
                        "number_of_shards": "1",
                        "provided_name": "articles",
                        "version": {"created": "8170000"},
                        "analysis": {"analyzer": {"spanish_legal": {}}},
                    }
                },
            }
        }

        result = ensure_alias_exists(client)

        self.assertTrue(result)

        # Should have created a new versioned index with cleaned settings
        client.indices.create.assert_called_once()
        create_call = client.indices.create.call_args
        self.assertEqual(create_call.kwargs["index"], "articles_v1710000000")
        body = create_call.kwargs["body"]
        self.assertIn("mappings", body)
        # Read-only settings should be stripped
        settings = body.get("settings", {})
        self.assertNotIn("creation_date", settings)
        self.assertNotIn("uuid", settings)
        # Custom settings should be preserved
        self.assertIn("analysis", settings)

        # Should have reindexed
        client.reindex.assert_called_once()

        # Should have deleted old concrete index
        client.indices.delete.assert_called_once_with(index="articles")

        # Should have created alias via update_aliases
        client.indices.update_aliases.assert_called_once()


class TestGetIndexStats(unittest.TestCase):
    def test_returns_correct_structure_with_alias(self):
        client = _make_mock_client()
        client.indices.get_alias.return_value = {"articles_v1710000000": {}}
        client.indices.get.return_value = {
            "articles_v1710000000": {},
            "articles_v1709000000": {},
        }
        client.indices.exists_alias.return_value = True

        stats = get_index_stats(client)

        self.assertEqual(stats["alias"], "articles")
        self.assertTrue(stats["alias_exists"])
        self.assertFalse(stats["concrete_exists"])
        self.assertEqual(stats["current_index"], "articles_v1710000000")
        self.assertEqual(
            stats["versioned_indices"],
            ["articles_v1709000000", "articles_v1710000000"],
        )
        self.assertFalse(stats["needs_migration"])

    def test_returns_needs_migration_when_concrete_only(self):
        client = _make_mock_client()
        # No alias
        client.indices.get_alias.side_effect = _not_found_error("alias not found")
        client.indices.get.side_effect = _not_found_error("no versioned")
        client.indices.exists_alias.return_value = False
        client.indices.exists.return_value = True

        stats = get_index_stats(client)

        self.assertFalse(stats["alias_exists"])
        self.assertTrue(stats["concrete_exists"])
        self.assertIsNone(stats["current_index"])
        self.assertEqual(stats["versioned_indices"], [])
        self.assertTrue(stats["needs_migration"])


# -- Management command tests use Django's TestCase --

from django.test import TestCase as DjangoTestCase


class TestManageEsAliasCommand(DjangoTestCase):
    @patch("apps.api.management.commands.manage_es_alias.get_index_stats")
    def test_status_subcommand(self, mock_stats):
        mock_stats.return_value = {
            "alias": "articles",
            "alias_exists": True,
            "concrete_exists": False,
            "current_index": "articles_v1710000000",
            "versioned_indices": ["articles_v1710000000"],
            "needs_migration": False,
        }

        from django.core.management import call_command

        out = StringIO()
        call_command("manage_es_alias", "--status", stdout=out)

        output = out.getvalue()
        self.assertIn("articles", output)
        self.assertIn("articles_v1710000000", output)
        self.assertIn("Alias exists: True", output)

    @patch("apps.api.management.commands.manage_es_alias.ensure_alias_exists")
    def test_migrate_subcommand(self, mock_ensure):
        mock_ensure.return_value = True

        from django.core.management import call_command

        out = StringIO()
        call_command("manage_es_alias", "--migrate", stdout=out)

        output = out.getvalue()
        self.assertIn("Migration complete", output)
        mock_ensure.assert_called_once()

    @patch("apps.api.management.commands.manage_es_alias.cleanup_old_indices")
    def test_cleanup_subcommand(self, mock_cleanup):
        mock_cleanup.return_value = ["articles_v1"]

        from django.core.management import call_command

        out = StringIO()
        call_command("manage_es_alias", "--cleanup", "--keep", "2", stdout=out)

        output = out.getvalue()
        self.assertIn("Deleted 1 old indices", output)
        mock_cleanup.assert_called_once_with(keep_n=2)

    @patch("apps.api.management.commands.manage_es_alias.es_client")
    @patch("apps.api.management.commands.manage_es_alias.swap_alias")
    @patch("apps.api.management.commands.manage_es_alias.get_current_index")
    def test_rollback_subcommand(self, mock_current, mock_swap, mock_es):
        mock_current.return_value = "articles_v1"
        mock_es.indices.exists.return_value = True

        from django.core.management import call_command

        out = StringIO()
        call_command("manage_es_alias", "--rollback", "articles_v2", stdout=out)

        output = out.getvalue()
        self.assertIn("Rolled back alias", output)
        mock_swap.assert_called_once_with(
            old_index="articles_v1", new_index="articles_v2"
        )
