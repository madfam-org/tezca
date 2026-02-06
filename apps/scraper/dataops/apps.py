from django.apps import AppConfig


class DataopsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.scraper.dataops"
    verbose_name = "Data Operations"
