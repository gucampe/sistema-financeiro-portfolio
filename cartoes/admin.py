from django.contrib import admin

from .models import Cartao


@admin.register(Cartao)
class CartaoAdmin(admin.ModelAdmin):
    list_display = ("nome", "usuario", "limite", "dia_fechamento", "dia_vencimento", "conta_padrao", "ativa")
    list_filter = ("ativa",)
    search_fields = ("nome", "usuario__email", "usuario__username")
