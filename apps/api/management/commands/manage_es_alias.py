"""Manage Elasticsearch index aliases for zero-downtime reindexing.

Usage:
    python manage.py manage_es_alias --status
    python manage.py manage_es_alias --migrate
    python manage.py manage_es_alias --rollback articles_v1710000000
    python manage.py manage_es_alias --cleanup --keep 2
"""

from django.core.management.base import BaseCommand

from apps.api.config import es_client
from apps.api.es_index_manager import (
    cleanup_old_indices,
    ensure_alias_exists,
    get_current_index,
    get_index_stats,
    swap_alias,
)


class Command(BaseCommand):
    help = "Manage Elasticsearch index aliases for zero-downtime reindexing"

    def add_arguments(self, parser):
        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument(
            "--status", action="store_true", help="Show current alias status"
        )
        group.add_argument(
            "--migrate",
            action="store_true",
            help="Migrate concrete index to alias (one-time)",
        )
        group.add_argument(
            "--rollback",
            type=str,
            metavar="INDEX",
            help="Switch alias to a specific index",
        )
        group.add_argument(
            "--cleanup",
            action="store_true",
            help="Remove old versioned indices",
        )
        parser.add_argument(
            "--keep",
            type=int,
            default=2,
            help="Number of old indices to keep (with --cleanup)",
        )

    def handle(self, *args, **options):
        if options["status"]:
            self._status()
        elif options["migrate"]:
            self._migrate()
        elif options["rollback"]:
            self._rollback(options["rollback"])
        elif options["cleanup"]:
            self._cleanup(options["keep"])

    def _status(self):
        stats = get_index_stats()
        self.stdout.write(f"Alias: {stats['alias']}")
        self.stdout.write(f"  Alias exists: {stats['alias_exists']}")
        self.stdout.write(f"  Concrete index exists: {stats['concrete_exists']}")
        self.stdout.write(f"  Current index: {stats['current_index'] or '(none)'}")
        self.stdout.write(
            f"  Versioned indices: {', '.join(stats['versioned_indices']) or '(none)'}"
        )
        if stats["needs_migration"]:
            self.stdout.write(
                self.style.WARNING(
                    "  Needs migration: run --migrate to convert concrete index to alias"
                )
            )

    def _migrate(self):
        self.stdout.write("Migrating concrete index to alias...")
        migrated = ensure_alias_exists()
        if migrated:
            self.stdout.write(self.style.SUCCESS("Migration complete"))
        else:
            self.stdout.write(
                "No migration needed (alias already exists or no index found)"
            )

    def _rollback(self, target_index):
        current = get_current_index()
        if current == target_index:
            self.stdout.write(f"Alias already points to {target_index}")
            return

        if not es_client.indices.exists(index=target_index):
            self.stderr.write(self.style.ERROR(f"Index {target_index} does not exist"))
            return

        swap_alias(old_index=current, new_index=target_index)
        self.stdout.write(
            self.style.SUCCESS(f"Rolled back alias: {current} -> {target_index}")
        )

    def _cleanup(self, keep):
        deleted = cleanup_old_indices(keep_n=keep)
        if deleted:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Deleted {len(deleted)} old indices: {', '.join(deleted)}"
                )
            )
        else:
            self.stdout.write("No old indices to clean up")
