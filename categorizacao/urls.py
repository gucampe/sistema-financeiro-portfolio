from django.urls import path

from categorizacao import views

app_name = "categorizacao"

urlpatterns = [
    path("sugerir/", views.sugerir_categoria, name="sugerir_categoria"),
    path("categorizar-import-batch/", views.categorizar_import_batch, name="categorizar_import_batch"),
    path("categorizar-import-cancel/", views.categorizar_import_cancel, name="categorizar_import_cancel"),
    path("regras/", views.minhas_regras, name="minhas_regras"),
    path("regras/<int:pk>/excluir/", views.excluir_regra, name="excluir_regra"),
    path("revisar-diversos/", views.revisar_diversos, name="revisar_diversos"),
]
