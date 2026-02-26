import logging
import os
import sys
from pathlib import Path

import django

logger = logging.getLogger(__name__)


class DatabaseSaver:
    """Helper to save ingested law data to Django DB."""

    def __init__(self):
        self._setup_django()

    def _setup_django(self):
        """Ensure Django environment is ready."""
        try:
            from django.conf import settings

            if not settings.configured:
                # Add project root path (three levels up from apps/ingestion/db_saver.py)
                project_root = str(Path(__file__).parent.parent.parent)
                if project_root not in sys.path:
                    sys.path.insert(0, project_root)

                os.environ.setdefault("DJANGO_SETTINGS_MODULE", "apps.indigo.settings")
                django.setup()
        except Exception as e:
            logger.error(f"Failed to setup Django: {e}")
            raise

    def save_law_version(self, law_metadata, xml_path, pdf_path):
        """
        Save law version to database.

        Args:
            law_metadata (dict): Metadata from registry
            xml_path (Path): Path to generated XML
            pdf_path (Path): Path to downloaded PDF
        """
        from django.utils.dateparse import parse_date

        from apps.api.models import Law, LawVersion

        # 1. Get or Create Law
        # Note: tier is hardcoded to "federal" because law_registry.json uses
        # "tier" for thematic categories (fiscal, constitutional, etc.), not
        # jurisdictional level. The Law model expects jurisdictional tier.
        law, created = Law.objects.get_or_create(
            official_id=law_metadata["id"],
            defaults={
                "name": law_metadata["name"],
                "short_name": law_metadata.get("short_name", law_metadata["name"]),
                "category": law_metadata.get("category"),
                "tier": "federal",
            },
        )

        if not created:
            # Update metadata if needed
            law.name = law_metadata["name"]
            law.short_name = law_metadata.get("short_name", law.short_name)
            law.save()

        # 2. Extract dates
        # Try to use publication date from metadata, or fallback to today
        pub_date_str = law_metadata.get("publication_date")
        if pub_date_str and pub_date_str != "1900-01-01":  # Skip placeholder dates
            pub_date = parse_date(pub_date_str)
        else:
            # Use None for unknown dates - don't create version
            logger.warning(
                f"Skipping version creation for {law_metadata['id']} - missing publication date"
            )
            return None

        # 3. Create Version
        # Check if version exists to avoid duplicates
        version, v_created = LawVersion.objects.get_or_create(
            law=law,
            publication_date=pub_date,
            defaults={
                "dof_url": law_metadata.get("url"),
                "xml_file_path": str(xml_path),
                "valid_from": pub_date,  # Default to publication date
            },
        )

        if not v_created:
            # Update paths
            version.xml_file_path = str(xml_path)
            version.dof_url = law_metadata.get("url")
            version.save()

        return version

    def get_law_history(self, law_id):
        """Get all versions for a law."""
        from apps.api.models import Law

        try:
            law = Law.objects.get(official_id=law_id)
            return law.versions.all()
        except Law.DoesNotExist:
            return []
