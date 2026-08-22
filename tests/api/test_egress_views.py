"""Tests for tenant/user data egress (self-service account takeout).

Covers:
  - Envelope shape and contract version (GET /user/export/)
  - Completeness: every per-user collection is present
  - Cross-tenant isolation: a caller never sees another account's rows
  - API-key principals resolve to the linked Janua subject, not "apikey:..."
  - Unlinked API keys are refused rather than exporting a bogus scope
  - Anonymous access is refused
  - Download variant returns a JSON attachment
  - Secrets are redacted and exclusions are declared
"""

import json
from unittest.mock import patch

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.api.egress_views import CONTRACT
from apps.api.middleware.apikey_auth import APIKeyUser
from apps.api.middleware.janua_auth import JanuaUser
from apps.api.models import (
    Annotation,
    APIKey,
    APIUsageLog,
    ExportLog,
    FeatureInterest,
    NewsletterSubscription,
    Notification,
    UserAlert,
    UserPreference,
    WebhookSubscription,
)

AUTH_PATCH = "apps.api.middleware.combined_auth.CombinedAuthentication.authenticate"

MINE = "user-mine"
THEIRS = "user-theirs"


def _make_user(user_id=MINE, tier="academic"):
    user = JanuaUser({"sub": user_id, "email": f"{user_id}@test.com", "tier": tier})
    user.tier = tier
    user.scopes = ["read", "search"]
    user.allowed_domains = []
    user.api_key_prefix = ""
    return user


def _make_key(prefix, janua_user_id, **kwargs):
    defaults = {
        "hashed_key": f"hash-{prefix}",
        "name": f"Key {prefix}",
        "owner_email": f"{janua_user_id}@test.com",
        "tier": "academic",
        "scopes": ["read", "search"],
        "is_active": True,
    }
    defaults.update(kwargs)
    return APIKey.objects.create(prefix=prefix, janua_user_id=janua_user_id, **defaults)


def _seed_account(janua_user_id, marker):
    """Create one row in every per-user table, tagged with ``marker``."""
    key = _make_key(f"{marker}key01"[:8], janua_user_id, organization=f"Org {marker}")

    Annotation.objects.create(
        janua_user_id=janua_user_id,
        law_id=f"law-{marker}",
        article_id="art-1",
        text=f"note-{marker}",
    )
    UserAlert.objects.create(
        janua_user_id=janua_user_id,
        law_id=f"law-{marker}",
        alert_type="law_updated",
    )
    Notification.objects.create(
        janua_user_id=janua_user_id,
        title=f"notif-{marker}",
        body=f"body-{marker}",
    )
    NewsletterSubscription.objects.create(
        email=f"{marker}@news.test",
        janua_user_id=janua_user_id,
        topics=["federal"],
    )
    FeatureInterest.objects.create(
        email=f"{marker}@interest.test",
        janua_user_id=janua_user_id,
        feature_key="webhooks",
        wishlist=f"wish-{marker}",
    )
    WebhookSubscription.objects.create(
        api_key=key,
        url=f"https://{marker}.example.test/hook",
        events=["law.updated"],
        secret=f"supersecret-{marker}",
    )
    UserPreference.objects.create(
        janua_user_id=janua_user_id,
        bookmarks=[f"bm-{marker}"],
        recently_viewed=[f"rv-{marker}"],
        preferences={"theme": marker},
    )
    ExportLog.objects.create(
        user_id=janua_user_id,
        ip_address="10.0.0.1",
        law_id=f"law-{marker}",
        format="pdf",
        tier="academic",
    )
    APIUsageLog.objects.create(
        api_key_prefix=key.prefix,
        ip_address="10.0.0.1",
        endpoint=f"/api/v1/{marker}/",
        status_code=200,
    )
    return key


