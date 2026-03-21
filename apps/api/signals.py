"""Django signals for webhook dispatch on Law/LawVersion changes."""

import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

logger = logging.getLogger(__name__)


def _resolve_domains(category: str) -> list[str]:
    """Return domain keys whose category lists include the given category."""
    from .constants import DOMAIN_MAP

    if not category:
        return []
    return [domain for domain, cats in DOMAIN_MAP.items() if category in cats]


@receiver(post_save, sender="api.Law")
def law_changed(sender, instance, created, **kwargs):
    """Dispatch webhook when a Law is created or updated."""
    from .webhooks import dispatch_webhook_event

    event = "law.created" if created else "law.updated"
    dispatch_webhook_event(
        event,
        {
            "law_id": instance.official_id,
            "law_name": instance.name,
            "category": instance.category or "",
            "tier": instance.tier or "",
            "law_type": instance.law_type or "",
            "domains": _resolve_domains(instance.category or ""),
        },
    )


@receiver(post_save, sender="api.LawVersion")
def version_created(sender, instance, created, **kwargs):
    """Dispatch webhook when a new LawVersion is created."""
    if not created:
        return

    from .webhooks import dispatch_webhook_event

    dispatch_webhook_event(
        "version.created",
        {
            "law_id": instance.law.official_id,
            "law_name": instance.law.name,
            "category": instance.law.category or "",
            "publication_date": str(instance.publication_date),
            "law_type": instance.law.law_type or "",
            "domains": _resolve_domains(instance.law.category or ""),
        },
    )
