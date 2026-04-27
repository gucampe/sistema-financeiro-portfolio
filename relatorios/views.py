from datetime import timedelta

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.views.generic import TemplateView

from categorias.models import Categoria
from contas.models import Conta
from transacoes.forms import TransacaoForm
from usuarios.models import Perfil

from relatorios.selectors import transacoes_base_qs
from relatorios.services.agregacoes import (
    aplicar_filtros_relatorio,
    movimento_por_conta,
    orcamento_vs_realizado,
    resumo_comparativo,
    resultado_fluxo,
    saldos_por_conta_totais,
    serie_fluxo_diario,
    top_categorias,
    totais_por_tipo,
)
from relatorios.services.filtros import RelatorioFiltros, parse_comparativo_secundario, parse_relatorio_filtros
from relatorios.services.insights import avaliar_alertas_orcamento, gerar_insights_dashboard


class RelatorioFiltrosMixin(LoginRequiredMixin):
    """Parse único de filtros GET para todas as telas de relatório."""

    def get_filtros(self):
        return parse_relatorio_filtros(self.request.GET, usuario=self.request.user)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        filtros = parse_relatorio_filtros(self.request.GET, usuario=user)
        ctx["filtros"] = filtros
        ctx["filtros_querystring"] = filtros.to_query_string()
        ctx["drill_transacoes_qs"] = filtros.to_drill_transacoes_query_string()
        ctx["contas_ativas"] = Conta.objects.filter(usuario=user, ativa=True).order_by("nome")
        ctx["categorias_filtro"] = (
            Categoria.objects.filter(Q(usuario=user) | Q(padrao=True), ativa=True)
            .order_by("tipo", "nome")
        )
        return ctx


class HomeRelatorioView(RelatorioFiltrosMixin, TemplateView):
    template_name = "relatorios/partials/home.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        filtros = ctx["filtros"]
        qs = aplicar_filtros_relatorio(transacoes_base_qs(user), filtros)

        totais = totais_por_tipo(qs)
        top_d = top_categorias(qs, "despesa", limit=8)
        top_despesas_chart = [
            {
                "nome": x["nome"],
                "total": float(x["total"]),
                "cor": x["cor"] or "#6B7280",
                "pct": float(x["percentual"]),
            }
            for x in top_d[:6]
        ]
        mov_contas = [
            {
                **m,
                "drill_qs": filtros.to_drill_transacoes_periodo_e_conta(m["conta_id"]),
            }
            for m in movimento_por_conta(qs, user)
        ]
        saldos_lista, saldo_patrimonio = saldos_por_conta_totais(user)
        ultimas = qs.order_by("-data", "-id")[:8]
        orc_linhas = orcamento_vs_realizado(user, filtros)
        insights = gerar_insights_dashboard(user, filtros, totais_atual=totais, top_despesa=top_d)
        alertas_orc = avaliar_alertas_orcamento(orc_linhas)

        categorias_despesa = Categoria.objects.filter(
            Q(usuario=user) | Q(padrao=True),
            tipo="despesa",
            ativa=True,
        ).order_by("nome")
        categorias_receita = Categoria.objects.filter(
            Q(usuario=user) | Q(padrao=True),
            tipo="receita",
            ativa=True,
        ).order_by("nome")
        perfil, _ = Perfil.objects.get_or_create(usuario=user)
        initial_tx, tipo_p = perfil.defaults_transacao_form()
        form = TransacaoForm(usuario=user, tipo_inicial=tipo_p, initial=initial_tx)

        ctx.update(
            {
                "totais": totais,
                "resultado_fluxo": resultado_fluxo(totais),
                "top_despesas_categoria": top_d,
                "top_despesas_chart": top_despesas_chart,
                "relatorio_nav": "home",
                "movimento_por_conta": mov_contas,
                "saldos_por_conta": saldos_lista,
                "saldo_patrimonio": saldo_patrimonio,
                "ultimas_transacoes": ultimas,
                "orcamento_linhas": orc_linhas,
                "insights": insights,
                "alertas_orcamento": alertas_orc,
                "categorias_despesa": categorias_despesa,
                "categorias_receita": categorias_receita,
                "form": form,
                "ocultar_valores_dashboard": perfil.ocultar_valores_dashboard,
            }
        )
        return ctx