@pytest.mark.django_db
class TestEgressEnvelope:
    """Shape and completeness of GET /user/export/."""

    def setup_method(self):
        self.client = APIClient()
        self.url = reverse("user-export")

    @patch(AUTH_PATCH)
    def test_envelope_contract_and_timestamp(self, mock_auth):
        """Envelope carries the versioned contract and an ISO timestamp."""
        mock_auth.return_value = (_make_user(), "fake-token")
        response = self.client.get(self.url)

        assert response.status_code == 200
        data = response.json()
        assert data["contract"] == CONTRACT == "tezca-egress/v1"
        assert data["exportedAt"]
        assert data["subject"]["janua_user_id"] == MINE
        assert data["subject"]["requested_via"] == "janua_jwt"

    @patch(AUTH_PATCH)
    def test_empty_account_still_exports(self, mock_auth):
        """An account with no artifacts gets a complete, empty envelope."""
        mock_auth.return_value = (_make_user(), "fake-token")
        data = self.client.get(self.url).json()

        assert data["preferences"] is None
        assert data["counts"] == {
            "alerts": 0,
            "annotations": 0,
            "api_keys": 0,
            "feature_interests": 0,
            "newsletter_subscriptions": 0,
            "notifications": 0,
            "webhook_subscriptions": 0,
        }
        assert data["usage"]["api_calls"]["total"] == 0
        assert data["usage"]["law_exports"]["total"] == 0

    @patch(AUTH_PATCH)
    def test_exports_every_collection(self, mock_auth):
        """Every per-user table Tezca stores appears in the export."""
        _seed_account(MINE, "aa")
        mock_auth.return_value = (_make_user(), "fake-token")
        data = self.client.get(self.url).json()

        collections = data["collections"]
        assert len(collections["api_keys"]) == 1
        assert len(collections["annotations"]) == 1
        assert len(collections["alerts"]) == 1
        assert len(collections["notifications"]) == 1
        assert len(collections["newsletter_subscriptions"]) == 1
        assert len(collections["feature_interests"]) == 1
        assert len(collections["webhook_subscriptions"]) == 1

        assert collections["annotations"][0]["text"] == "note-aa"
        assert collections["notifications"][0]["title"] == "notif-aa"
        assert data["preferences"]["bookmarks"] == ["bm-aa"]
        assert data["preferences"]["preferences"] == {"theme": "aa"}

    @patch(AUTH_PATCH)
    def test_account_and_entitlement_facts(self, mock_auth):
        """Account block reports tier, org, emails, and key counts."""
        _make_key("entkey01", MINE, tier="institutional", organization="ACME")
        _make_key("entkey02", MINE, tier="academic", is_active=False)
        mock_auth.return_value = (_make_user(), "fake-token")
        account = self.client.get(self.url).json()["account"]

        assert account["janua_user_id"] == MINE
        assert account["current_tier"] == "institutional"
        assert account["organizations"] == ["ACME"]
        assert account["emails"] == [f"{MINE}@test.com"]
        assert account["api_key_count"] == 2
        assert account["active_api_key_count"] == 1
        assert account["active_trial"] is None

    @patch(AUTH_PATCH)
    def test_active_trial_is_reported(self, mock_auth):
        """A live trial surfaces as the current entitlement."""
        now = timezone.now()
        _make_key(
            "trialk01",
            MINE,
            tier="essentials",
            trial_tier="institutional",
            trial_started_at=now,
            trial_ends_at=now + timezone.timedelta(days=7),
            trial_cc_provided=True,
        )
        mock_auth.return_value = (_make_user(), "fake-token")
        account = self.client.get(self.url).json()["account"]

        assert account["current_tier"] == "institutional"
        assert account["active_trial"]["tier"] == "institutional"
        assert account["active_trial"]["credit_card_provided"] is True

    @patch(AUTH_PATCH)
    def test_usage_summaries(self, mock_auth):
        """Usage is summarized per format and per endpoint."""
        _seed_account(MINE, "bb")
        mock_auth.return_value = (_make_user(), "fake-token")
        usage = self.client.get(self.url).json()["usage"]

        assert usage["law_exports"]["total"] == 1
        assert usage["law_exports"]["by_format"] == {"pdf": 1}
        assert usage["law_exports"]["first_at"]
        assert usage["api_calls"]["total"] == 1
        assert usage["api_calls"]["by_endpoint"] == {"/api/v1/bb/": 1}

    @patch(AUTH_PATCH)
    def test_webhook_secret_is_redacted(self, mock_auth):
        """Signing secrets never leave the system, but their presence is stated."""
        _seed_account(MINE, "cc")
        mock_auth.return_value = (_make_user(), "fake-token")
        body = self.client.get(self.url).content.decode()

        assert "supersecret-cc" not in body
        hook = json.loads(body)["collections"]["webhook_subscriptions"][0]
        assert hook["secret"] == "[redacted]"
        assert hook["has_secret"] is True

    @patch(AUTH_PATCH)
    def test_declares_law_corpus_exclusion(self, mock_auth):
        """The envelope states that the public law corpus is not Tezca's to export."""
        mock_auth.return_value = (_make_user(), "fake-token")
        excluded = self.client.get(self.url).json()["excluded"]

        keys = {item["what"] for item in excluded}
        assert "law_corpus" in keys
        assert "billing_records" in keys
        assert "identity_profile" in keys
        assert all(item["reason"] for item in excluded)

        corpus = next(i for i in excluded if i["what"] == "law_corpus")
        assert "does not own" in corpus["reason"]

    @patch(AUTH_PATCH)
    def test_truncation_is_declared_not_silent(self, mock_auth):
        """Over-cap collections report their true total rather than lying."""
        Annotation.objects.bulk_create(
            Annotation(
                janua_user_id=MINE,
                law_id="law-x",
                article_id=f"art-{i}",
                text=f"n{i}",
            )
            for i in range(5)
        )
        mock_auth.return_value = (_make_user(), "fake-token")

        with patch("apps.api.egress_views.MAX_ROWS_PER_COLLECTION", 2):
            data = self.client.get(self.url).json()

        assert len(data["collections"]["annotations"]) == 2
        assert {
            "collection": "annotations",
            "exported": 2,
            "total": 5,
        } in data["truncated"]


