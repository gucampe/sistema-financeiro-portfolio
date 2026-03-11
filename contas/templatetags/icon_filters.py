"""Filtros para renderização de ícones de contas (instituições vs genéricos)."""
from django import template

register = template.Library()

# Slug -> nome do arquivo quando diferente (ex.: inter -> intermedium.png)
ICONE_INSTITUICAO_FILENAME = {"inter": "intermedium"}

# Ícones que usam PNG em instituicoes/ (igual à view contas_home)
ICONE_INSTITUICOES = frozenset([
    "nubank", "itau", "santander", "bradesco", "bb", "caixa",
    "inter", "sicredi", "sicoob", "picpay", "mercadopago",
])


@register.filter
def icon_instituicao_filename(slug):
    """Retorna o nome do arquivo (sem extensão) para ícone de instituição."""
    if not slug:
        return "bank"
    return ICONE_INSTITUICAO_FILENAME.get(slug, slug)


@register.filter
def conta_icon_path(icone):
    """Retorna o caminho estático do ícone da conta (para uso com {% static %})."""
    slug = (icone or "bank").strip() or "bank"
    if slug in ICONE_INSTITUICOES:
        filename = ICONE_INSTITUICAO_FILENAME.get(slug, slug)
        return f"contas/icons/instituicoes/{filename}.png"
    return f"contas/icons/genericos/{slug}.svg"
