from django import template

from usuarios.ajuda.catalogo import artigos_por_grupo, catalogo_ajuda_json

register = template.Library()


@register.inclusion_tag("usuarios/ajuda/drawer.html")
def ajuda_drawer():
    grupos = artigos_por_grupo()
    return {
        "ajuda_comece_aqui": grupos["comece_aqui"],
        "ajuda_organize": grupos["organize"],
        "ajuda_entenda": grupos["entenda"],
        "ajuda_catalogo_json": catalogo_ajuda_json(),
    }
