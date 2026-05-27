from usuarios.utils import iniciais_avatar, primeiro_nome


def perfil_header(request):
    """Foto e iniciais do usuário para o header global."""
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return {}

    perfil = getattr(user, "perfil", None)
    foto_url = perfil.foto.url if perfil and perfil.foto else None

    return {
        "header_foto_url": foto_url,
        "header_iniciais_avatar": iniciais_avatar(user.nome),
        "header_primeiro_nome": primeiro_nome(user.nome),
    }
