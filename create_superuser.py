#!/usr/bin/env python
"""
Cria superusuário automaticamente no deploy (Render).

Usa variáveis de ambiente e não duplica usuário existente (login por e-mail).
"""

import os
import sys

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.contrib.auth import get_user_model


def main() -> int:
    email = os.environ.get("DJANGO_SUPERUSER_EMAIL", "").strip()
    password = os.environ.get("DJANGO_SUPERUSER_PASSWORD", "")
    # App usa e-mail como login; USERNAME guarda o nome completo (campo `nome`).
    nome = os.environ.get("DJANGO_SUPERUSER_USERNAME", "").strip()

    if not all([email, password, nome]):
        print(
            "Variáveis DJANGO_SUPERUSER_* incompletas; criação de superusuário ignorada.",
            file=sys.stderr,
        )
        return 0

    User = get_user_model()
    email = User.objects.normalize_email(email)

    if User.objects.filter(email=email).exists():
        print(f"Superusuário já existe: {email}")
        return 0

    User.objects.create_superuser(email=email, password=password, nome=nome)
    print(f"Superusuário criado: {email}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
