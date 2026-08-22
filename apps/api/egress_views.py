"""
Tenant/user data egress — self-service account takeout.

GET /api/v1/user/export/          → JSON envelope (inline)
GET /api/v1/user/export/download/ → same envelope as an attachment

Emits the ``tezca-egress/v1`` contract: every row Tezca stores that belongs to
the requesting principal, complete and re-usable, so a customer can leave
without an operator in the loop (self-serve-sellable criterion C6).

Scope rule: the export is keyed on the caller's Janua subject
(``janua_user_id``). Nothing outside that key is ever read. The public law
corpus is deliberately excluded — Tezca does not own it (see EXCLUDED).
"""

import json
import logging

from django.http import HttpResponse
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import (
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

logger = logging.getLogger(__name__)

CONTRACT = "tezca-egress/v1"

#: Row cap per collection. Usage logs are unbounded over an account's lifetime;
#: everything else is naturally small. Truncation is always reported in the
#: envelope so the export never silently lies about being complete.
MAX_ROWS_PER_COLLECTION = 10_000

#: What this export deliberately does NOT contain, and why. Surfaced in the
#: envelope so a reader never has to guess whether an absence is a bug.
EXCLUDED = [
    {
        "what": "law_corpus",
        "reason": (
            "Mexican legislation, judicial records (SCJN jurisprudencia and "
            "tesis), and their versions are public-domain primary sources that "
            "Tezca republishes but does not own. They are not your data. Fetch "
            "them from the public API (/api/v1/laws/, /api/v1/judicial/) or "
            "export a single law via /api/v1/laws/{id}/export/{format}/."
        ),
    },
    {
        "what": "search_analytics",
        "reason": (
            "Search queries are recorded against a hashed session identifier, "
            "not against your account, so they cannot be attributed to you and "
            "are not exportable as your data."
        ),
    },
    {
        "what": "api_key_secrets",
        "reason": (
            "Only irreversible hashes of API keys are stored. Key prefixes and "
            "metadata are included; the secret values are not recoverable and "
            "are not present in this export."
        ),
    },
    {
        "what": "webhook_signing_secrets",
        "reason": (
            "Webhook HMAC secrets are credentials, not user content. Their "
            "presence is reported; the values are redacted."
        ),
    },
    {
        "what": "billing_records",
        "reason": (
            "Invoices, payment methods, and CFDI documents live in Dhanam, the "
            "billing system of record. Export them from your Dhanam account."
        ),
    },
    {
        "what": "identity_profile",
        "reason": (
            "Name, email, password, and session history live in Janua, the "
            "identity provider. Export them from your Janua account."
        ),
    },
]


def _resolve_principal(request):
    """
    Resolve the requesting principal to a Janua subject.

    Returns ``(janua_user_id, api_key_prefix)``. ``janua_user_id`` is ``None``
    when the request cannot be attributed to an account.

    Two authenticated shapes reach this view (see middleware/combined_auth.py):

    * **Janua JWT** — ``request.user.id`` is the ``sub`` claim. That *is* the
      scope key.
    * **API key** — ``request.user.id`` is the synthetic string
      ``"apikey:<prefix>"``, which is NOT a Janua subject. The real subject
      must be read off the ``APIKey`` row, and a key that was never linked to
      an account (``janua_user_id == ""``) has no account to export.

    Conflating those two would let an API-key caller export under a literal
    ``"apikey:..."`` key, so the branch is explicit here rather than reusing
    ``preference_views._get_user_id``.
    """
    user = getattr(request, "user", None)
    if not user or not getattr(user, "is_authenticated", False):
        # Fall back to raw claims when a bare auth dict is present.
        auth = getattr(request, "auth", None)
        if isinstance(auth, dict):
            sub = auth.get("sub") or auth.get("user_id")
            return (sub or None), ""
        return None, ""

    prefix = getattr(user, "api_key_prefix", "") or ""
    raw_id = getattr(user, "id", None) or ""

    if prefix or str(raw_id).startswith("apikey:"):
        prefix = prefix or str(raw_id).split(":", 1)[1]
        key = APIKey.objects.filter(prefix=prefix).first()
        linked = (key.janua_user_id or "").strip() if key else ""
        return (linked or None), prefix

    return (str(raw_id) or None), ""


def _rows(queryset, mapper):
    """Materialize a capped, mapped list plus its truncation flag."""
    total = queryset.count()
    rows = [mapper(obj) for obj in queryset[:MAX_ROWS_PER_COLLECTION]]
    return rows, total


def _iso(value):
    return value.isoformat() if value else None


def _collect(janua_user_id, api_key_prefix):
    """
    Build the full ``tezca-egress/v1`` payload for one Janua subject.

    Every queryset below is filtered on ``janua_user_id`` (or, for rows Tezca
    keys by API key rather than by subject, on keys owned by that subject).
    There is no unfiltered read anywhere in this function.
    """
    now = timezone.now()

    # ── Account + entitlement facts ────────────────────────────────────
    keys_qs = APIKey.objects.filter(janua_user_id=janua_user_id).order_by("created_at")
    owned_keys = list(keys_qs)
    owned_prefixes = [k.prefix for k in owned_keys]

    active_keys = [k for k in owned_keys if k.is_active]
    # Highest-signal tier the account currently holds, preferring a live trial.
    current_tier = ""
    trial = None
    for key in active_keys:
        if key.trial_tier and key.trial_ends_at and key.trial_ends_at > now:
            trial = {
                "tier": key.trial_tier,
                "started_at": _iso(key.trial_started_at),
                "ends_at": _iso(key.trial_ends_at),
                "credit_card_provided": key.trial_cc_provided,
                "api_key_prefix": key.prefix,
            }
            current_tier = key.trial_tier
            break
    if not current_tier and active_keys:
        current_tier = active_keys[0].tier

    account = {
        "janua_user_id": janua_user_id,
        "emails": sorted({k.owner_email for k in owned_keys if k.owner_email}),
        "organizations": sorted({k.organization for k in owned_keys if k.organization}),
        "current_tier": current_tier,
        "active_trial": trial,
        "api_key_count": len(owned_keys),
        "active_api_key_count": len(active_keys),
    }

    # ── Collections (user-generated artifacts) ─────────────────────────
    collections = {}
    truncated = []

    def add(name, queryset, mapper):
        rows, total = _rows(queryset, mapper)
        collections[name] = rows
        if total > len(rows):
            truncated.append(
                {"collection": name, "exported": len(rows), "total": total}
            )

    add(
        "api_keys",
        keys_qs,
        lambda k: {
            "prefix": k.prefix,
            "name": k.name,
            "owner_email": k.owner_email,
            "organization": k.organization,
            "tier": k.tier,
            "scopes": k.scopes,
            "allowed_domains": k.allowed_domains,
            "is_active": k.is_active,
            "rate_limit_per_hour": k.rate_limit_per_hour,
            "trial_tier": k.trial_tier,
            "trial_started_at": _iso(k.trial_started_at),
            "trial_ends_at": _iso(k.trial_ends_at),
            "trial_cc_provided": k.trial_cc_provided,
            "created_at": _iso(k.created_at),
            "expires_at": _iso(k.expires_at),
            "last_used_at": _iso(k.last_used_at),
        },
    )

    add(
        "annotations",
        Annotation.objects.filter(janua_user_id=janua_user_id).order_by("created_at"),
        lambda a: {
            "id": a.id,
            "law_id": a.law_id,
            "article_id": a.article_id,
            "text": a.text,
            "highlight_start": a.highlight_start,
            "highlight_end": a.highlight_end,
            "color": a.color,
            "created_at": _iso(a.created_at),
            "updated_at": _iso(a.updated_at),
        },
    )

    add(
        "alerts",
        UserAlert.objects.filter(janua_user_id=janua_user_id).order_by("created_at"),
        lambda a: {
            "id": a.id,
            "law_id": a.law_id,
            "category": a.category,
            "state": a.state,
            "alert_type": a.alert_type,
            "delivery": a.delivery,
            "is_active": a.is_active,
            "created_at": _iso(a.created_at),
        },
    )

    add(
        "notifications",
        Notification.objects.filter(janua_user_id=janua_user_id).order_by("created_at"),
        lambda n: {
            "id": n.id,
            "title": n.title,
            "body": n.body,
            "link": n.link,
            "is_read": n.is_read,
            "created_at": _iso(n.created_at),
        },
    )

    add(
        "newsletter_subscriptions",
        NewsletterSubscription.objects.filter(janua_user_id=janua_user_id).order_by(
            "created_at"
        ),
        lambda s: {
            "email": s.email,
            "topics": s.topics,
            "is_active": s.is_active,
            "created_at": _iso(s.created_at),
            "unsubscribed_at": _iso(s.unsubscribed_at),
        },
    )

    add(
        "feature_interests",
        FeatureInterest.objects.filter(janua_user_id=janua_user_id).order_by(
            "created_at"
        ),
        lambda f: {
            "email": f.email,
            "feature_key": f.feature_key,
            "use_case": f.use_case,
            "source_page": f.source_page,
            "wishlist": f.wishlist,
            "created_at": _iso(f.created_at),
        },
    )

    add(
        "webhook_subscriptions",
        WebhookSubscription.objects.filter(api_key__in=owned_keys).order_by(
            "created_at"
        ),
        lambda w: {
            "id": w.id,
            "api_key_prefix": w.api_key.prefix,
            "url": w.url,
            "events": w.events,
            "domain_filter": w.domain_filter,
            "law_id_filter": w.law_id_filter,
            # Credential, not content — see EXCLUDED.
            "secret": "[redacted]",
            "has_secret": bool(w.secret),
            "is_active": w.is_active,
            "created_at": _iso(w.created_at),
            "last_triggered_at": _iso(w.last_triggered_at),
            "failure_count": w.failure_count,
        },
    )

    # ── Preferences (single row, not a collection) ─────────────────────
    pref = UserPreference.objects.filter(janua_user_id=janua_user_id).first()
    preferences = (
        {
            "bookmarks": pref.bookmarks,
            "recently_viewed": pref.recently_viewed,
            "preferences": pref.preferences,
            "created_at": _iso(pref.created_at),
            "updated_at": _iso(pref.updated_at),
        }
        if pref
        else None
    )

    # ── Usage summaries (aggregates, not raw request logs) ─────────────
    export_logs = ExportLog.objects.filter(user_id=janua_user_id)
    export_by_format = {}
    for row in export_logs.values_list("format", flat=True):
        export_by_format[row] = export_by_format.get(row, 0) + 1
    first_export = export_logs.order_by("created_at").first()
    last_export = export_logs.order_by("-created_at").first()

    api_logs = (
        APIUsageLog.objects.filter(api_key_prefix__in=owned_prefixes)
        if owned_prefixes
        else APIUsageLog.objects.none()
    )
    api_by_endpoint = {}
    for row in api_logs.values_list("endpoint", flat=True):
        api_by_endpoint[row] = api_by_endpoint.get(row, 0) + 1
    first_call = api_logs.order_by("created_at").first()
    last_call = api_logs.order_by("-created_at").first()

    usage = {
        "law_exports": {
            "total": export_logs.count(),
            "by_format": dict(sorted(export_by_format.items())),
            "first_at": _iso(first_export.created_at) if first_export else None,
            "last_at": _iso(last_export.created_at) if last_export else None,
        },
        "api_calls": {
            "total": api_logs.count(),
            "by_endpoint": dict(
                sorted(api_by_endpoint.items(), key=lambda kv: (-kv[1], kv[0]))
            ),
            "api_key_prefixes": owned_prefixes,
            "first_at": _iso(first_call.created_at) if first_call else None,
            "last_at": _iso(last_call.created_at) if last_call else None,
        },
    }

    return {
        "contract": CONTRACT,
        "exportedAt": now.isoformat(),
        "subject": {
            "janua_user_id": janua_user_id,
            "requested_via": "api_key" if api_key_prefix else "janua_jwt",
            "requesting_api_key_prefix": api_key_prefix,
        },
        "account": account,
        "preferences": preferences,
        "collections": collections,
        "usage": usage,
        "counts": {name: len(rows) for name, rows in sorted(collections.items())},
        "truncated": truncated,
        "excluded": EXCLUDED,
    }


@api_view(["GET"])
def user_export(request):
    """Return the caller's complete ``tezca-egress/v1`` envelope as JSON."""
    janua_user_id, prefix = _resolve_principal(request)
    if not janua_user_id:
        if prefix:
            return Response(
                {
                    "error": (
                        "This API key is not linked to a Tezca account, so there "
                        "is no account data to export. Sign in and create the key "
                        "from your account page."
                    )
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        return Response(
            {"error": "Authentication required."}, status=status.HTTP_401_UNAUTHORIZED
        )

    return Response(_collect(janua_user_id, prefix))


@api_view(["GET"])
def user_export_download(request):
    """Same envelope as :func:`user_export`, served as a file attachment."""
    janua_user_id, prefix = _resolve_principal(request)
    if not janua_user_id:
        if prefix:
            return Response(
                {
                    "error": (
                        "This API key is not linked to a Tezca account, so there "
                        "is no account data to export. Sign in and create the key "
                        "from your account page."
                    )
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        return Response(
            {"error": "Authentication required."}, status=status.HTTP_401_UNAUTHORIZED
        )

    payload = _collect(janua_user_id, prefix)
    body = json.dumps(payload, ensure_ascii=False, indent=2, default=str)

    stamp = timezone.now().strftime("%Y%m%d")
    response = HttpResponse(body, content_type="application/json; charset=utf-8")
    response["Content-Disposition"] = (
        f'attachment; filename="tezca-export-{stamp}.json"'
    )
    response["Cache-Control"] = "no-store"
    return response
