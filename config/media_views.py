"""Servir arquivos de mídia apenas para usuários autorizados (produção)."""

from __future__ import annotations

import mimetypes
from pathlib import Path

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import FileResponse, Http404
from django.views.decorators.http import require_GET


def _media_root() -> Path:
    return Path(settings.MEDIA_ROOT).resolve()


def _safe_path(relative: str) -> Path:
    relative = relative.lstrip("/")
    if not relative or ".." in relative.split("/"):
        raise Http404
    full = (_media_root() / relative).resolve()
    if not str(full).startswith(str(_media_root())):
        raise Http404
    if not full.is_file():
        raise Http404
    return full


def _user_can_access(user, relative: str) -> bool:
    if user.is_staff or user.is_superuser:
        return True

    from relatorios.models import ExportJob
    from usuarios.models import Perfil

    if relative.startswith("perfis/fotos/"):
        return Perfil.objects.filter(usuario=user, foto=relative).exists()

    if relative.startswith("exports/"):
        return ExportJob.objects.filter(usuario=user, arquivo=relative).exists()

    return False


@login_required
@require_GET
def protected_media(request, path: str):
    relative = path
    if not _user_can_access(request.user, relative):
        raise Http404
    full = _safe_path(relative)
    content_type, _ = mimetypes.guess_type(str(full))
    return FileResponse(full.open("rb"), content_type=content_type or "application/octet-stream")
