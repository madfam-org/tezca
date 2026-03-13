"""Elasticsearch index alias manager for zero-downtime reindexing.

Strategy: articles (alias) -> articles_v20260313 (concrete index)

Reindex flow:
1. Create articles_v{timestamp} with same mappings
2. Bulk index into new index
3. Atomic swap: POST /_aliases { remove old, add new }
4. Optionally delete old index
"""

import logging
import time

from elasticsearch import Elasticsearch, NotFoundError

from apps.api.config import INDEX_ALIAS, INDEX_PREFIX, es_client

logger = logging.getLogger(__name__)


def get_current_index(client: Elasticsearch = None) -> str | None:
    """Get the concrete index behind the alias, or None if alias doesn't exist."""
    client = client or es_client
    try:
        result = client.indices.get_alias(name=INDEX_ALIAS)
        indices = list(result.keys())
        return indices[0] if indices else None
    except NotFoundError:
        return None


def create_versioned_index(
    client: Elasticsearch = None,
    mappings: dict = None,
    settings: dict = None,
) -> str:
    """Create a new versioned index with timestamp suffix."""
    client = client or es_client
    index_name = f"{INDEX_PREFIX}{int(time.time())}"

    body = {}
    if mappings:
        body["mappings"] = mappings
    if settings:
        body["settings"] = settings

    client.indices.create(index=index_name, body=body)
    logger.info("Created versioned index: %s", index_name)
    return index_name


def swap_alias(
    client: Elasticsearch = None,
    old_index: str = None,
    new_index: str = None,
) -> None:
    """Atomically swap the alias from old_index to new_index."""
    client = client or es_client

    actions = []
    if old_index:
        actions.append({"remove": {"index": old_index, "alias": INDEX_ALIAS}})
    actions.append({"add": {"index": new_index, "alias": INDEX_ALIAS}})

    client.indices.update_aliases(body={"actions": actions})
    logger.info("Swapped alias '%s': %s -> %s", INDEX_ALIAS, old_index, new_index)


def cleanup_old_indices(client: Elasticsearch = None, keep_n: int = 2) -> list[str]:
    """Delete old versioned indices, keeping the most recent keep_n."""
    client = client or es_client

    # Find all versioned indices
    try:
        all_indices = client.indices.get(index=f"{INDEX_PREFIX}*")
    except NotFoundError:
        return []

    index_names = sorted(all_indices.keys())

    # Don't delete the one behind the current alias
    current = get_current_index(client)
    protected = {current} if current else set()

    # Keep the most recent keep_n
    candidates = [i for i in index_names if i not in protected]
    to_delete = candidates[:-keep_n] if len(candidates) > keep_n else []

    for idx in to_delete:
        client.indices.delete(index=idx)
        logger.info("Deleted old index: %s", idx)

    return to_delete


def ensure_alias_exists(client: Elasticsearch = None) -> bool:
    """One-time migration: if 'articles' is a concrete index, convert to alias.

    Returns True if migration was performed, False if alias already exists.
    """
    client = client or es_client

    # Check if alias already exists
    if client.indices.exists_alias(name=INDEX_ALIAS):
        logger.info("Alias '%s' already exists", INDEX_ALIAS)
        return False

    # Check if concrete index exists
    if not client.indices.exists(index=INDEX_ALIAS):
        logger.info("Neither alias nor index '%s' exists", INDEX_ALIAS)
        return False

    # Concrete index exists -- migrate to alias
    # 1. Get current mappings/settings
    index_info = client.indices.get(index=INDEX_ALIAS)
    info = index_info[INDEX_ALIAS]
    mappings = info.get("mappings", {})
    settings = info.get("settings", {}).get("index", {})

    # Remove read-only settings that can't be set on create
    for key in [
        "creation_date",
        "uuid",
        "version",
        "provided_name",
        "number_of_replicas",
        "number_of_shards",
    ]:
        settings.pop(key, None)

    # 2. Create new versioned index
    new_index = create_versioned_index(
        client, mappings=mappings, settings=settings if settings else None
    )

    # 3. Reindex data
    client.reindex(
        body={
            "source": {"index": INDEX_ALIAS},
            "dest": {"index": new_index},
        },
        wait_for_completion=True,
        request_timeout=3600,
    )

    # 4. Delete old concrete index
    client.indices.delete(index=INDEX_ALIAS)

    # 5. Create alias pointing to new index
    swap_alias(client, old_index=None, new_index=new_index)

    logger.info("Migrated concrete index '%s' to alias -> %s", INDEX_ALIAS, new_index)
    return True


def get_index_stats(client: Elasticsearch = None) -> dict:
    """Get status info about current alias and indices."""
    client = client or es_client

    current = get_current_index(client)

    # Find all versioned indices
    try:
        all_indices = client.indices.get(index=f"{INDEX_PREFIX}*")
        versioned = sorted(all_indices.keys())
    except NotFoundError:
        versioned = []

    # Check if alias exists
    alias_exists = client.indices.exists_alias(name=INDEX_ALIAS)

    # Check if concrete index exists (non-alias)
    concrete_exists = False
    if not alias_exists:
        concrete_exists = client.indices.exists(index=INDEX_ALIAS)

    return {
        "alias": INDEX_ALIAS,
        "alias_exists": alias_exists,
        "concrete_exists": concrete_exists,
        "current_index": current,
        "versioned_indices": versioned,
        "needs_migration": concrete_exists and not alias_exists,
    }