class FluxoCaixaView(RelatorioFiltrosMixin, TemplateView):
    template_name = "relatorios/fluxo_caixa.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        filtros = ctx["filtros"]
        qs = aplicar_filtros_relatorio(transacoes_base_qs(user), filtros)
        tot = totais_por_tipo(qs)
        ctx.update(
            {
                "serie_fluxo": serie_fluxo_diario(qs, filtros),
                "totais": tot,
                "resultado_fluxo": resultado_fluxo(tot),
                "relatorio_nav": "fluxo_caixa",
            }
        )
        return ctx


class DespesasPorCategoriaView(RelatorioFiltrosMixin, TemplateView):
    template_name = "relatorios/despesas_categoria.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        filtros = ctx["filtros"]
        qs = aplicar_filtros_relatorio(transacoes_base_qs(user), filtros)
        top = top_categorias(qs, "despesa", limit=30)
        ctx.update(
            {
                "top_categorias": top,
                "totais": totais_por_tipo(qs),
                "relatorio_nav": "despesas_categoria",
            }
        )
        return ctx


class ReceitasPorCategoriaView(RelatorioFiltrosMixin, TemplateView):
    template_name = "relatorios/receitas_categoria.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        filtros = ctx["filtros"]
        qs = aplicar_filtros_relatorio(transacoes_base_qs(user), filtros)
        top = top_categorias(qs, "receita", limit=30)
        ctx.update(
            {
                "top_categorias": top,
                "totais": totais_por_tipo(qs),
                "relatorio_nav": "receitas_categoria",
            }
        )
        return ctx


class PorContaView(RelatorioFiltrosMixin, TemplateView):
    template_name = "relatorios/por_conta.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        filtros = ctx["filtros"]
        qs = aplicar_filtros_relatorio(transacoes_base_qs(user), filtros)
        saldos_lista, saldo_total = saldos_por_conta_totais(user)
        mov = [
            {
                **m,
                "drill_qs": filtros.to_drill_transacoes_periodo_e_conta(m["conta_id"]),
            }
            for m in movimento_por_conta(qs, user)
        ]
        ctx.update(
            {
                "movimento_por_conta": mov,
                "saldos_por_conta": saldos_lista,
                "saldo_patrimonio": saldo_total,
                "totais_periodo": totais_por_tipo(qs),
                "relatorio_nav": "por_conta",
            }
        )
        return ctx


class ComparativoView(RelatorioFiltrosMixin, TemplateView):
    template_name = "relatorios/comparativo.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        primario = ctx["filtros"]
        secundario = parse_comparativo_secundario(self.request.GET, usuario=user, primario=primario)
        if secundario is None:
            span = (primario.data_fim - primario.data_inicio).days + 1
            fim_b = primario.data_inicio - timedelta(days=1)
            ini_b = fim_b - timedelta(days=span - 1)
            secundario = RelatorioFiltros(
                data_inicio=ini_b,
                data_fim=fim_b,
                conta_ids=primario.conta_ids,
                categoria_ids=primario.categoria_ids,
                tipos=primario.tipos,
                preset="custom",
                meio_pagamento=primario.meio_pagamento,
                modo_data=primario.modo_data,
            )

        qs_a = aplicar_filtros_relatorio(transacoes_base_qs(user), primario)
        qs_b = aplicar_filtros_relatorio(transacoes_base_qs(user), secundario)
        comp = resumo_comparativo(qs_a, qs_b)

        ctx.update(
            {
                "filtros_a": primario,
                "filtros_b": secundario,
                "filtros_querystring": primario.to_query_string(),
                "comparativo": comp,
                "relatorio_nav": "comparativo",
            }
        )
        return ctx
