from usuarios.temas import TEMA_ESCURO, tema_do_request
from usuarios.utils import iniciais_avatar, primeiro_nome


def perfil_header(request):
    """Foto, iniciais e tema para o shell do app."""
    tema = tema_do_request(request)
    ctx = {
        "tema": tema,
        "tema_escuro": tema == TEMA_ESCURO,
    }
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return ctx

    perfil = getattr(user, "perfil", None)
    foto_url = perfil.foto.url if perfil and perfil.foto else None

    ctx.update(
        {
            "header_foto_url": foto_url,
            "header_iniciais_avatar": iniciais_avatar(user.nome),
            "header_primeiro_nome": primeiro_nome(user.nome),
        }
    )
    return ctx