@pytest.mark.django_db
class TestEgressTenantIsolation:
    """No cross-tenant reads. This is the load-bearing guarantee of C6."""

    def setup_method(self):
        self.client = APIClient()
        self.url = reverse("user-export")

    @patch(AUTH_PATCH)
    def test_never_returns_another_accounts_rows(self, mock_auth):
        """With two fully-populated accounts, only the caller's data comes back."""
        _seed_account(MINE, "mm")
        _seed_account(THEIRS, "tt")

        mock_auth.return_value = (_make_user(MINE), "fake-token")
        response = self.client.get(self.url)
        assert response.status_code == 200
        body = response.content.decode()
        data = response.json()

        # Not one byte of the other tenant's data appears anywhere. The marker
        # is matched inside real values ("note-tt", "ttkey01") rather than as a
        # bare two-letter substring, which would collide with ".test" and
        # "attachment" and make the assertion meaningless.
        assert THEIRS not in body
        for leaked in (
            "note-tt",
            "ttkey01",
            "notif-tt",
            "wish-tt",
            "bm-tt",
            "tt@news.test",
            "https://tt.example.test/hook",
            "/api/v1/tt/",
        ):
            assert leaked not in body

        assert data["subject"]["janua_user_id"] == MINE
        assert data["counts"]["annotations"] == 1
        assert data["collections"]["annotations"][0]["text"] == "note-mm"
        assert data["collections"]["api_keys"][0]["prefix"] == "mmkey01"
        assert data["preferences"]["bookmarks"] == ["bm-mm"]
        assert data["usage"]["api_calls"]["by_endpoint"] == {"/api/v1/mm/": 1}

    @patch(AUTH_PATCH)
    def test_isolation_holds_in_both_directions(self, mock_auth):
        """The other tenant likewise sees only their own rows."""
        _seed_account(MINE, "mm")
        _seed_account(THEIRS, "tt")

        mock_auth.return_value = (_make_user(THEIRS), "fake-token")
        data = self.client.get(self.url).json()

        assert data["subject"]["janua_user_id"] == THEIRS
        assert data["collections"]["annotations"][0]["text"] == "note-tt"
        assert data["collections"]["api_keys"][0]["prefix"] == "ttkey01"
        assert data["usage"]["api_calls"]["by_endpoint"] == {"/api/v1/tt/": 1}

    @patch(AUTH_PATCH)
    def test_webhooks_of_other_tenants_keys_excluded(self, mock_auth):
        """Webhooks hang off API keys — the key ownership filter must hold."""
        _seed_account(MINE, "mm")
        theirs_key = _seed_account(THEIRS, "tt")
        WebhookSubscription.objects.create(
            api_key=theirs_key,
            url="https://leak.example.test/hook",
            events=["law.created"],
            secret="nope",
        )

        mock_auth.return_value = (_make_user(MINE), "fake-token")
        data = self.client.get(self.url).json()

        urls = [w["url"] for w in data["collections"]["webhook_subscriptions"]]
        assert urls == ["https://mm.example.test/hook"]

    @patch(AUTH_PATCH)
    def test_usage_logs_of_other_tenants_keys_excluded(self, mock_auth):
        """Usage rows are keyed by API-key prefix; only owned prefixes count."""
        _seed_account(MINE, "mm")
        _seed_account(THEIRS, "tt")
        APIUsageLog.objects.create(
            api_key_prefix="ttkey01",
            ip_address="10.0.0.9",
            endpoint="/api/v1/secret/",
            status_code=200,
        )

        mock_auth.return_value = (_make_user(MINE), "fake-token")
        usage = self.client.get(self.url).json()["usage"]["api_calls"]

        assert usage["total"] == 1
        assert "/api/v1/secret/" not in usage["by_endpoint"]
        assert usage["api_key_prefixes"] == ["mmkey01"]


