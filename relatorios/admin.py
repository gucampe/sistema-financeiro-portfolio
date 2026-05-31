from django.contrib import admin

from relatorios.models import ExportRelatorioJob, OrcamentoCategoria


@admin.register(OrcamentoCategoria)
class OrcamentoCategoriaAdmin(admin.ModelAdmin):
    list_display = (
        "usuario",
        "categoria",
        "valor_planejado",
        "ativo",
        "inicio_ano",
        "inicio_mes",
        "fim_ano",
        "fim_mes",
    )
    list_filter = ("ativo", "inicio_ano", "inicio_mes")
    search_fields = ("usuario__email", "categoria__nome")
    readonly_fields = ("criado_em", "atualizado_em")


@admin.register(ExportRelatorioJob)
class ExportRelatorioJobAdmin(admin.ModelAdmin):
    list_display = ("id", "usuario", "status", "criado_em")
    list_filter = ("status",)
    readonly_fields = ("criado_em", "atualizado_em", "filtros_json", "arquivo", "mensagem_erro")
