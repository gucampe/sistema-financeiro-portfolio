from django.apps import AppConfig


class CategorizacaoConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "categorizacao"
    verbose_name = "Categorização automática"

    def ready(self):
        import categorizacao.signals  # noqa: F401
