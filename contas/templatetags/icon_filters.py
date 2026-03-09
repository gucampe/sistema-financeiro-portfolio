"""Filtros para renderização de ícones de contas (instituições vs genéricos)."""
from django import template

register = template.Library()

# Slug -> nome do arquivo quando diferente (ex.: inter -> intermedium.png)
ICONE_INSTITUICAO_FILENAME = {"inter": "intermedium"}


@register.filter
def icon_instituicao_filename(slug):
    """Retorna o nome do arquivo (sem extensão) para ícone de instituição."""
    if not slug:
        return "bank"
    return ICONE_INSTITUICAO_FILENAME.get(slug, slug)
