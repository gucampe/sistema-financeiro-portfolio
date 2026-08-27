"""Middlewares de performance."""

from __future__ import annotations

from django.contrib.auth import get_user_model


class PrefetchUserPerfilMiddleware:
    """Evita query lazy de `user.perfil` no header e context processors."""

    def __init__(self, get_response):
        self.get_response = get_response
        self._user_model = get_user_model()

    def __call__(self, request):
        user = getattr(request, "user", None)
        if user is not None and getattr(user, "is_authenticated", False):
            if hasattr(user, "perfil"):
                return self.get_response(request)
            request.user = (
                self._user_model.objects.select_related("perfil")
                .only(
                    "id",
                    "nome",
                    "email",
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "perfil__id",
                    "perfil__foto",
                    "perfil__ocultar_valores_dashboard",
                    "perfil__tema",
                )
                .get(pk=user.pk)
            )
        return self.get_response(request)
