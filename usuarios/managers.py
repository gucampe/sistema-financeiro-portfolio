from django.contrib.auth.base_user import BaseUserManager
from django.utils.translation import gettext_lazy as _

from usuarios.utils import normalizar_email


class UsuarioManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError(_('O campo de e-mail é obrigatório'))
        email = normalizar_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if not extra_fields.get('is_staff'):
            raise ValueError(_('Superusuário precisa ter is_staff=True'))
        if not extra_fields.get('is_superuser'):
            raise ValueError(_('Superusuário precisa ter is_superuser=True'))

        return self.create_user(email, password, **extra_fields)
