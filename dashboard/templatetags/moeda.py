from django import template

register = template.Library()

@register.filter()
def moeda(valor):
    try:
        valor = float(valor)
        return f"R$ {valor:,.2f}".replace(",", "v").replace(".", ",").replace("v", ".")
    except (ValueError, TypeError):
        return "R$ 0,00" 