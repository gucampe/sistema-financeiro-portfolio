"""Agregações específicas da tela Visão Geral (dashboard executivo)."""

from __future__ import annotations

import calendar
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from django.db.models import Exists, OuterRef, Sum
from django.utils import timezone

from cartoes.models import Cartao, Fatura
from cartoes.services.faturas import obter_ou_criar_fatura
from cartoes.services.gestao_faturas import calcular_resumo_pagamento, total_fatura
from contas.models import Conta
from relatorios.selectors import transacoes_base_qs
from relatorios.services.agregacoes import (
    _float_json_seguro,
    aplicar_filtros_relatorio,
    orcamento_vs_realizado,
    resultado_fluxo,
    saldos_por_conta_totais,
    top_categorias,
    totais_por_tipo,
)
from relatorios.services.filtros import RelatorioFiltros
from transacoes.models import Transacao


def saudacao_periodo() -> str:
    hora = timezone.localtime().hour
    if hora < 12:
        return "Bom dia"
    if hora < 18:
        return "Boa tarde"
    return "Boa noite"


def _filtros_mes(ano: int, mes: int) -> RelatorioFiltros:
    inicio = date(ano, mes, 1)
    fim = date(ano, mes, calendar.monthrange(ano, mes)[1])
    return RelatorioFiltros(
        data_inicio=inicio,
        data_fim=fim,
        preset="custom",
    )


def _totais_mes(user, ano: int, mes: int) -> dict[str, Decimal]:
    filtros = _filtros_mes(ano, mes)
    qs = aplicar_filtros_relatorio(transacoes_base_qs(user), filtros)
    return totais_por_tipo(qs)


def _delta_pct(novo: Decimal, antigo: Decimal) -> Decimal | None:
    if antigo == 0:
        return None
    return (novo - antigo) / abs(antigo) * 100


def comparacao_mensal(user) -> dict[str, Any]:
    hoje = timezone.localdate()
    tot_atual = _totais_mes(user, hoje.year, hoje.month)
    if hoje.month == 1:
        ant_ano, ant_mes = hoje.year - 1, 12
    else:
        ant_ano, ant_mes = hoje.year, hoje.month - 1
    tot_anterior = _totais_mes(user, ant_ano, ant_mes)
    res_atual = resultado_fluxo(tot_atual)
    res_anterior = resultado_fluxo(tot_anterior)
    return {
        "atual": tot_atual,
        "anterior": tot_anterior,
        "resultado_atual": res_atual,
        "resultado_anterior": res_anterior,
        "delta_pct_receitas": _delta_pct(tot_atual["receitas"], tot_anterior["receitas"]),
        "delta_pct_despesas": _delta_pct(tot_atual["despesas"], tot_anterior["despesas"]),
        "delta_pct_resultado": _delta_pct(res_atual, res_anterior),
    }


def serie_evolucao_meses(user, *, meses: int = 6) -> dict[str, Any]:
    hoje = timezone.localdate()
    y, m = hoje.year, hoje.month
    labels: list[str] = []
    receitas: list[float] = []
    despesas: list[float] = []
    saldos: list[float] = []

    for _ in range(meses):
        tot = _totais_mes(user, y, m)
        res = resultado_fluxo(tot)
        labels.insert(0, date(y, m, 1).strftime("%b/%y").capitalize())
        receitas.insert(0, _float_json_seguro(tot["receitas"]))
        despesas.insert(0, _float_json_seguro(tot["despesas"]))
        saldos.insert(0, _float_json_seguro(res))
        if m == 1:
            m = 12
            y -= 1
        else:
            m -= 1

    return {
        "labels": labels,
        "receitas": receitas,
        "despesas": despesas,
        "saldos": saldos,
    }


def top_despesas_mes_atual(user, *, limit: int = 5) -> list[dict[str, Any]]:
    hoje = timezone.localdate()
    filtros = _filtros_mes(hoje.year, hoje.month)
    qs = aplicar_filtros_relatorio(transacoes_base_qs(user), filtros)
    return top_categorias(qs, "despesa", limit=limit)


