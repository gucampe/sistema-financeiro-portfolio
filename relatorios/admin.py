from django.contrib import admin

from relatorios.models import ExportRelatorioJob, OrcamentoCategoria


@admin.register(OrcamentoCategoria)
class OrcamentoCategoriaAdmin(admin.ModelAdmin):
    list_display = ("usuario", "categoria", "ano", "mes", "valor_planejado")
    list_filter = ("ano", "mes")
    search_fields = ("usuario__email", "categoria__nome")


@admin.register(ExportRelatorioJob)
class ExportRelatorioJobAdmin(admin.ModelAdmin):
    list_display = ("id", "usuario", "status", "criado_em")
    list_filter = ("status",)
    readonly_fields = ("criado_em", "atualizado_em", "filtros_json", "arquivo", "mensagem_erro")
