from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from django.contrib.auth import get_user_model

from categorias.models import Categoria
from categorizacao.services.learning import processar_feedback_transacao
from categorizacao.services.pipeline import sugerir
from contas.models import Conta
from transacoes.models import Transacao

from categorizacao.evaluation.longitudinal.ledger import LedgerRow

User = get_user_model()


@dataclass
class FeedbackStats:
    aceitas: int = 0
    corrigidas: int = 0
    ignoradas: int = 0


def _categoria(user, nome: str, tipo: str = "despesa") -> Categoria | None:
    from django.db.models import Q

    return (
        Categoria.objects.filter(nome__iexact=nome, tipo=tipo)
        .filter(Q(usuario=user) | Q(padrao=True))
        .first()
    )


def _categoria_diversos(user, tipo: str = "despesa") -> Categoria | None:
    return _categoria(user, "Diversos", tipo) or _categoria(user, "Outros", tipo)


def ingest_row(user: User, conta: Conta, row: LedgerRow, policy: str) -> FeedbackStats:
    """Cria transação, obtém sugestão e simula feedback conforme política."""
    stats = FeedbackStats()
    valor = Decimal(row.valor.replace(",", "."))
    cat_gold = _categoria(user, row.categoria_gold, row.tipo)
    if not cat_gold:
        cat_gold = _categoria_diversos(user, row.tipo)
    if not cat_gold:
        return stats

    sug = sugerir(user, row.descricao, row.tipo, abs(valor) if row.tipo == "despesa" else valor)
    sug_id = sug.categoria_id if sug else None
    sug_nome = sug.categoria_nome if sug else None

    if policy == "ignorar":
        cat_final = _categoria_diversos(user, row.tipo) or cat_gold
        stats.ignoradas += 1
        categoria_sugerida_id = None
    elif policy == "aceitar_sugestao":
        if sug_id:
            cat_final = Categoria.objects.get(pk=sug_id)
            stats.aceitas += 1
        else:
            cat_final = cat_gold
            stats.corrigidas += 1
        categoria_sugerida_id = sug_id
    elif policy == "aceitar_tudo":
        if sug_id and sug_nome == row.categoria_gold:
            cat_final = Categoria.objects.get(pk=sug_id)
            stats.aceitas += 1
        elif sug_id:
            cat_final = Categoria.objects.get(pk=sug_id)
            stats.aceitas += 1
        else:
            cat_final = cat_gold
            stats.aceitas += 1
        categoria_sugerida_id = sug_id
    elif policy == "corrigir_para_gold":
        cat_final = cat_gold
        if sug_id and sug_nome == row.categoria_gold:
            stats.aceitas += 1
        elif sug_id:
            stats.corrigidas += 1
        else:
            stats.corrigidas += 1
        categoria_sugerida_id = sug_id
    else:
        cat_final = cat_gold
        categoria_sugerida_id = sug_id

    tx = Transacao.objects.create(
        usuario=user,
        conta=conta,
        categoria=cat_final,
        tipo=row.tipo,
        valor=abs(valor) if row.tipo == "despesa" else valor,
        data=row.data,
        descricao=row.descricao,
    )

    processar_feedback_transacao(
        usuario=user,
        transacao=tx,
        descricao=row.descricao,
        categoria_final=cat_final,
        categoria_sugerida_id=categoria_sugerida_id,
        confianca=sug.confianca if sug else None,
        fonte=sug.fonte if sug else "",
    )
    return stats


def simulate_corrections_for_reimport(
    user: User,
    rows: list[LedgerRow],
    policy: str,
) -> tuple[int, int]:
    """Simula quantas correções seriam necessárias no preview (sem persistir)."""
    correcoes = 0
    aceites = 0
    for row in rows:
        valor = Decimal(row.valor.replace(",", "."))
        sug = sugerir(user, row.descricao, row.tipo, abs(valor))
        if not sug:
            if policy != "ignorar":
                correcoes += 1
            continue
        if sug.categoria_nome == row.categoria_gold:
            aceites += 1
        elif policy == "corrigir_para_gold":
            correcoes += 1
        elif policy == "ignorar":
            correcoes += 1
        elif policy in ("aceitar_sugestao", "aceitar_tudo"):
            if sug.categoria_nome != row.categoria_gold:
                correcoes += 1
            else:
                aceites += 1
    return aceites, correcoes
