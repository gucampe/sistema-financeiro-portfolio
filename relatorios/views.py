from datetime import date

from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_POST
from django.views.generic import TemplateView

from categorias.models import Categoria
from contas.models import Conta
from usuarios.models import Perfil

from relatorios.forms import OrcamentoCategoriaForm
from relatorios.models import OrcamentoCategoria
from relatorios.services.fluxo_caixa import (
    destaques_fluxo_periodo,
    dinamica_fluxo_periodo,
    filtros_mes,
    interpretacao_dinamica_fluxo,
    resumo_minimo_periodo,
)
from relatorios.services.orcamentos import (
    MESES_PT,
    _filtros_orcamento_despesas,
    historico_utilizacao_categoria,
    listar_orcamentos,
    referencia_mes_orcamento,
)
from relatorios.selectors import transacoes_base_qs
from relatorios.services.agregacoes import (
    aplicar_filtros_relatorio,
    resultado_fluxo,
    serie_fluxo_diario,
    top_categorias,
    totais_por_tipo,
)
from relatorios.services.despesas_categoria import montar_analise_despesas_categoria
from relatorios.services.por_conta import montar_analise_por_conta
from relatorios.services.filtros import parse_relatorio_filtros
from relatorios.services.dashboard_context import montar_contexto_dashboard
from relatorios.services.orcamentos_context import montar_contexto_orcamentos
from relatorios.services.request_cache import RelatorioRequestCache


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
        cache = RelatorioRequestCache(self.request.user)
        ctx.update(
            montar_contexto_dashboard(
                self.request.user,
                cache,
                categorias_preloaded=ctx.get("categorias_filtro"),
            )
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


class OrcamentosView(RelatorioFiltrosMixin, TemplateView):
    template_name = "relatorios/orcamentos.html"

    def get_template_names(self):
        if getattr(self.request, "htmx", False):
            return ["relatorios/partials/orcamentos_linhas.html"]
        return [self.template_name]

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        cache = RelatorioRequestCache(self.request.user)
        ctx.update(montar_contexto_orcamentos(self.request.user, ctx["filtros"], cache=cache))
        return ctx


@login_required
def historico_categoria_orcamento(request, categoria_id: int):
    """Partial HTMX: histórico de 3 meses para uma categoria (lazy)."""
    get_object_or_404(
        Categoria.objects.filter(Q(usuario=request.user) | Q(padrao=True)),
        pk=categoria_id,
    )
    cache = RelatorioRequestCache(request.user)
    historico = historico_utilizacao_categoria(
        request.user, categoria_id, meses=3, cache=cache
    )
    return render(
        request,
        "relatorios/partials/orcamento_historico_categoria.html",
        {"historico": historico, "categoria_id": categoria_id},
    )


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
    base_filtros = parse_relatorio_filtros(request.GET, usuario=user)
    if not (request.GET.get("inicio") or request.GET.get("preset")):
        ano, mes = _parse_ano_mes(request)
        from relatorios.services.orcamentos import filtros_mes as filtros_mes_orc

        base_filtros = filtros_mes_orc(ano, mes)
    filtros_periodo = _filtros_orcamento_despesas(base_filtros)
    ano_ref, mes_ref = referencia_mes_orcamento(base_filtros)
    linhas = listar_orcamentos(
        user,
        filtros_periodo,
        ano_ref=ano_ref,
        mes_ref=mes_ref,
        incluir_inativos=False,
        exibir_inativos=True,
    )
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


@login_required
@require_POST
def excluir_orcamento(request, pk):
    orcamento = get_object_or_404(OrcamentoCategoria, pk=pk, usuario=request.user)
    orcamento_id = orcamento.pk
    orcamento.delete()
    return JsonResponse({"status": "ok", "id": orcamento_id})


class FluxoCaixaView(RelatorioFiltrosMixin, TemplateView):
    template_name = "relatorios/fluxo_caixa.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        base_filtros = ctx["filtros"]
        if self.request.GET.get("ano") and self.request.GET.get("mes"):
            ano, mes = _parse_ano_mes(self.request, default=base_filtros.data_inicio)
            filtros = filtros_mes(base_filtros, ano, mes)
        else:
            filtros = base_filtros
            ano, mes = filtros.data_inicio.year, filtros.data_inicio.month
        qs = aplicar_filtros_relatorio(transacoes_base_qs(user), filtros)
        tot = totais_por_tipo(qs)
        serie = serie_fluxo_diario(qs, filtros)
        resultado = resultado_fluxo(tot)
        destaques = destaques_fluxo_periodo(qs, filtros, serie)
        dinamica = dinamica_fluxo_periodo(serie, destaques)
        mes_rotulo = MESES_PT[mes - 1]

        ctx["filtros"] = filtros
        ctx["filtros_querystring"] = filtros.to_query_string()
        ctx["drill_transacoes_qs"] = filtros.to_drill_transacoes_query_string()
        ctx.update(
            {
                "serie_fluxo": serie,
                "totais": tot,
                "resultado_fluxo": resultado,
                "destaques_fluxo": destaques,
                "resumo_minimo": resumo_minimo_periodo(serie, resultado),
                "dinamica": dinamica,
                "interpretacao": interpretacao_dinamica_fluxo(dinamica, tot),
                "top_despesas": top_categorias(qs, "despesa", limit=4),
                "top_receitas": top_categorias(qs, "receita", limit=4),
                "relatorio_nav": "fluxo_caixa",
                "ano": ano,
                "mes": mes,
                "mes_rotulo": mes_rotulo,
            }
        )
        return ctx


class DespesasPorCategoriaView(RelatorioFiltrosMixin, TemplateView):
    template_name = "relatorios/despesas_categoria.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        filtros = ctx["filtros"]
        analise = montar_analise_despesas_categoria(user, filtros)
        qs = aplicar_filtros_relatorio(transacoes_base_qs(user), filtros)
        ctx.update(
            {
                "analise_categorias": analise,
                "hero_categorias": analise["hero"],
                "categorias": analise["categorias"],
                "grafico_categorias": analise["grafico"],
                "insights_categorias": analise["insights"],
                "totais": totais_por_tipo(qs),
                "relatorio_nav": "despesas_categoria",
            }
        )
        return ctx


class PorContaView(RelatorioFiltrosMixin, TemplateView):
    template_name = "relatorios/por_conta.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        filtros = ctx["filtros"]
        analise = montar_analise_por_conta(user, filtros)
        ctx.update(
            {
                "analise_contas": analise,
                "hero_contas": analise["hero"],
                "contas": analise["contas"],
                "grafico_contas": analise["grafico"],
                "insights_contas": analise["insights"],
                "relatorio_nav": "por_conta",
            }
        )
        return ctx


class ExportHubView(RelatorioFiltrosMixin, TemplateView):
    template_name = "relatorios/export/hub.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["relatorio_nav"] = "exportar"
        return ctx
