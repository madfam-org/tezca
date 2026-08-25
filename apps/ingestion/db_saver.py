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

    @staticmethod
    def _resolve_status(raw_status):
        """Normalise a registry status string to a valid Law.Status value.

        The registry uses non-canonical markers that are not model choices:
          - "active"      → a current, in-force law            → VIGENTE
          - "discovered"  → known but not yet ingested; once we are saving a
                            version it IS ingested and current  → VIGENTE
          - missing/blank                                       → VIGENTE
        Canonical values ("vigente", "abrogada", "derogada", "unknown") are
        passed through unchanged (case-insensitively).
        """
        from apps.api.models import Law

        if not raw_status:
            return Law.Status.VIGENTE

        normalized = str(raw_status).strip().lower()
        valid = {choice.value for choice in Law.Status}
        if normalized in valid:
            return normalized

        alias = {
            "active": Law.Status.VIGENTE,
            "vigent": Law.Status.VIGENTE,
            "current": Law.Status.VIGENTE,
            "discovered": Law.Status.VIGENTE,
            "in_force": Law.Status.VIGENTE,
            "abrogated": Law.Status.ABROGADA,
            "repealed": Law.Status.ABROGADA,
            "derogated": Law.Status.DEROGADA,
        }
        return alias.get(normalized, Law.Status.VIGENTE)

    def save_law_version(self, law_metadata, xml_path, pdf_path, quality_metrics=None):
        """
        Save law version to database.

        Args:
            law_metadata (dict): Metadata from registry
            xml_path (Path): Path to generated XML
            pdf_path (Path): Path to downloaded PDF
            quality_metrics: Optional QualityMetrics with grade/score
        """
        from django.utils.dateparse import parse_date

        from apps.api.models import Law, LawVersion

        # Resolve the legal status. A law present in the registry with a current
        # version is "vigente" by default. The registry historically carries
        # non-canonical status strings ("active", "discovered") that are NOT
        # valid Law.Status choices, so normalise them. Without this the Law is
        # created with the model default (UNKNOWN) and the API serves
        # status="unknown" for every freshly ingested law.
        status = self._resolve_status(law_metadata.get("status"))

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
                "status": status,
            },
        )

        if not created:
            # Update metadata if needed
            law.name = law_metadata["name"]
            law.short_name = law_metadata.get("short_name", law.short_name)
            # Promote an unknown/blank status to the resolved one. Never
            # downgrade an explicitly-curated status back to "unknown".
            if status != Law.Status.UNKNOWN or not law.status:
                law.status = status
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

        # Persist quality metrics
        if quality_metrics is not None:
            version.quality_grade = quality_metrics.grade
            version.quality_score = quality_metrics.overall_score
            version.save(update_fields=["quality_grade", "quality_score"])

        return version

    def get_law_history(self, law_id):
        """Get all versions for a law."""
        from apps.api.models import Law

        try:
            law = Law.objects.get(official_id=law_id)
            return law.versions.all()
        except Law.DoesNotExist:
            return []
