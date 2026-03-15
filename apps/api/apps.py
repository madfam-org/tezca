from django.apps import AppConfig


class ApiConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.api"

    def ready(self):
        import apps.api.signals  # noqa: F401
        from apps.api.posthog_analytics import init_posthog

        init_posthog()
