from django.db.models import QuerySet

from transacoes.models import Transacao


def transacoes_base_qs(usuario) -> QuerySet[Transacao]:
    """Queryset base para relatórios — sempre escopado ao usuário."""
    return Transacao.objects.filter(usuario=usuario).select_related(
        "conta", "categoria", "cartao", "fatura"
    )
