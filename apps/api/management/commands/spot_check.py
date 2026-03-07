"""
Management command to sample real laws and trace data through every layer.

Read-only, production-safe. Checks DB fields, file existence, text encoding,
AKN article counts, Elasticsearch consistency, and cross-reference integrity.

Usage:
    python manage.py spot_check
    python manage.py spot_check --golden-set
    python manage.py spot_check --limit 3
    python manage.py spot_check --golden-set --output report.json
"""

import datetime
import json
import logging
import sys

from django.core.management.base import BaseCommand
from django.db.models import Count
from django.db.models.functions import Length

from apps.api.models import CrossReference, Law, LawVersion

logger = logging.getLogger(__name__)

# AKN namespace used by the V2 parser
NS = {"akn": "http://docs.oasis-open.org/legaldocml/ns/akn/3.0"}

# ES truncation threshold used in index_laws.py raw-text fallback
ES_TEXT_CAP = 50_000

# Field length thresholds
NAME_MAX = 500
NAME_WARN_THRESHOLD = 490

# Sentinel date used by ingestion scripts when no real date is available
SENTINEL_DATE = datetime.date(2023, 1, 1)


PASS = "pass"
FAIL = "fail"
WARNING = "warning"
SKIP = "skip"


class Command(BaseCommand):
    help = "Sample laws and trace data through DB, filesystem, ES, and cross-references"

    def add_arguments(self, parser):
        parser.add_argument(
            "--golden-set",
            action="store_true",
            help="Use 10 curated laws instead of random sampling",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=5,
            help="Laws per tier for random sampling (default: 5)",
        )
        parser.add_argument(
            "--output",
            type=str,
            default="",
            help="Write JSON report to this file path",
        )

    def handle(self, **options):
        if options["golden_set"]:
            laws = self._select_golden_set()
        else:
            laws = self._select_random(options["limit"])

        if not laws:
            self.stderr.write(self.style.ERROR("No laws found to check."))
            return

        es = self._get_es_client()
        checks = []

        for law in laws:
            self.stdout.write(
                self.style.MIGRATE_HEADING(f"\n--- {law.official_id} ---")
            )
            law_checks = self._run_checks(law, es)
            checks.extend(law_checks)

            for c in law_checks:
                style = {
                    PASS: self.style.SUCCESS,
                    FAIL: self.style.ERROR,
                    WARNING: self.style.WARNING,
                    SKIP: self.style.NOTICE,
                }.get(c["status"], self.style.NOTICE)
                self.stdout.write(
                    f"  [{c['status'].upper():7s}] {c['check']}: {c['detail']}"
                    if c["status"] == PASS
                    else style(
                        f"  [{c['status'].upper():7s}] {c['check']}: {c['detail']}"
                    )
                )

        summary = {
            "passed": sum(1 for c in checks if c["status"] == PASS),
            "failed": sum(1 for c in checks if c["status"] == FAIL),
            "warnings": sum(1 for c in checks if c["status"] == WARNING),
            "skipped": sum(1 for c in checks if c["status"] == SKIP),
        }

        report = {
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "laws_sampled": len(laws),
            "checks": checks,
            "summary": summary,
        }

        self.stdout.write("")
        self.stdout.write(self.style.MIGRATE_HEADING("=== Summary ==="))
        self.stdout.write(self.style.SUCCESS(f"  Passed:   {summary['passed']}"))
        self.stdout.write(self.style.ERROR(f"  Failed:   {summary['failed']}"))
        self.stdout.write(self.style.WARNING(f"  Warnings: {summary['warnings']}"))
        self.stdout.write(f"  Skipped:  {summary['skipped']}")

        if options["output"]:
            output_path = options["output"]
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2, ensure_ascii=False, default=str)
            self.stdout.write(self.style.SUCCESS(f"\nReport written to {output_path}"))
        else:
            # Print JSON to stdout as well for piping
            self.stdout.write("")
            self.stdout.write(
                json.dumps(report, indent=2, ensure_ascii=False, default=str)
            )

        if summary["failed"] > 0:
            sys.exit(1)

    # ------------------------------------------------------------------
    # Sampling
    # ------------------------------------------------------------------

    def _select_random(self, limit):
        """Sample `limit` random laws per tier (federal, state, municipal)."""
        laws = []
        for tier_value in ("federal", "state", "municipal"):
            qs = Law.objects.filter(tier=tier_value).order_by("?")[:limit]
            sampled = list(qs)
            self.stdout.write(f"Sampled {len(sampled)} {tier_value} law(s)")
            laws.extend(sampled)
        return laws

    def _select_golden_set(self):
        """Select 10 curated laws by specific criteria."""
        laws = []

        def _add(label, law):
            if law:
                self.stdout.write(f"Golden [{label}]: {law.official_id}")
                laws.append(law)
            else:
                self.stdout.write(
                    self.style.WARNING(f"Golden [{label}]: not found, skipping")
                )

        # 1. CPEUM
        _add("CPEUM", Law.objects.filter(official_id="cpeum").first())

        # 2. A NOM
        nom = (
            Law.objects.filter(tier="federal", category__icontains="nom").first()
            or Law.objects.filter(tier="federal", official_id__icontains="nom").first()
        )
        _add("NOM", nom)

        # 3. A treaty
        treaty = (
            Law.objects.filter(category__icontains="treaty").first()
            or Law.objects.filter(category__icontains="tratado").first()
        )
        _add("Treaty", treaty)

        # 4. A municipal law
        _add("Municipal", Law.objects.filter(tier="municipal").order_by("?").first())

        # 5. Law with sentinel publication_date
        sentinel_version = (
            LawVersion.objects.filter(publication_date=SENTINEL_DATE)
            .select_related("law")
            .first()
        )
        _add(
            "Sentinel date",
            sentinel_version.law if sentinel_version else None,
        )

        # 6. Longest-named law
        longest = (
            Law.objects.annotate(name_len=Length("name")).order_by("-name_len").first()
        )
        _add("Longest name", longest)

        # 7. Law with 0 ES articles (if ES available)
        es = self._get_es_client()
        if es:
            zero_es = self._find_law_with_zero_es_articles(es)
            _add("Zero ES articles", zero_es)
        else:
            self.stdout.write(
                self.style.WARNING(
                    "Golden [Zero ES articles]: ES unavailable, skipping"
                )
            )

        # 8. A state law
        _add("State", Law.objects.filter(tier="state").order_by("?").first())

        # 9. Law with CrossReferences as source
        xref_slug = (
            CrossReference.objects.values_list("source_law_slug", flat=True)
            .distinct()
            .first()
        )
        if xref_slug:
            _add("Has xrefs", Law.objects.filter(official_id=xref_slug).first())
        else:
            _add("Has xrefs", None)

        # 10. Law with xml_file_path set
        version_with_xml = (
            LawVersion.objects.exclude(xml_file_path__isnull=True)
            .exclude(xml_file_path="")
            .select_related("law")
            .order_by("?")
            .first()
        )
        _add(
            "Has XML path",
            version_with_xml.law if version_with_xml else None,
        )

        # Deduplicate while preserving order
        seen = set()
        unique = []
        for law in laws:
            if law.pk not in seen:
                seen.add(law.pk)
                unique.append(law)
        return unique

    def _find_law_with_zero_es_articles(self, es):
        """Find a law that has an xml_file_path but zero ES articles."""
        from apps.api.config import INDEX_NAME

        candidates = (
            LawVersion.objects.exclude(xml_file_path__isnull=True)
            .exclude(xml_file_path="")
            .select_related("law")
            .order_by("?")[:50]
        )
        for version in candidates:
            try:
                resp = es.count(
                    index=INDEX_NAME,
                    body={"query": {"term": {"law_id": version.law.official_id}}},
                )
                if resp.get("count", 0) == 0:
                    return version.law
            except Exception:
                continue

        # Fallback: any law with 0 versions
        law_without_versions = (
            Law.objects.annotate(ver_count=Count("versions"))
            .filter(ver_count=0)
            .first()
        )
        return law_without_versions

    # ------------------------------------------------------------------
    # ES helper
    # ------------------------------------------------------------------

    def _get_es_client(self):
        """Return the singleton ES client if available, else None."""
        try:
            from apps.api.config import es_client

            es_client.info()
            return es_client
        except Exception as exc:
            self.stderr.write(self.style.WARNING(f"Elasticsearch unavailable: {exc}"))
            return None

    # ------------------------------------------------------------------
    # Checks
    # ------------------------------------------------------------------

    def _run_checks(self, law, es):
        """Run all checks for a single law. Returns list of check dicts."""
        results = []

        def _record(check_name, status, detail):
            results.append(
                {
                    "law_id": law.official_id,
                    "check": check_name,
                    "status": status,
                    "detail": detail,
                }
            )

        # Retrieve the latest version for file-based checks
        latest_version = law.versions.first()  # ordered by -publication_date

        # 1. field_lengths
        name_len = len(law.name) if law.name else 0
        if name_len >= NAME_WARN_THRESHOLD:
            _record(
                "field_lengths",
                WARNING,
                f"name length: {name_len}/{NAME_MAX} (near max)",
            )
        else:
            _record("field_lengths", PASS, f"name length: {name_len}/{NAME_MAX}")

        # Get file path and content for subsequent checks
        xml_path = latest_version.xml_file_path if latest_version else None
        resolved_path = None
        content = None

        if xml_path:
            from apps.api.utils.paths import (
                read_data_content,
                resolve_data_path_or_none,
            )

            resolved_path = resolve_data_path_or_none(xml_path)

            # 2. file_existence
            if resolved_path is None:
                _record(
                    "file_existence",
                    FAIL,
                    f"path set ({xml_path}) but file not found on disk",
                )
            else:
                _record(
                    "file_existence",
                    PASS,
                    f"file exists at {resolved_path}",
                )
                content = read_data_content(xml_path)
        else:
            _record("file_existence", SKIP, "no xml_file_path on latest version")

        # 3. text_size
        if content is not None:
            text_len = len(content)
            if text_len > ES_TEXT_CAP:
                _record(
                    "text_size",
                    WARNING,
                    f"{text_len:,} chars (exceeds {ES_TEXT_CAP:,} ES raw-text cap)",
                )
            else:
                _record("text_size", PASS, f"{text_len:,} chars")
        elif xml_path:
            _record("text_size", SKIP, "file could not be read")
        else:
            _record("text_size", SKIP, "no file path")

        # 4. akn_article_count
        if content is not None and self._is_akn_xml(content):
            try:
                article_count = self._count_akn_articles(content)
                _record(
                    "akn_article_count",
                    PASS,
                    f"{article_count} <article> element(s) in AKN XML",
                )
            except Exception as exc:
                _record(
                    "akn_article_count",
                    WARNING,
                    f"XML parse error: {exc}",
                )
        elif content is not None:
            _record("akn_article_count", SKIP, "content is not AKN XML")
        else:
            _record("akn_article_count", SKIP, "no content available")

        # 5. encoding_check
        if content is not None:
            replacement_count = content.count("\ufffd")
            if replacement_count > 0:
                _record(
                    "encoding_check",
                    WARNING,
                    f"found {replacement_count} U+FFFD replacement character(s)",
                )
            else:
                _record("encoding_check", PASS, "no replacement characters")
        else:
            _record("encoding_check", SKIP, "no content available")

        # 6. db_es_article_count
        if es:
            self._check_es_article_count(law, xml_path, es, _record)
        else:
            _record("db_es_article_count", SKIP, "ES unavailable")

        # 7. es_text_sample
        if es:
            self._check_es_text_samples(law, es, _record)
        else:
            _record("es_text_sample", SKIP, "ES unavailable")

        # 8. xref_slug_match
        self._check_xref_slugs(law, _record)

        # 9. date_sentinel
        if latest_version:
            if latest_version.publication_date == SENTINEL_DATE:
                _record(
                    "date_sentinel",
                    WARNING,
                    f"publication_date is sentinel ({SENTINEL_DATE}), likely placeholder",
                )
            else:
                _record(
                    "date_sentinel",
                    PASS,
                    f"publication_date: {latest_version.publication_date}",
                )
        else:
            _record("date_sentinel", SKIP, "no versions found")

        return results

    # ------------------------------------------------------------------
    # Individual check implementations
    # ------------------------------------------------------------------

    @staticmethod
    def _is_akn_xml(content):
        """Return True if content looks like AKN XML."""
        # Check the first 500 chars to avoid scanning huge files
        head = content[:500]
        return head.lstrip().startswith("<?xml") or "<akomaNtoso" in head

    @staticmethod
    def _count_akn_articles(content):
        """Parse AKN XML and count <article> elements."""
        from lxml import etree

        tree = etree.fromstring(content.encode("utf-8"))
        articles = tree.xpath("//akn:article", namespaces=NS)
        return len(articles)

    def _check_es_article_count(self, law, xml_path, es, _record):
        """Compare ES article count with expectations."""
        from apps.api.config import INDEX_NAME

        try:
            resp = es.count(
                index=INDEX_NAME,
                body={"query": {"term": {"law_id": law.official_id}}},
            )
            es_count = resp.get("count", 0)
        except Exception as exc:
            _record("db_es_article_count", SKIP, f"ES query failed: {exc}")
            return

        if es_count == 0 and xml_path:
            _record(
                "db_es_article_count",
                WARNING,
                f"0 ES articles but xml_file_path is set ({xml_path})",
            )
        elif es_count == 0:
            _record(
                "db_es_article_count",
                PASS,
                "0 ES articles (no xml_file_path, expected)",
            )
        else:
            _record(
                "db_es_article_count",
                PASS,
                f"{es_count:,} article(s) in ES",
            )

    def _check_es_text_samples(self, law, es, _record):
        """Sample up to 3 ES articles and check text quality."""
        from apps.api.config import INDEX_NAME

        try:
            resp = es.search(
                index=INDEX_NAME,
                body={
                    "query": {"term": {"law_id": law.official_id}},
                    "size": 3,
                    "_source": ["text", "article_id"],
                },
            )
        except Exception as exc:
            _record("es_text_sample", SKIP, f"ES query failed: {exc}")
            return

        hits = resp.get("hits", {}).get("hits", [])
        if not hits:
            _record("es_text_sample", SKIP, "no ES articles to sample")
            return

        issues = []
        for hit in hits:
            src = hit.get("_source", {})
            text = src.get("text", "")
            article_id = src.get("article_id", "?")

            if not text:
                issues.append(f"{article_id}: empty text")
            elif text.rstrip().endswith("\ufffd"):
                issues.append(f"{article_id}: text ends with U+FFFD")

        if issues:
            _record(
                "es_text_sample",
                WARNING,
                f"{len(issues)} issue(s): {'; '.join(issues)}",
            )
        else:
            _record(
                "es_text_sample",
                PASS,
                f"sampled {len(hits)} article(s), text looks clean",
            )

    def _check_xref_slugs(self, law, _record):
        """Check that cross-reference target slugs resolve to real laws."""
        xrefs = CrossReference.objects.filter(source_law_slug=law.official_id)
        total = xrefs.count()

        if total == 0:
            _record("xref_slug_match", SKIP, "no cross-references as source")
            return

        target_slugs = set(
            xrefs.exclude(target_law_slug__isnull=True)
            .exclude(target_law_slug="")
            .values_list("target_law_slug", flat=True)
            .distinct()
        )

        if not target_slugs:
            _record(
                "xref_slug_match",
                PASS,
                f"{total} xref(s), none with target_law_slug to resolve",
            )
            return

        existing_slugs = set(
            Law.objects.filter(official_id__in=target_slugs).values_list(
                "official_id", flat=True
            )
        )
        unresolved = target_slugs - existing_slugs

        if unresolved:
            sample = sorted(unresolved)[:5]
            _record(
                "xref_slug_match",
                WARNING,
                f"{len(unresolved)}/{len(target_slugs)} target slug(s) unresolved "
                f"(e.g. {', '.join(sample)})",
            )
        else:
            _record(
                "xref_slug_match",
                PASS,
                f"all {len(target_slugs)} target slug(s) resolve to existing laws",
            )
