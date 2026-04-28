from django.apps import AppConfig


class FinanceiroConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'transacoes'

    def ready(self):
        import transacoes.signals  # noqa: F401
