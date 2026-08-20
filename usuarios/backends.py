from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model

from usuarios.utils import normalizar_email


class EmailBackend(ModelBackend):
    def user_can_authenticate(self, user):
        return super().user_can_authenticate(user) and getattr(user, "ativo", True)

    def authenticate(self, request, email=None, password=None, **kwargs):
        Usuario = get_user_model()
        if email is None or password is None:
            return None
        email = normalizar_email(email)
        user = Usuario.objects.filter(email=email).first()
        if user is None:
            user = Usuario.objects.filter(email__iexact=email).first()
        if user is None:
            return None

        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None

    def get_user(self, user_id):
        Usuario = get_user_model()
        try:
            user = Usuario.objects.get(pk=user_id)
        except Usuario.DoesNotExist:
            return None
        if not self.user_can_authenticate(user):
            return None
        return user
