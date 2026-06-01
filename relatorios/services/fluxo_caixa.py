"""
Destaques, narrativa e interpretação do fluxo de caixa no período selecionado.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from django.db.models import QuerySet
from django.utils import timezone

from relatorios.services.agregacoes import aplicar_filtros_relatorio, resultado_fluxo, totais_por_tipo
from relatorios.services.filtros import RelatorioFiltros
from relatorios.selectors import transacoes_base_qs
from transacoes.models import Transacao


def _titulo_transacao(tx: Transacao | None) -> str | None:
    if tx is None:
        return None
    if tx.categoria_id and tx.categoria:
        return tx.categoria.nome
    desc = (tx.descricao or "").strip()
    return desc or "Sem descrição"


def _delta_pct(novo: Decimal, antigo: Decimal) -> Decimal | None:
    if antigo == 0:
        return None
    return (novo - antigo) / abs(antigo) * 100


def destaques_fluxo_periodo(
    qs: QuerySet[Transacao],
    filtros: RelatorioFiltros,
    serie_fluxo: dict[str, Any],
) -> dict[str, Any | None]:
    """Maior entrada/saída e melhor/pior dia líquido no intervalo."""
    maior_receita = (
        qs.filter(tipo="receita").select_related("categoria").order_by("-valor").first()
    )
    maior_despesa = (
        qs.filter(tipo="despesa").select_related("categoria").order_by("-valor").first()
    )

    liquidos: list[float] = serie_fluxo.get("liquido") or []
    labels: list[str] = serie_fluxo.get("labels") or []

    melhor_valor: float | None = None
    melhor_rotulo: str | None = None
    pior_valor: float | None = None
    pior_rotulo: str | None = None

    for idx, bruto in enumerate(liquidos):
        if bruto > 0 and (melhor_valor is None or bruto > melhor_valor):
            melhor_valor = bruto
            melhor_rotulo = labels[idx] if idx < len(labels) else None
        if bruto < 0 and (pior_valor is None or bruto < pior_valor):
            pior_valor = bruto
            pior_rotulo = labels[idx] if idx < len(labels) else None

    def _destaque_tx(tx: Transacao | None) -> dict[str, Any] | None:
        if tx is None:
            return None
        return {
            "valor": tx.valor,
            "titulo": _titulo_transacao(tx),
            "rotulo": tx.data.strftime("%d/%m"),
        }

    def _destaque_dia(valor: float | None, rotulo: str | None) -> dict[str, Any] | None:
        if valor is None or rotulo is None:
            return None
        return {"valor": Decimal(str(valor)), "rotulo": rotulo}

    return {
        "maior_entrada": _destaque_tx(maior_receita),
        "maior_saida": _destaque_tx(maior_despesa),
        "melhor_dia": _destaque_dia(melhor_valor, melhor_rotulo),
        "pior_dia": _destaque_dia(pior_valor, pior_rotulo),
        "tem_movimentacao": qs.exists(),
    }


def indicadores_saude_fluxo(
    totais: dict[str, Decimal],
    serie_fluxo: dict[str, Any],
    destaques: dict[str, Any | None],
) -> dict[str, Any]:
    liquidos: list[float] = serie_fluxo.get("liquido") or []

    return {
        "dias_positivos": sum(1 for v in liquidos if v > 0),
        "dias_negativos": sum(1 for v in liquidos if v < 0),
        "maior_sobra_diaria": destaques.get("melhor_dia"),
    }


def comparacao_mes_anterior(
    usuario,
    filtros: RelatorioFiltros,
    totais: dict[str, Decimal],
    resultado: Decimal,
    serie_fluxo: dict[str, Any],
) -> dict[str, Any]:
    ano, mes = filtros.data_inicio.year, filtros.data_inicio.month
    if mes == 1:
        ant_ano, ant_mes = ano - 1, 12
    else:
        ant_ano, ant_mes = ano, mes - 1

    ant_filtros = filtros_mes(filtros, ant_ano, ant_mes)
    qs_ant = aplicar_filtros_relatorio(transacoes_base_qs(usuario), ant_filtros)
    tot_ant = totais_por_tipo(qs_ant)
    res_ant = resultado_fluxo(tot_ant)

    acumulado: list[float] = serie_fluxo.get("acumulado") or []
    crescimento_saldo_pct: Decimal | None = None
    if len(acumulado) >= 2:
        ini, fim = acumulado[0], acumulado[-1]
        if ini != 0:
            crescimento_saldo_pct = Decimal(str((fim - ini) / abs(ini) * 100))
        elif fim > 0:
            crescimento_saldo_pct = None

    tem_base = (tot_ant["receitas"] or Decimal("0")) > 0 or (tot_ant["despesas"] or Decimal("0")) > 0
    rec_atual = totais.get("receitas") or Decimal("0")
    desp_atual = totais.get("despesas") or Decimal("0")
    rec_ant = tot_ant["receitas"] or Decimal("0")
    desp_ant = tot_ant["despesas"] or Decimal("0")

    return {
        "receitas_pct": _delta_pct(rec_atual, rec_ant),
        "despesas_pct": _delta_pct(desp_atual, desp_ant),
        "resultado_pct": _delta_pct(resultado, res_ant),
        "delta_receitas": rec_atual - rec_ant,
        "delta_despesas": desp_atual - desp_ant,
        "delta_resultado": resultado - res_ant,
        "crescimento_saldo_pct": crescimento_saldo_pct,
        "tem_base": tem_base,
    }


def insights_rapidos(
    totais: dict[str, Decimal],
    resultado: Decimal,
    destaques: dict[str, Any | None],
    indicadores: dict[str, Any],
) -> dict[str, Any]:
    """Frases curtas para interpretação rápida do período."""
    receitas = totais.get("receitas") or Decimal("0")
    despesas = totais.get("despesas") or Decimal("0")

    if receitas == 0 and despesas == 0:
        return {"modo": "vazio", "itens": []}

    itens: list[str] = []

    if resultado > 0:
        itens.append("Você terminou o mês com saldo positivo.")
    elif resultado < 0:
        itens.append("Você terminou o mês com saldo negativo.")
    else:
        itens.append("Receitas e despesas se equilibraram no período.")

    maior_saida = destaques.get("maior_saida")
    if maior_saida:
        itens.append(f"Sua maior despesa foi {maior_saida['titulo']}.")

    maior_entrada = destaques.get("maior_entrada")
    if maior_entrada:
        itens.append(f"A maior entrada ocorreu em {maior_entrada['rotulo']}.")

    taxa = taxa_retencao(totais, resultado)
    if taxa is not None and receitas > 0:
        itens.append(f"Você poupou {taxa:.0f}% da renda.")

    dias_pos = indicadores.get("dias_positivos") or 0
    dias_neg = indicadores.get("dias_negativos") or 0
    if dias_pos or dias_neg:
        itens.append(f"{dias_pos} dias positivos e {dias_neg} negativos no período.")

    return {"modo": "completo", "itens": itens[:5]}


def contexto_periodo(
    mes_rotulo: str,
    totais: dict[str, Decimal],
    resultado: Decimal,
    indicadores: dict[str, Any],
) -> dict[str, Any]:
    """Narrativa única do período + resumo compacto de indicadores + CTA."""
    receitas = totais.get("receitas") or Decimal("0")
    despesas = totais.get("despesas") or Decimal("0")

    if receitas == 0 and despesas == 0:
        return {
            "titulo": f"O que aconteceu em {mes_rotulo}",
            "modo": "vazio",
            "cta_label": "Abrir transações",
            "cta_tipo": "transacoes",
        }

    dias_pos = indicadores.get("dias_positivos") or 0
    dias_neg = indicadores.get("dias_negativos") or 0

    if receitas > 0 and despesas > 0:
        if resultado > 0:
            narrativa_tipo = "receitas_superaram"
        elif resultado < 0:
            narrativa_tipo = "despesas_superaram"
        else:
            narrativa_tipo = "equilibrio"
    elif receitas > 0:
        narrativa_tipo = "so_receitas"
    else:
        narrativa_tipo = "so_despesas"

    if resultado > 0:
        if dias_neg == 0 or dias_pos >= dias_neg * 2:
            texto_conclusao = (
                "Você encerrou o período com saldo positivo e manteve uma boa margem financeira."
            )
        else:
            texto_conclusao = (
                "Você fechou positivo, mas alguns dias tiveram saldo negativo — "
                "vale revisar os picos de saída."
            )
        cta_label = "Analisar categorias"
        cta_tipo = "categorias"
    elif resultado < 0:
        texto_conclusao = "Atenção: suas despesas superaram as receitas neste período."
        cta_label = "Ver maiores despesas"
        cta_tipo = "despesas"
    else:
        texto_conclusao = "O período terminou equilibrado, sem sobra nem déficit líquido."
        cta_label = "Ver transações"
        cta_tipo = "transacoes"

    partes: list[str] = []
    if dias_pos or dias_neg:
        partes.append(f"{dias_pos} dias positivos · {dias_neg} negativos")
    maior = indicadores.get("maior_sobra_diaria")
    if maior:
        partes.append("maior_sobra")

    return {
        "titulo": f"O que aconteceu em {mes_rotulo}",
        "modo": "completo",
        "narrativa_tipo": narrativa_tipo,
        "receitas": receitas,
        "despesas": despesas,
        "resultado": resultado,
        "resultado_abs": abs(resultado),
        "texto_conclusao": texto_conclusao,
        "indicadores_resumo": " · ".join(partes),
        "mostrar_maior_sobra": bool(maior),
        "maior_sobra": maior,
        "dias_positivos": dias_pos,
        "dias_negativos": dias_neg,
        "cta_label": cta_label,
        "cta_tipo": cta_tipo,
    }


def titulo_hero(mes_rotulo: str, resultado: Decimal) -> str:
    if resultado > 0:
        return f"Você encerrou {mes_rotulo} com saldo positivo"
    if resultado < 0:
        return f"Você fechou {mes_rotulo} no negativo"
    return f"Resultado equilibrado em {mes_rotulo}"


def resumo_o_que_aconteceu(
    mes_rotulo: str,
    totais: dict[str, Decimal],
    resultado: Decimal,
    comparacao: dict[str, Any],
) -> dict[str, Any]:
    """Compatibilidade com testes legados."""
    ins = insights_rapidos(totais, resultado, {}, {"dias_positivos": 0, "dias_negativos": 0})
    return {
        "titulo": f"O que aconteceu em {mes_rotulo}",
        "modo": ins["modo"],
        "mensagem": ins["itens"][0] if ins["itens"] else "",
        "linhas": [],
    }


def status_resultado(resultado: Decimal) -> dict[str, str]:
    if resultado > 0:
        return {"rotulo": "Saldo positivo", "tom": "emerald"}
    if resultado < 0:
        return {"rotulo": "Saldo negativo", "tom": "rose"}
    return {"rotulo": "Equilibrado", "tom": "gray"}


def taxa_retencao(totais: dict[str, Decimal], resultado: Decimal) -> Decimal | None:
    receitas = totais.get("receitas") or Decimal("0")
    if receitas <= 0:
        return None
    return max(min(resultado / receitas * 100, Decimal("999")), Decimal("-999"))


def alerta_proximo_fluxo(usuario, fluxo_caixa: dict[str, Any]) -> dict[str, Any]:
    hoje = timezone.localdate()
    resumo = fluxo_caixa.get("resumo_30d") or {}
    saldo_proj = resumo.get("saldo_projetado") or Decimal("0")

    if fluxo_caixa.get("todos_vazios"):
        return {
            "nivel": "neutro",
            "titulo": "Sem projeções cadastradas",
            "mensagem": "Cadastre receitas e despesas futuras para acompanhar o que vem pela frente.",
        }

    prox_receita = (
        Transacao.objects.filter(
            usuario=usuario,
            tipo="receita",
            cartao__isnull=True,
            data__gte=hoje,
        )
        .order_by("data")
        .only("data", "valor")
        .first()
    )

    if saldo_proj < 0:
        return {
            "nivel": "aviso",
            "titulo": "Atenção ao fluxo futuro",
            "mensagem": "Despesas previstas superam o que você deve receber nos próximos 30 dias.",
        }

    if prox_receita:
        dias = (prox_receita.data - hoje).days
        if dias == 0:
            return {
                "nivel": "info",
                "titulo": "Recebimento previsto para hoje",
                "mensagem": "Há uma entrada programada para hoje no seu calendário.",
            }
        if dias == 1:
            return {
                "nivel": "info",
                "titulo": "Próximo recebimento amanhã",
                "mensagem": "Sua próxima entrada está prevista para amanhã.",
            }
        if dias <= 14:
            return {
                "nivel": "info",
                "titulo": f"Próximo recebimento em {dias} dias",
                "mensagem": "Você possui saldo projetado positivo até lá."
                if saldo_proj >= 0
                else "Revise despesas previstas antes do próximo recebimento.",
            }

    if saldo_proj >= 0:
        return {
            "nivel": "ok",
            "titulo": "Situação confortável",
            "mensagem": "Você possui saldo suficiente para chegar ao próximo recebimento.",
        }

    return {
        "nivel": "neutro",
        "titulo": "Acompanhe o que vem pela frente",
        "mensagem": "Confira entradas e saídas previstas nos próximos 30 dias.",
    }


def percentual_despesas_sobre_receitas(totais: dict[str, Decimal]) -> Decimal | None:
    receitas = totais.get("receitas") or Decimal("0")
    despesas = totais.get("despesas") or Decimal("0")
    if receitas <= 0:
        return None
    return min(despesas / receitas * 100, Decimal("999"))


def resumo_minimo_periodo(
    serie_fluxo: dict[str, Any],
    resultado: Decimal,
) -> dict[str, Any]:
    """Saldo inicial, final e variação líquida no intervalo (fluxo acumulado do período)."""
    acumulado: list[float] = serie_fluxo.get("acumulado") or []
    liquidos: list[float] = serie_fluxo.get("liquido") or []
    saldo_inicial = Decimal("0")
    saldo_final = Decimal(str(acumulado[-1])) if acumulado else Decimal("0")
    tem_movimentacao = any(v != 0 for v in liquidos)
    return {
        "saldo_inicial": saldo_inicial,
        "saldo_final": saldo_final,
        "variacao_liquida": resultado,
        "tem_movimentacao": tem_movimentacao,
    }


def _pico_dia(
    valores: list[float],
    labels: list[str],
) -> dict[str, Any] | None:
    if not valores:
        return None
    maior = max(valores)
    if maior <= 0:
        return None
    idx = valores.index(maior)
    return {
        "rotulo": labels[idx] if idx < len(labels) else "",
        "valor": Decimal(str(maior)),
    }


def dinamica_fluxo_periodo(
    serie_fluxo: dict[str, Any],
    destaques: dict[str, Any | None],
) -> dict[str, Any]:
    """Picos e padrão de movimentação diária."""
    labels: list[str] = serie_fluxo.get("labels") or []
    entradas: list[float] = serie_fluxo.get("entradas") or []
    saidas: list[float] = serie_fluxo.get("saidas") or []
    total_dias = len(labels) or 1

    dias_com_entrada = sum(1 for v in entradas if v > 0)
    dias_com_saida = sum(1 for v in saidas if v > 0)
    dias_com_movimento = sum(
        1 for i in range(len(entradas)) if entradas[i] > 0 or (i < len(saidas) and saidas[i] > 0)
    )

    return {
        "pico_entrada": _pico_dia(entradas, labels),
        "pico_saida": _pico_dia(saidas, labels),
        "melhor_dia": destaques.get("melhor_dia"),
        "pior_dia": destaques.get("pior_dia"),
        "dias_com_movimento": dias_com_movimento,
        "dias_com_entrada": dias_com_entrada,
        "dias_com_saida": dias_com_saida,
        "total_dias": total_dias,
        "fluxo_irregular": 0 < dias_com_movimento < total_dias * 0.35,
        "entradas_pontuais": dias_com_entrada <= 2 and dias_com_entrada > 0,
        "entradas_recorrentes": dias_com_entrada >= 5,
    }


def interpretacao_dinamica_fluxo(
    dinamica: dict[str, Any],
    totais: dict[str, Decimal],
) -> list[str]:
    """Leitura do comportamento do fluxo — sem repetir KPIs do topo."""
    receitas = totais.get("receitas") or Decimal("0")
    despesas = totais.get("despesas") or Decimal("0")

    if receitas == 0 and despesas == 0:
        return []

    frases: list[str] = []

    if dinamica.get("fluxo_irregular"):
        frases.append(
            "O fluxo do mês foi irregular — a movimentação concentrou-se em poucos dias."
        )
    elif (dinamica.get("dias_com_movimento") or 0) >= (dinamica.get("total_dias") or 1) * 0.4:
        frases.append("O fluxo se distribuiu ao longo do mês, com movimentação frequente.")
    else:
        frases.append("Houve períodos longos sem movimentação registrada.")

    if dinamica.get("entradas_pontuais"):
        frases.append("As entradas foram pontuais, não espalhadas pelo calendário.")
    elif dinamica.get("entradas_recorrentes"):
        frases.append("As entradas apareceram de forma recorrente ao longo do mês.")

    if despesas > 0 and (dinamica.get("dias_com_saida") or 0) <= 3 and len(frases) < 2:
        frases.append("Os gastos concentraram-se em poucos dias — observe possíveis picos.")

    pico_saida = dinamica.get("pico_saida")
    if pico_saida and len(frases) < 2:
        frases.append(f"O maior pico de saída ocorreu em {pico_saida['rotulo']}.")

    return frases[:2]


def interpretacao_acionavel(
    mes_rotulo: str,
    totais: dict[str, Decimal],
    resultado: Decimal,
    comparacao: dict[str, Any],
    top_despesas: list[dict[str, Any]],
    top_receitas: list[dict[str, Any]],
) -> list[str]:
    """1–2 insights específicos baseados nos dados do período."""
    receitas = totais.get("receitas") or Decimal("0")
    despesas = totais.get("despesas") or Decimal("0")

    if receitas == 0 and despesas == 0:
        return []

    itens: list[str] = []

    if top_despesas:
        maior = top_despesas[0]
        pct = maior.get("percentual")
        if pct is not None and pct >= Decimal("30"):
            itens.append(
                f"A maior concentração de gastos está em {maior['nome']} "
                f"({pct:.0f}% das despesas)."
            )
        elif len(itens) == 0:
            itens.append(f"Sua principal categoria de gasto foi {maior['nome']}.")

    if comparacao.get("tem_base") and comparacao.get("despesas_pct") is not None:
        var_d = comparacao["despesas_pct"]
        if var_d >= Decimal("10"):
            itens.append(
                f"Suas despesas totais aumentaram cerca de {var_d:.0f}% "
                "em relação ao mês anterior."
            )
        elif var_d <= Decimal("-10") and len(itens) < 2:
            itens.append(
                f"Suas despesas caíram cerca de {abs(var_d):.0f}% "
                "em relação ao mês anterior."
            )

    if resultado > 0 and top_receitas and len(itens) < 2:
        itens.append(
            f"Seu resultado positivo foi impulsionado por entradas em {top_receitas[0]['nome']}."
        )
    elif resultado < 0 and len(itens) < 2:
        itens.append(
            f"Você fechou {mes_rotulo} no negativo — revise as categorias com maior peso."
        )

    return itens[:2]


def interpretacao_fluxo_periodo(
    totais: dict[str, Decimal],
    serie_fluxo: dict[str, Any],
) -> str:
    """Texto curto que transforma números em entendimento."""
    receitas = totais.get("receitas") or Decimal("0")
    despesas = totais.get("despesas") or Decimal("0")
    resultado = resultado_fluxo(totais)
    liquidos: list[float] = serie_fluxo.get("liquido") or []
    acumulado: list[float] = serie_fluxo.get("acumulado") or []

    if receitas == 0 and despesas == 0:
        return "Nenhuma movimentação registrada neste período."

    dias_positivos = sum(1 for v in liquidos if v > 0)
    total_dias = len(liquidos) or 1

    if resultado > 0 and dias_positivos >= total_dias * 0.5:
        return "Seu fluxo de caixa permaneceu positivo durante a maior parte do período."

    if receitas > 0:
        pct = (despesas / receitas) * 100
        if resultado >= 0:
            if len(acumulado) >= 2 and acumulado[-1] > acumulado[0]:
                return "O saldo acumulado apresentou crescimento consistente."
            return f"As despesas consumiram {pct:.0f}% das receitas registradas."
        return f"As despesas consumiram {pct:.0f}% das receitas — o período fechou no negativo."

    if resultado < 0:
        return "As saídas superaram as entradas neste período."

    return "Receitas e despesas se equilibraram no período."


def nav_qs_extra_filtros(filtros: RelatorioFiltros) -> str:
    """Preserva filtros avançados na navegação por mês (sem datas/preset)."""
    from urllib.parse import urlencode

    params = filtros.to_query_dict()
    params.pop("inicio", None)
    params.pop("fim", None)
    params.pop("preset", None)
    if not params:
        return ""
    return "&" + urlencode(params, doseq=True)


def filtros_mes(
    base: RelatorioFiltros,
    ano: int,
    mes: int,
) -> RelatorioFiltros:
    """Mesmo critério de conta/categoria/tipo, limitado a um mês civil."""
    import calendar

    inicio = date(ano, mes, 1)
    fim = date(ano, mes, calendar.monthrange(ano, mes)[1])
    return RelatorioFiltros(
        data_inicio=inicio,
        data_fim=fim,
        conta_ids=base.conta_ids,
        categoria_ids=base.categoria_ids,
        tipos=base.tipos,
        preset="custom",
        meio_pagamento=base.meio_pagamento,
        modo_data=base.modo_data,
    )