def ultimas_movimentacoes(user, *, limit: int = 10):
    return (
        transacoes_base_qs(user)
        .select_related("categoria", "conta", "cartao")
        .order_by("-data", "-id")[:limit]
    )


def resumo_contas_patrimonio(user) -> dict[str, Any]:
    lista, total = saldos_por_conta_totais(user)
    return {"contas": lista, "patrimonio_total": total}


MESES_PT = (
    "",
    "Janeiro",
    "Fevereiro",
    "Março",
    "Abril",
    "Maio",
    "Junho",
    "Julho",
    "Agosto",
    "Setembro",
    "Outubro",
    "Novembro",
    "Dezembro",
)


def rotulo_periodo_atual() -> str:
    hoje = timezone.localdate()
    return f"Resumo de {MESES_PT[hoje.month]} de {hoje.year}"


def query_transacoes_mes_atual() -> str:
    hoje = timezone.localdate()
    inicio = date(hoje.year, hoje.month, 1)
    fim = date(hoje.year, hoje.month, calendar.monthrange(hoje.year, hoje.month)[1])
    from urllib.parse import urlencode

    return urlencode({"inicio": inicio.isoformat(), "fim": fim.isoformat()})


def _urgencia_vencimento(data: date, hoje: date) -> str:
    dias = (data - hoje).days
    if dias < 0:
        return "atrasado"
    if dias == 0:
        return "hoje"
    return "proximo"


def _nome_instituicao_conta(conta: Conta) -> str:
    nomes = {
        "nubank": "Nubank",
        "itau": "Itaú",
        "santander": "Santander",
        "bradesco": "Bradesco",
        "bb": "Banco do Brasil",
        "caixa": "Caixa",
        "inter": "Inter",
        "sicredi": "Sicredi",
        "sicoob": "Sicoob",
        "picpay": "PicPay",
        "mercadopago": "Mercado Pago",
    }
    if conta.icone in nomes:
        return nomes[conta.icone]
    return dict(Conta.TIPO_CHOICES).get(conta.tipo, conta.tipo)


def contas_dashboard(user, *, limit: int = 5) -> dict[str, Any]:
    lista, total = saldos_por_conta_totais(user)
    contas_qs = {
        c.id: c
        for c in Conta.objects.filter(usuario=user, ativa=True).only("id", "tipo", "icone", "nome")
    }
    contas: list[dict[str, Any]] = []
    for item in lista[:limit]:
        conta = contas_qs.get(item["conta_id"])
        instituicao = _nome_instituicao_conta(conta) if conta else ""
        contas.append({**item, "instituicao": instituicao})
    return {
        "contas": contas,
        "patrimonio_total": total,
        "total_contas": len(lista),
        "tem_mais": len(lista) > limit,
    }


def _status_alerta_cartao(dias: int, saldo: Decimal) -> str:
    if saldo <= 0:
        return "normal"
    if dias < 0:
        return "vencido"
    if dias <= 7:
        return "proximo"
    return "normal"


def resumo_cartoes_dashboard(user) -> dict[str, Any]:
    hoje = timezone.localdate()
    cartoes: list[dict[str, Any]] = []
    total_faturas = Decimal("0")
    for cartao in Cartao.objects.filter(usuario=user, ativa=True).order_by("nome"):
        fatura = obter_ou_criar_fatura(cartao, hoje)
        resumo = calcular_resumo_pagamento(fatura, hoje)
        saldo = resumo.saldo or Decimal("0")
        total_faturas += saldo
        dias = (fatura.data_vencimento - hoje).days
        limite_disp = max(cartao.limite - saldo, Decimal("0"))
        cartoes.append(
            {
                "cartao_id": cartao.id,
                "fatura_id": fatura.id,
                "nome": cartao.nome,
                "icone": cartao.icone,
                "limite": cartao.limite,
                "limite_disponivel": limite_disp,
                "valor_fatura": resumo.total,
                "saldo_fatura": saldo,
                "data_vencimento": fatura.data_vencimento,
                "dias_vencimento": dias,
                "texto_vencimento": _texto_vencimento(dias),
                "alerta": _status_alerta_cartao(dias, saldo),
                "status_pagamento": resumo.status_pagamento,
            }
        )
    return {
        "cartoes": cartoes,
        "total_faturas": total_faturas,
        "quantidade": len(cartoes),
    }


