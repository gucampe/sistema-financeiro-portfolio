from django.apps import AppConfig


class CategoriasConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'categorias'

    def ready(self):
        from . import signal  # noqa