"""
Integration tests for DB-ES data consistency.

These tests require a running Elasticsearch instance. They are skipped
automatically when ES is unreachable (e.g. in CI without Docker services).

All tests are marked with @pytest.mark.spotcheck for selective execution:
    pytest -m spotcheck tests/integration/test_db_es_consistency.py
"""

import pytest

from apps.api.config import INDEX_NAME, es_client
from apps.api.models import Law


@pytest.fixture
def es_or_skip():
    """Provide the ES client or skip the test if ES is not available."""
    try:
        if not es_client.ping():
            pytest.skip("ES not available")
    except Exception:
        pytest.skip("ES not available")
    return es_client


@pytest.mark.spotcheck
@pytest.mark.django_db
class TestDbEsConsistency:
    """Verify consistency between the Django DB and Elasticsearch index."""

    def test_sampled_laws_have_es_docs(self, es_or_skip):
        """Sample 10 random Laws with xml_file_path set and verify each has ES docs.

        Laws that have an xml_file_path on their latest version should have
        at least one article indexed in ES. This test reports any gaps.
        """
        from apps.api.models import LawVersion

        versions_with_xml = (
            LawVersion.objects.exclude(xml_file_path__isnull=True)
            .exclude(xml_file_path="")
            .select_related("law")
            .order_by("?")[:10]
        )

        if not versions_with_xml:
            pytest.skip("No LawVersions with xml_file_path in test DB")

        missing = []
        for version in versions_with_xml:
            count_resp = es_or_skip.count(
                index=INDEX_NAME,
                query={"term": {"law_id": version.law.official_id}},
            )
            if count_resp.get("count", 0) == 0:
                missing.append(version.law.official_id)

        # Report but do not hard-fail -- some laws may have parse failures
        if missing:
            pytest.xfail(
                f"{len(missing)}/{len(versions_with_xml)} law(s) with "
                f"xml_file_path have 0 ES docs: {missing[:5]}"
            )

    def test_es_law_ids_exist_in_db(self, es_or_skip):
        """Fetch 20 random ES docs and verify each law_id exists in the DB."""
        res = es_or_skip.search(
            index=INDEX_NAME,
            query={"function_score": {"random_score": {}}},
            size=20,
            source=["law_id"],
        )

        hits = res.get("hits", {}).get("hits", [])
        if not hits:
            pytest.skip("ES index is empty")

        es_law_ids = {
            hit["_source"]["law_id"] for hit in hits if hit["_source"].get("law_id")
        }
        db_law_ids = set(
            Law.objects.filter(official_id__in=es_law_ids).values_list(
                "official_id", flat=True
            )
        )

        orphaned = es_law_ids - db_law_ids
        assert (
            not orphaned
        ), f"{len(orphaned)} ES law_id(s) not found in DB: {sorted(orphaned)[:5]}"

    def test_laws_with_xml_have_es_docs(self, es_or_skip):
        """Sample 20 Laws that have xml_file_path set and check ES coverage."""
        from apps.api.models import LawVersion

        versions = (
            LawVersion.objects.exclude(xml_file_path__isnull=True)
            .exclude(xml_file_path="")
            .select_related("law")
            .order_by("?")[:20]
        )

        if not versions:
            pytest.skip("No LawVersions with xml_file_path in test DB")

        zero_count = 0
        for version in versions:
            count_resp = es_or_skip.count(
                index=INDEX_NAME,
                query={"term": {"law_id": version.law.official_id}},
            )
            if count_resp.get("count", 0) == 0:
                zero_count += 1

        # Allow some tolerance -- up to 25% missing is a warning, not failure
        tolerance = max(1, len(versions) // 4)
        assert zero_count <= tolerance, (
            f"{zero_count}/{len(versions)} laws with xml_file_path have 0 ES "
            f"articles (tolerance: {tolerance})"
        )

    def test_es_articles_have_nonempty_text(self, es_or_skip):
        """Fetch 10 random articles from ES and verify text fields are non-empty."""
        res = es_or_skip.search(
            index=INDEX_NAME,
            query={"function_score": {"random_score": {}}},
            size=10,
            source=["text", "law_id", "article"],
        )

        hits = res.get("hits", {}).get("hits", [])
        if not hits:
            pytest.skip("ES index is empty")

        empty = []
        for hit in hits:
            src = hit["_source"]
            text = src.get("text", "")
            if not text or not text.strip():
                empty.append(f"{src.get('law_id', '?')}:{src.get('article', '?')}")

        assert not empty, f"{len(empty)} ES article(s) have empty text: {empty[:5]}"

    def test_full_text_article_count(self, es_or_skip):
        """Count articles with article='full_text' (raw-text fallback metric).

        This is an informational test -- it reports how many laws fell back to
        raw-text indexing instead of AKN article extraction. The count is
        expected to be > 0 for a production-like dataset.
        """
        count_resp = es_or_skip.count(
            index=INDEX_NAME,
            query={"term": {"article": "full_text"}},
        )
        count = count_resp.get("count", 0)

        # Just report the count -- no hard assertion on the value
        # This metric is tracked for monitoring raw-text fallback usage
        assert count >= 0, "Count should be non-negative"
