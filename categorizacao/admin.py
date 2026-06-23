from django.contrib import admin
from django.db.models import Avg, Count
from django.urls import path
from django.shortcuts import render
from datetime import date

from django.conf import settings

from categorizacao.models import (
    AgregacaoMerchantGlobal,
    EventoCategorizacao,
    LLMRequestLog,
    MemoriaMerchantUsuario,
    MerchantGlobal,
    ModeloClassificacaoUsuario,
    RegraCategorizacao,
)


@admin.register(LLMRequestLog)
class LLMRequestLogAdmin(admin.ModelAdmin):
    list_display = (
        "criado_em",
        "usuario",
        "model",
        "success",
        "cache_hit",
        "latency_ms",
        "input_tokens",
        "output_tokens",
        "cost_usd_estimated",
        "gate_reason",
    )
    list_filter = ("success", "cache_hit", "model")
    readonly_fields = (
        "usuario",
        "model",
        "latency_ms",
        "input_tokens",
        "output_tokens",
        "success",
        "cache_hit",
        "gate_reason",
        "descricao_hash",
        "cost_usd_estimated",
        "criado_em",
    )
    search_fields = ("usuario__email", "model", "gate_reason")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(MerchantGlobal)
class MerchantGlobalAdmin(admin.ModelAdmin):
    list_display = ("canonical_name", "categoria_padrao_nome", "tipo", "prioridade", "ativo")
    list_filter = ("tipo", "ativo")
    search_fields = ("canonical_name", "categoria_padrao_nome")


@admin.register(RegraCategorizacao)
class RegraCategorizacaoAdmin(admin.ModelAdmin):
    list_display = (
        "padrao",
        "tipo_regra",
        "categoria",
        "usuario",
        "origem",
        "prioridade",
        "confianca_base",
        "ativa",
    )
    list_filter = ("tipo_regra", "origem", "ativa", "usuario")
    search_fields = ("padrao", "padrao_normalizado")


@admin.register(MemoriaMerchantUsuario)
class MemoriaMerchantUsuarioAdmin(admin.ModelAdmin):
    list_display = ("usuario", "merchant_key", "categoria", "confirmacoes", "score")
    search_fields = ("merchant_key", "usuario__email")


@admin.register(EventoCategorizacao)
class EventoCategorizacaoAdmin(admin.ModelAdmin):
    list_display = ("criado_em", "usuario", "acao", "fonte", "confianca", "merchant_key")
    list_filter = ("acao", "fonte")
    readonly_fields = ("criado_em",)


@admin.register(ModeloClassificacaoUsuario)
class ModeloClassificacaoUsuarioAdmin(admin.ModelAdmin):
    list_display = ("usuario", "versao", "amostras_treino", "treinado_em")
    readonly_fields = ("artefato",)


@admin.register(AgregacaoMerchantGlobal)
class AgregacaoMerchantGlobalAdmin(admin.ModelAdmin):
    list_display = (
        "merchant_key",
        "categoria_padrao_nome",
        "ocorrencias",
        "usuarios_distintos",
        "atualizado_em",
    )


def metricas_categorizacao_view(request):
    por_fonte = (
        EventoCategorizacao.objects.filter(acao__in=("aceita", "auto_aplicada"))
        .values("fonte")
        .annotate(total=Count("id"), confianca_media=Avg("confianca"))
        .order_by("-total")
    )
    por_acao = (
        EventoCategorizacao.objects.values("acao")
        .annotate(total=Count("id"))
        .order_by("-total")
    )
    llm_hoje = LLMRequestLog.objects.filter(criado_em__date=date.today())
    llm_stats = {
        "total": llm_hoje.count(),
        "sucesso": llm_hoje.filter(success=True).count(),
        "cache_hits": llm_hoje.filter(cache_hit=True).count(),
        "custo_usd": sum(llm_hoje.values_list("cost_usd_estimated", flat=True)),
        "tokens_in": sum(llm_hoje.values_list("input_tokens", flat=True)),
        "tokens_out": sum(llm_hoje.values_list("output_tokens", flat=True)),
    }
    llm_admin = {
        "habilitado": bool(getattr(settings, "ENABLE_CATEGORIZACAO_LLM", False)),
        "modelo": getattr(settings, "CATEGORIZACAO_LLM_MODEL", ""),
        "mock": bool(getattr(settings, "CATEGORIZACAO_LLM_USE_MOCK", False)),
        "mostrar_badge": bool(getattr(settings, "CATEGORIZACAO_LLM_MOSTRAR_BADGE", True)),
    }
    return render(
        request,
        "admin/categorizacao/metricas.html",
        {
            "por_fonte": por_fonte,
            "por_acao": por_acao,
            "llm_stats": llm_stats,
            "llm_admin": llm_admin,
            "title": "Métricas categorização",
        },
    )


def get_admin_urls(urls):
    custom = [
        path(
            "categorizacao/metricas/",
            admin.site.admin_view(metricas_categorizacao_view),
            name="categorizacao_metricas",
        ),
    ]
    return custom + urls


_original_admin_get_urls = admin.site.get_urls


def _patched_admin_get_urls():
    return get_admin_urls(_original_admin_get_urls())


admin.site.get_urls = _patched_admin_get_urls