def _item_saida_fatura(fatura: Fatura, hoje: date) -> dict[str, Any] | None:
    """Fatura pendente com lançamentos, pronta para exibição em saídas previstas."""
    if total_fatura(fatura) <= 0:
        return None
    resumo = calcular_resumo_pagamento(fatura, hoje)
    if resumo.saldo <= 0:
        return None
    dias = (fatura.data_vencimento - hoje).days
    mes_comp = MESES_PT[fatura.competencia.month]
    return {
        "titulo": f"Fatura {fatura.cartao.nome} {mes_comp}",
        "subtitulo": _texto_vencimento(dias),
        "data": fatura.data_vencimento,
        "valor": resumo.saldo,
        "urgencia": _urgencia_vencimento(fatura.data_vencimento, hoje),
        "tipo": "fatura",
    }


def _faturas_saidas_previstas(
    user,
    hoje: date,
    *,
    max_atrasadas: int = 3,
    max_proximas: int = 3,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Faturas pendentes com lançamentos: até N atrasadas e N próximas."""
    tem_lancamento = Transacao.objects.filter(
        fatura=OuterRef("pk"),
        usuario=OuterRef("usuario_id"),
        tipo="despesa",
    )
    faturas = (
        Fatura.objects.filter(usuario=user)
        .filter(Exists(tem_lancamento))
        .select_related("cartao")
    )

    atrasadas: list[dict[str, Any]] = []
    proximas: list[dict[str, Any]] = []
    for fatura in faturas:
        item = _item_saida_fatura(fatura, hoje)
        if item is None:
            continue
        if fatura.data_vencimento < hoje:
            atrasadas.append(item)
        else:
            proximas.append(item)

    atrasadas.sort(key=lambda x: x["data"], reverse=True)
    proximas.sort(key=lambda x: x["data"])

    return atrasadas[:max_atrasadas], proximas[:max_proximas]


def fluxo_caixa_futuro_dashboard(
    user,
    *,
    max_faturas_atrasadas: int = 3,
    max_faturas_proximas: int = 3,
    max_meses_entradas: int = 3,
) -> dict[str, Any]:
    """
    Painel consolidado de fluxo futuro: resumo 30d, faturas de cartão pendentes
    (até 3 atrasadas + 3 próximas) e entradas agrupadas por mês.
    """
    hoje = timezone.localdate()
    fim_30 = hoje + timedelta(days=30)
    horizonte_saidas = hoje + timedelta(days=365)

    saidas_atrasadas, saidas_proximas = _faturas_saidas_previstas(
        user,
        hoje,
        max_atrasadas=max_faturas_atrasadas,
        max_proximas=max_faturas_proximas,
    )
    saidas = saidas_atrasadas + saidas_proximas

    # Entradas agrupadas por mês (futuras)
    receitas_por_mes: dict[tuple[int, int], Decimal] = {}
    receitas_qs = (
        Transacao.objects.filter(
            usuario=user,
            tipo="receita",
            cartao__isnull=True,
            data__gte=hoje,
            data__lte=horizonte_saidas,
        )
        .only("data", "valor")
        .order_by("data")
    )
    for tx in receitas_qs.iterator(chunk_size=500):
        chave = (tx.data.year, tx.data.month)
        receitas_por_mes[chave] = receitas_por_mes.get(chave, Decimal("0")) + tx.valor

    entradas_meses: list[dict[str, Any]] = []
    for ano, mes in sorted(receitas_por_mes.keys()):
        total = receitas_por_mes[(ano, mes)]
        if total <= 0:
            continue
        entradas_meses.append(
            {
                "rotulo": f"{MESES_PT[mes]} {ano}",
                "total": total,
                "ano": ano,
                "mes": mes,
            }
        )
        if len(entradas_meses) >= max_meses_entradas:
            break

    # Totais próximos 30 dias
    total_receber_30 = (
        Transacao.objects.filter(
            usuario=user,
            tipo="receita",
            cartao__isnull=True,
            data__gte=hoje,
            data__lte=fim_30,
        ).aggregate(s=Sum("valor"))["s"]
        or Decimal("0")
    )

    total_pagar_30 = Decimal("0")
    tem_lancamento = Transacao.objects.filter(
        fatura=OuterRef("pk"),
        usuario=OuterRef("usuario_id"),
        tipo="despesa",
    )
    for fatura in (
        Fatura.objects.filter(
            usuario=user,
            data_vencimento__gte=hoje,
            data_vencimento__lte=fim_30,
        )
        .filter(Exists(tem_lancamento))
        .select_related("cartao")
    ):
        resumo = calcular_resumo_pagamento(fatura, hoje)
        if resumo.saldo > 0:
            total_pagar_30 += resumo.saldo

    total_pagar_30 += (
        Transacao.objects.filter(
            usuario=user,
            tipo="despesa",
            cartao__isnull=True,
            data__gte=hoje,
            data__lte=fim_30,
        ).aggregate(s=Sum("valor"))["s"]
        or Decimal("0")
    )

    saldo_projetado = total_receber_30 - total_pagar_30
    todos_vazios = len(saidas) == 0 and len(entradas_meses) == 0

    return {
        "resumo_30d": {
            "total_receber": total_receber_30,
            "total_pagar": total_pagar_30,
            "saldo_projetado": saldo_projetado,
        },
        "saidas": saidas,
        "saidas_atrasadas": saidas_atrasadas,
        "saidas_proximas": saidas_proximas,
        "entradas_meses": entradas_meses,
        "todos_vazios": todos_vazios,
    }


def _texto_vencimento(dias: int) -> str:
    if dias < 0:
        n = abs(dias)
        return f"Atrasada há {n} dia{'s' if n != 1 else ''}"
    if dias == 0:
        return "Vence hoje"
    if dias == 1:
        return "Vence amanhã"
    return f"Vence em {dias} dias"


def resumo_cartoes(user) -> list[dict[str, Any]]:
    hoje = timezone.localdate()
    out: list[dict[str, Any]] = []
    cartoes = Cartao.objects.filter(usuario=user, ativa=True).order_by("nome")
    for cartao in cartoes:
        fatura = obter_ou_criar_fatura(cartao, hoje)
        resumo = calcular_resumo_pagamento(fatura, hoje)
        dias = (fatura.data_vencimento - hoje).days
        out.append(
            {
                "cartao_id": cartao.id,
                "fatura_id": fatura.id,
                "nome": cartao.nome,
                "valor_fatura": resumo.total,
                "saldo_fatura": resumo.saldo,
                "data_vencimento": fatura.data_vencimento,
                "dias_vencimento": dias,
                "texto_vencimento": _texto_vencimento(dias),
                "status_pagamento": resumo.status_pagamento,
            }
        )
    return out


def proximos_vencimentos(user, *, limit: int = 5) -> list[dict[str, Any]]:
    hoje = timezone.localdate()
    limite = hoje + timedelta(days=90)
    itens: list[dict[str, Any]] = []

    faturas = (
        Fatura.objects.filter(
            usuario=user,
            data_vencimento__gte=hoje - timedelta(days=7),
            data_vencimento__lte=limite,
        )
        .select_related("cartao")
        .order_by("data_vencimento")
    )
    for fatura in faturas:
        resumo = calcular_resumo_pagamento(fatura, hoje)
        if resumo.saldo <= 0:
            continue
        itens.append(
            {
                "descricao": f"Fatura {fatura.cartao.nome}",
                "data": fatura.data_vencimento,
                "valor": resumo.saldo,
                "tipo": "fatura",
            }
        )

    despesas = (
        Transacao.objects.filter(
            usuario=user,
            tipo="despesa",
            cartao__isnull=True,
            data__gte=hoje,
            data__lte=limite,
        )
        .select_related("categoria")
        .order_by("data", "id")
    )
    for tx in despesas:
        itens.append(
            {
                "descricao": tx.descricao,
                "data": tx.data,
                "valor": tx.valor,
                "tipo": "despesa",
            }
        )

    itens.sort(key=lambda x: x["data"])
    return itens[:limit]


def metas_financeiras(user) -> list[dict[str, Any]]:
    from relatorios.services.orcamentos import listar_orcamentos_dashboard

    return [linha.as_dict() for linha in listar_orcamentos_dashboard(user, limite=3)]


def calcular_saldo_disponivel(user, patrimonio_total: Decimal) -> dict[str, Any]:
    """
    Estimativa: patrimônio em contas − faturas pendentes − despesas futuras em conta.
    TODO: incluir receitas previstas, parcelas e reserva mínima configurável pelo usuário.
    """
    hoje = timezone.localdate()
    limite = hoje + timedelta(days=30)

    total_faturas = Decimal("0")
    for card in resumo_cartoes(user):
        total_faturas += card.get("saldo_fatura") or Decimal("0")

    despesas_futuras = (
        Transacao.objects.filter(
            usuario=user,
            tipo="despesa",
            cartao__isnull=True,
            data__gte=hoje,
            data__lte=limite,
        ).aggregate(s=Sum("valor"))["s"]
        or Decimal("0")
    )

    compromissos = total_faturas + despesas_futuras
    disponivel = patrimonio_total - compromissos

    return {
        "valor": disponivel,
        "patrimonio": patrimonio_total,
        "faturas_pendentes": total_faturas,
        "despesas_futuras": despesas_futuras,
        "compromissos": compromissos,
    }


def resumo_obrigacoes(user) -> dict[str, int]:
    """Contagens compactas para o card de obrigações (sem listar itens)."""
    hoje = timezone.localdate()
    limite = hoje + timedelta(days=90)

    contas_pagar = 0
    faturas = Fatura.objects.filter(
        usuario=user,
        data_vencimento__gte=hoje - timedelta(days=7),
        data_vencimento__lte=limite,
    )
    for fatura in faturas:
        if calcular_resumo_pagamento(fatura, hoje).saldo > 0:
            contas_pagar += 1

    contas_pagar += Transacao.objects.filter(
        usuario=user,
        tipo="despesa",
        cartao__isnull=True,
        data__gte=hoje,
        data__lte=limite,
    ).count()

    contas_receber = Transacao.objects.filter(
        usuario=user,
        tipo="receita",
        cartao__isnull=True,
        data__gte=hoje,
        data__lte=limite,
    ).count()

    faturas_abertas = 0
    for card in resumo_cartoes(user):
        if (card.get("saldo_fatura") or Decimal("0")) > 0:
            faturas_abertas += 1

    return {
        "contas_pagar": contas_pagar,
        "contas_receber": contas_receber,
        "faturas_abertas": faturas_abertas,
    }


def percentual_economia_mes(receitas: Decimal, resultado: Decimal) -> Decimal | None:
    if receitas <= 0:
        return None
    return (resultado / receitas) * 100


def contagem_ativos(user) -> dict[str, int]:
    return {
        "contas": Conta.objects.filter(usuario=user, ativa=True).count(),
        "cartoes": Cartao.objects.filter(usuario=user, ativa=True).count(),
    }
