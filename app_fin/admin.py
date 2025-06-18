from django.contrib import admin

# Register your models here.
from .models import Usuario
class UsuarioAdmin(admin.ModelAdmin):
    list_display = ('nome', 'email', 'data_registro')
    search_fields = ('nome', 'email')
    list_filter = ('data_registro',)
    ordering = ('-data_registro',)
    
admin.site.register(Usuario, UsuarioAdmin)