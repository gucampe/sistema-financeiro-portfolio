"""Resposta de lockout do django-axes em português."""

from __future__ import annotations

from django.http import HttpResponse
from django.urls import reverse


def lockout_response(request, credentials, *args, **kwargs):
    reset_url = reverse("usuarios:password_reset")
    html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head><meta charset="utf-8"><title>Conta bloqueada</title></head>
<body style="font-family:system-ui,sans-serif;max-width:32rem;margin:3rem auto;padding:0 1rem;">
  <h1>Conta bloqueada temporariamente</h1>
  <p>Muitas tentativas de login incorretas. Aguarde alguns minutos e tente novamente.</p>
  <p>Se esqueceu a senha, use <a href="{reset_url}">redefinir senha</a>.</p>
  <p><a href="{reverse("usuarios:login")}">Voltar ao login</a></p>
</body>
</html>"""
    return HttpResponse(html, status=429, content_type="text/html; charset=utf-8")
