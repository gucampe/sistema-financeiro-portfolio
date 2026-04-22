from django.urls import path

from relatorios.api_views import (
    ApiExportCsvCreateView,
    ApiExportJobDetailView,
    ApiExportJobDownloadView,
    ApiSerieTendenciaView,
    ApiTopCategoriasView,
)
from relatorios.views import (
    ComparativoView,
    DespesasPorCategoriaView,
    FluxoCaixaView,
    HomeRelatorioView,
    PorContaView,
    ReceitasPorCategoriaView,
)

app_name = "relatorios"

urlpatterns = [
    path("relatorios/", HomeRelatorioView.as_view(), name="home"),
    path("relatorios/fluxo-caixa/", FluxoCaixaView.as_view(), name="fluxo_caixa"),
    path("relatorios/despesas-por-categoria/", DespesasPorCategoriaView.as_view(), name="despesas_categoria"),
    path("relatorios/receitas-por-categoria/", ReceitasPorCategoriaView.as_view(), name="receitas_categoria"),
    path("relatorios/por-conta/", PorContaView.as_view(), name="por_conta"),
    path("relatorios/comparativo/", ComparativoView.as_view(), name="comparativo"),
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