@pytest.mark.django_db
class TestEgressAuth:
    """Principal resolution across the two authenticated shapes."""

    def setup_method(self):
        self.client = APIClient()
        self.url = reverse("user-export")

    def test_anonymous_is_refused(self):
        """No auth → 401, no data."""
        response = self.client.get(self.url)
        assert response.status_code == 401
        assert "collections" not in response.json()

    @patch(AUTH_PATCH)
    def test_api_key_principal_resolves_to_linked_subject(self, mock_auth):
        """An API-key caller exports the account the key is linked to."""
        _seed_account(MINE, "mm")
        _seed_account(THEIRS, "tt")
        key = APIKey.objects.get(prefix="mmkey01")

        mock_auth.return_value = (APIKeyUser(key), "fake-token")
        data = self.client.get(self.url).json()

        # Not the literal "apikey:mmkey01" string.
        assert data["subject"]["janua_user_id"] == MINE
        assert data["subject"]["requested_via"] == "api_key"
        assert data["subject"]["requesting_api_key_prefix"] == "mmkey01"
        assert data["collections"]["annotations"][0]["text"] == "note-mm"
        assert THEIRS not in self.client.get(self.url).content.decode()

    @patch(AUTH_PATCH)
    def test_unlinked_api_key_is_refused(self, mock_auth):
        """A key with no Janua link has no account scope — refuse, don't guess."""
        key = _make_key("orphan01", "")
        mock_auth.return_value = (APIKeyUser(key), "fake-token")

        response = self.client.get(self.url)
        assert response.status_code == 403
        assert "not linked" in response.json()["error"]


@pytest.mark.django_db
class TestEgressDownload:
    """GET /user/export/download/ serves the same envelope as a file."""

    def setup_method(self):
        self.client = APIClient()
        self.url = reverse("user-export-download")

    @patch(AUTH_PATCH)
    def test_returns_json_attachment(self, mock_auth):
        """Response is a downloadable JSON file, not cached."""
        _seed_account(MINE, "dd")
        mock_auth.return_value = (_make_user(), "fake-token")
        response = self.client.get(self.url)

        assert response.status_code == 200
        assert response["Content-Type"] == "application/json; charset=utf-8"
        assert "attachment;" in response["Content-Disposition"]
        assert "tezca-export-" in response["Content-Disposition"]
        assert response["Content-Disposition"].endswith('.json"')
        assert response["Cache-Control"] == "no-store"

    @patch(AUTH_PATCH)
    def test_body_is_the_same_envelope(self, mock_auth):
        """The download parses as the contract envelope."""
        _seed_account(MINE, "ee")
        mock_auth.return_value = (_make_user(), "fake-token")
        payload = json.loads(self.client.get(self.url).content)

        assert payload["contract"] == "tezca-egress/v1"
        assert payload["subject"]["janua_user_id"] == MINE
        assert payload["collections"]["annotations"][0]["text"] == "note-ee"
        assert payload["excluded"]

    @patch(AUTH_PATCH)
    def test_download_is_tenant_scoped(self, mock_auth):
        """The file variant enforces the same isolation as the JSON variant."""
        _seed_account(MINE, "mm")
        _seed_account(THEIRS, "tt")
        mock_auth.return_value = (_make_user(MINE), "fake-token")

        body = self.client.get(self.url).content.decode()
        assert THEIRS not in body
        for leaked in (
            "note-tt",
            "ttkey01",
            "notif-tt",
            "https://tt.example.test/hook",
        ):
            assert leaked not in body
        assert "note-mm" in body

    def test_anonymous_download_is_refused(self):
        """No auth → 401 on the download variant too."""
        assert self.client.get(self.url).status_code == 401
