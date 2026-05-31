from datetime import date, timedelta

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_POST
from django.views.generic import TemplateView
from django.contrib.auth.decorators import login_required

from categorias.models import Categoria
from contas.models import Conta
from transacoes.forms import TransacaoForm
from usuarios.models import Perfil
from usuarios.utils import primeiro_nome

from relatorios.forms import OrcamentoCategoriaForm
from relatorios.models import OrcamentoCategoria
from relatorios.services.orcamentos import (
    MESES_PT,
    historico_utilizacao_categoria,
    listar_orcamentos_mes,
    navegacao_mes_context,
    painel_mes_orcamento,
    resumo_linhas_orcamento,
    usuario_tem_orcamentos_cadastrados,
    usuario_tem_orcamentos_vigentes_mes,
)
from relatorios.selectors import transacoes_base_qs
from relatorios.services.agregacoes import (
    aplicar_filtros_relatorio,
    movimento_por_conta,
    resumo_comparativo,
    resultado_fluxo,
    saldos_por_conta_totais,
    serie_fluxo_diario,
    top_categorias,
    totais_por_tipo,
)
from relatorios.services.filtros import RelatorioFiltros, parse_comparativo_secundario, parse_relatorio_filtros
from relatorios.services.dashboard import (
    comparacao_mensal,
    fluxo_caixa_futuro_dashboard,
    contas_dashboard,
    metas_financeiras,
    query_transacoes_mes_atual,
    resumo_cartoes_dashboard,
    rotulo_periodo_atual,
    saudacao_periodo,
    top_despesas_mes_atual,
)


class RelatorioFiltrosMixin(LoginRequiredMixin):
    """Parse único de filtros GET para todas as telas de relatório."""

    def get_filtros(self):
        return parse_relatorio_filtros(self.request.GET, usuario=self.request.user)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        filtros = parse_relatorio_filtros(self.request.GET, usuario=user)
        ctx["filtros"] = filtros
        ctx["filtros_ativos_count"] = filtros.contagem_filtros_ativos()
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

        comparacao = comparacao_mensal(user)
        totais_mes = comparacao["atual"]
        patrimonio = contas_dashboard(user, limit=5)
        cartoes = resumo_cartoes_dashboard(user)
        fluxo_caixa = fluxo_caixa_futuro_dashboard(user)
        metas = metas_financeiras(user)
        tem_orcamentos_cadastrados = usuario_tem_orcamentos_cadastrados(user)
        hoje = date.today()
        tem_orcamentos_vigentes = usuario_tem_orcamentos_vigentes_mes(user, hoje.year, hoje.month)
        top_despesas_mes = top_despesas_mes_atual(user, limit=5)
        top_despesas_chart = [
            {
                "nome": x["nome"],
                "total": float(x["total"]),
                "cor": x["cor"] or "#6B7280",
                "pct": float(x["percentual"]),
                "categoria_id": x["categoria_id"],
            }
            for x in top_despesas_mes
        ]
        resultado_mes = comparacao["resultado_atual"]

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
                "relatorio_nav": "home",
                "saudacao": saudacao_periodo(),
                "nome_usuario": primeiro_nome(user.nome),
                "rotulo_periodo": rotulo_periodo_atual(),
                "comparacao_mensal": comparacao,
                "totais_mes": totais_mes,
                "resultado_mes": resultado_mes,
                "patrimonio": patrimonio,
                "cartoes_dashboard": cartoes,
                "fluxo_caixa": fluxo_caixa,
                "metas_financeiras": metas,
                "tem_orcamentos_cadastrados": tem_orcamentos_cadastrados,
                "tem_orcamentos_vigentes": tem_orcamentos_vigentes,
                "top_despesas_mes": top_despesas_mes,
                "top_despesas_chart": top_despesas_chart,
                "periodo_transacoes_qs": query_transacoes_mes_atual(),
                "icone_choices_instituicoes": [
                    "nubank", "itau", "santander", "bradesco", "bb", "caixa",
                    "inter", "sicredi", "sicoob", "picpay", "mercadopago",
                ],
                "categorias_despesa": categorias_despesa,
                "categorias_receita": categorias_receita,
                "form": form,
                "ocultar_valores_dashboard": perfil.ocultar_valores_dashboard,
            }
        )
        return ctx


@login_required
@require_POST
def toggle_ocultar_valores_dashboard(request):
    perfil, _ = Perfil.objects.get_or_create(usuario=request.user)
    perfil.ocultar_valores_dashboard = not perfil.ocultar_valores_dashboard
    perfil.save(update_fields=["ocultar_valores_dashboard"])
    return JsonResponse({"ocultar": perfil.ocultar_valores_dashboard})


