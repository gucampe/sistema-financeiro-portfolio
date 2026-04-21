from django.urls import path

from .views import home

app_name = "relatorios"

urlpatterns = [
    path("relatorios/", home, name="home"),
]
