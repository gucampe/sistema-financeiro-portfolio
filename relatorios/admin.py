from django.contrib import admin

from relatorios.models import ExportJob, OrcamentoCategoria

# Alias admin
ExportRelatorioJob = ExportJob


@admin.register(OrcamentoCategoria)
class OrcamentoCategoriaAdmin(admin.ModelAdmin):
    list_display = (
        "usuario",
        "categoria",
        "valor_planejado",
        "ativo",
        "criado_em",
    )
    list_filter = ("ativo",)
    search_fields = ("usuario__email", "categoria__nome")
    readonly_fields = ("criado_em", "atualizado_em")


@admin.register(ExportJob)
class ExportJobAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "usuario",
        "dominio",
        "formato",
        "status",
        "linhas_count",
        "tamanho_bytes",
        "tentativas",
        "criado_em",
        "finalizado_em",
    )
    list_filter = ("status", "dominio", "formato")
    search_fields = ("usuario__email", "task_id")
    readonly_fields = (
        "criado_em",
        "atualizado_em",
        "filtros_json",
        "arquivo",
        "mensagem_erro",
        "erro_interno",
        "token_download",
        "iniciado_em",
        "finalizado_em",
    )
