from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Usuario

# Register your models here.
admin.site.register(Usuario)


class UsuarioAdmin(UserAdmin):
    model = Usuario
    list_display = ('email', 'nome', 'is_staff', 'is_active',)
    list_filter = ('is_staff', 'is_active')
    search_fields = ('email', 'nome')
    ordering = ('email',)
    fieldsets = (
        (None, {'fields': ('email', 'password', 'nome', 'data_nascimento',)}),
        ('Permissões', {'fields': ('is_staff', 'is_active', 'is_superuser', 'groups', 'user_permissions')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'nome', 'password1', 'password2', 'is_staff', 'is_active')}
        ),
    )