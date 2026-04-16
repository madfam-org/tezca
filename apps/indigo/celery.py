"""
Celery application configuration for Leyes Como Código MX.
"""

import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "apps.indigo.settings")

app = Celery("leyes_mx")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
app.autodiscover_tasks(["apps.scraper.scheduling"])
