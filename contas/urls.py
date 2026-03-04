from django.urls import path
from . import views

app_name = "contas"

urlpatterns = [
    path("", views.contas_home, name="home"),
    path("salvar/", views.salvar_conta, name="salvar"),
    path("<int:id>/arquivar/", views.arquivar_conta, name="arquivar"),
    path("<int:id>/reativar/", views.reativar_conta, name="reativar"),
]
