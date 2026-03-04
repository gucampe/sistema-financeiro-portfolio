from django.contrib import admin

from .models import Conta


@admin.register(Conta)
class ContaAdmin(admin.ModelAdmin):
    list_display = ("nome", "tipo", "usuario", "ativa", "get_saldo_atual", "criada_em")

    @admin.display(description="Saldo atual")
    def get_saldo_atual(self, obj):
        return obj.saldo_atual_calc
    list_filter = ("tipo", "ativa")
    search_fields = ("nome",)