def _parse_ano_mes(request, default: date | None = None) -> tuple[int, int]:
    ref = default or date.today()
    try:
        ano = int(request.GET.get("ano") or request.POST.get("ref_ano") or ref.year)
        mes = int(request.GET.get("mes") or request.POST.get("ref_mes") or ref.month)
        if not (1 <= mes <= 12):
            raise ValueError
    except (TypeError, ValueError):
        ano, mes = ref.year, ref.month
    return ano, mes


class OrcamentosView(LoginRequiredMixin, TemplateView):
    template_name = "relatorios/orcamentos.html"

    def get_context_data(self, **kwargs):
        import calendar

        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        filtros = parse_relatorio_filtros(self.request.GET, usuario=user)
        ano, mes = _parse_ano_mes(self.request)
        linhas = listar_orcamentos_mes(user, ano, mes, incluir_inativos=True)
        resumo = resumo_linhas_orcamento(linhas)
        painel_mes = painel_mes_orcamento(linhas, resumo)
        nav_mes = navegacao_mes_context(ano, mes)

        historico_por_categoria: dict[int, list] = {}
        orcamento_ids = [l.orcamento_id for l in linhas if l.orcamento_id]
        orcamentos_map = {
            o.pk: o
            for o in OrcamentoCategoria.objects.filter(usuario=user, pk__in=orcamento_ids)
        }
        for linha in linhas:
            if linha.orcamento_id and linha.planejado > 0:
                historico_por_categoria[linha.categoria_id] = historico_utilizacao_categoria(
                    user, linha.categoria_id, meses=3
                )
            linha.historico = historico_por_categoria.get(linha.categoria_id, [])
            linha.orcamento_obj = orcamentos_map.get(linha.orcamento_id)

        inicio_mes = date(ano, mes, 1)
        fim_mes = date(ano, mes, calendar.monthrange(ano, mes)[1])
        drill_qs = f"inicio={inicio_mes.isoformat()}&fim={fim_mes.isoformat()}&tipo=despesa"

        ctx.update(
            {
                "relatorio_nav": "orcamentos",
                "filtros_querystring": filtros.to_query_string(),
                "ano": ano,
                "mes": mes,
                "mes_rotulo": MESES_PT[mes - 1],
                "linhas_orcamento": linhas,
                "resumo_orcamento": resumo,
                "painel_mes": painel_mes,
                "nav_mes": nav_mes,
                "data_mes": nav_mes["data_mes"],
                "ano_anterior": nav_mes["ano_anterior"],
                "mes_anterior": nav_mes["mes_anterior"],
                "ano_proximo": nav_mes["ano_proximo"],
                "mes_proximo": nav_mes["mes_proximo"],
                "ano_hoje": nav_mes["ano_hoje"],
                "mes_hoje": nav_mes["mes_hoje"],
                "meses_dropdown": nav_mes["meses_dropdown"],
                "nav_qs_extra": nav_mes["nav_qs_extra"],
                "tem_orcamentos": usuario_tem_orcamentos_cadastrados(user),
                "historico_por_categoria": historico_por_categoria,
                "drill_mes_qs": drill_qs,
                "form_orcamento": OrcamentoCategoriaForm(
                    usuario=user,
                    initial={"inicio_ano": ano, "inicio_mes": mes, "ativo": True},
                ),
            }
        )
        return ctx


@login_required
@require_POST
def salvar_orcamento(request):
    user = request.user
    orcamento_id = request.POST.get("orcamento_id") or None
    instance = None
    if orcamento_id:
        instance = get_object_or_404(OrcamentoCategoria, pk=orcamento_id, usuario=user)
    elif request.POST.get("categoria"):
        instance = OrcamentoCategoria.objects.filter(
            usuario=user, categoria_id=request.POST.get("categoria")
        ).first()

    form = OrcamentoCategoriaForm(request.POST, instance=instance, usuario=user)
    if not form.is_valid():
        errors = {k: [str(e) for e in v] for k, v in form.errors.items()}
        return JsonResponse({"status": "erro", "errors": errors}, status=400)

    obj = form.save()
    ano, mes = _parse_ano_mes(request)
    linhas = listar_orcamentos_mes(user, ano, mes, incluir_inativos=True)
    linha = next((l for l in linhas if l.orcamento_id == obj.pk), None)
    payload = linha.as_dict() if linha else {"orcamento_id": obj.pk}
    return JsonResponse({"status": "ok", "linha": payload})


@login_required
@require_POST
def toggle_orcamento_ativo(request, pk):
    orcamento = get_object_or_404(OrcamentoCategoria, pk=pk, usuario=request.user)
    orcamento.ativo = not orcamento.ativo
    try:
        orcamento.save()
    except ValidationError as exc:
        msgs = exc.message_dict if hasattr(exc, "message_dict") else {"__all__": exc.messages}
        return JsonResponse({"status": "erro", "errors": msgs}, status=400)
    return JsonResponse({"status": "ok", "ativo": orcamento.ativo, "id": orcamento.pk})


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
