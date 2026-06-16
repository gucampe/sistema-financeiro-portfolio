from django.urls import path

from relatorios.api_views import (
    ApiExportCsvCreateView,
    ApiExportJobCancelView,
    ApiExportJobCreateView,
    ApiExportJobDetailView,
    ApiExportJobDownloadView,
    ApiExportJobListView,
    ApiExportJobShareDownloadView,
    ApiSerieTendenciaView,
    ApiTopCategoriasView,
)
from relatorios.views import (
    DespesasPorCategoriaView,
    ExportHubView,
    FluxoCaixaView,
    HomeRelatorioView,
    OrcamentosView,
    PorContaView,
    excluir_orcamento,
    salvar_orcamento,
    toggle_ocultar_valores_dashboard,
    toggle_orcamento_ativo,
)

app_name = "relatorios"

urlpatterns = [
    path("relatorios/", HomeRelatorioView.as_view(), name="home"),
    path("relatorios/toggle-ocultar-valores/", toggle_ocultar_valores_dashboard, name="toggle_ocultar_valores"),
    path("relatorios/fluxo-caixa/", FluxoCaixaView.as_view(), name="fluxo_caixa"),
    path("relatorios/despesas-por-categoria/", DespesasPorCategoriaView.as_view(), name="despesas_categoria"),
    path("relatorios/por-conta/", PorContaView.as_view(), name="por_conta"),
    path("relatorios/orcamentos/", OrcamentosView.as_view(), name="orcamentos"),
    path("relatorios/exportar/", ExportHubView.as_view(), name="exportar"),
    path("relatorios/orcamentos/salvar/", salvar_orcamento, name="orcamentos_salvar"),
    path("relatorios/orcamentos/<int:pk>/toggle-ativo/", toggle_orcamento_ativo, name="orcamentos_toggle_ativo"),
    path("relatorios/orcamentos/<int:pk>/excluir/", excluir_orcamento, name="orcamentos_excluir"),
    path("relatorios/api/serie-tendencia/", ApiSerieTendenciaView.as_view(), name="api_serie_tendencia"),
    path("relatorios/api/top-categorias/", ApiTopCategoriasView.as_view(), name="api_top_categorias"),
    path("relatorios/api/export/jobs/", ApiExportJobCreateView.as_view(), name="api_export_jobs_create"),
    path("relatorios/api/export/jobs/list/", ApiExportJobListView.as_view(), name="api_export_jobs_list"),
    path("relatorios/api/export/csv/", ApiExportCsvCreateView.as_view(), name="api_export_csv"),
    path("relatorios/api/export/jobs/<int:pk>/", ApiExportJobDetailView.as_view(), name="api_export_job_detail"),
    path(
        "relatorios/api/export/jobs/<int:pk>/cancelar/",
        ApiExportJobCancelView.as_view(),
        name="api_export_job_cancel",
    ),
    path(
        "relatorios/api/export/jobs/<int:pk>/download/",
        ApiExportJobDownloadView.as_view(),
        name="api_export_job_download",
    ),
    path(
        "relatorios/api/export/share/<uuid:token>/download/",
        ApiExportJobShareDownloadView.as_view(),
        name="api_export_share_download",
    ),
]
