"""CRM webhook dispatch — sends interest.created events to phyne-crm."""

import logging

from django.conf import settings

logger = logging.getLogger(__name__)

CRM_WEBHOOK_URL = getattr(settings, "CRM_WEBHOOK_URL", "")
CRM_WEBHOOK_SECRET = getattr(settings, "CRM_WEBHOOK_SECRET", "")


def dispatch_crm_event(event: str, payload: dict):
    """Queue a CRM sync via Celery if CRM is configured."""
    if not CRM_WEBHOOK_URL or not CRM_WEBHOOK_SECRET:
        return
    from .tasks import deliver_crm_webhook

    deliver_crm_webhook.delay(event, payload)
