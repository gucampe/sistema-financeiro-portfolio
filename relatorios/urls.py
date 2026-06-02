from django.urls import path

from relatorios.api_views import (
    ApiExportCsvCreateView,
    ApiExportJobDetailView,
    ApiExportJobDownloadView,
    ApiSerieTendenciaView,
    ApiTopCategoriasView,
)
from relatorios.views import (
    DespesasPorCategoriaView,
    FluxoCaixaView,
    HomeRelatorioView,
    OrcamentosView,
    PorContaView,
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
    path("relatorios/orcamentos/salvar/", salvar_orcamento, name="orcamentos_salvar"),
    path("relatorios/orcamentos/<int:pk>/toggle-ativo/", toggle_orcamento_ativo, name="orcamentos_toggle_ativo"),
    path("relatorios/api/serie-tendencia/", ApiSerieTendenciaView.as_view(), name="api_serie_tendencia"),
    path("relatorios/api/top-categorias/", ApiTopCategoriasView.as_view(), name="api_top_categorias"),
    path("relatorios/api/export/csv/", ApiExportCsvCreateView.as_view(), name="api_export_csv"),
    path("relatorios/api/export/jobs/<int:pk>/", ApiExportJobDetailView.as_view(), name="api_export_job_detail"),
    path(
        "relatorios/api/export/jobs/<int:pk>/download/",
        ApiExportJobDownloadView.as_view(),
        name="api_export_job_download",
    ),
]
