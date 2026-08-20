from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _

from .models import AuditLog, Consentimento, LeadPrimeirosDonos, Perfil, Usuario


class PerfilInline(admin.StackedInline):
    model = Perfil
    fk_name = "usuario"
    can_delete = False
    max_num = 1


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    model = Usuario
    inlines = (PerfilInline,)

    list_display = ('email', 'nome', 'origem', 'is_staff', 'is_superuser', 'ativo')
    list_filter = ('is_staff', 'is_superuser', 'ativo', 'origem')
    search_fields = ('email', 'nome', 'whatsapp')
    ordering = ('email',)

    readonly_fields = ('criado_em', 'atualizado_em', 'last_login')

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        (_('Informações pessoais'), {'fields': ('nome', 'whatsapp', 'data_nascimento', 'origem')}),
        (_('Permissões'), {'fields': ('is_staff', 'is_superuser', 'groups', 'user_permissions', 'ativo')}),
        (_('Datas importantes'), {'fields': ('last_login', 'criado_em', 'atualizado_em')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'nome', 'password1', 'password2', 'is_staff', 'is_superuser', 'ativo')}
        ),
    )


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("acao", "usuario", "ip", "criado_em")
    list_filter = ("acao", "criado_em")
    search_fields = ("usuario__email", "ip")
    readonly_fields = ("usuario", "acao", "ip", "metadata", "criado_em")
    ordering = ("-criado_em",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(LeadPrimeirosDonos)
class LeadPrimeirosDonosAdmin(admin.ModelAdmin):
    list_display = ("nome", "email", "whatsapp", "usuario", "criado_em")
    search_fields = ("nome", "email", "whatsapp")
    readonly_fields = ("criado_em", "atualizado_em")
    ordering = ("-criado_em",)
    raw_id_fields = ("usuario",)


@admin.register(Consentimento)
class ConsentimentoAdmin(admin.ModelAdmin):
    list_display = ("email", "canal", "versao_termos", "versao_privacidade", "aceito_em")
    list_filter = ("canal",)
    search_fields = ("email", "usuario__email")
    readonly_fields = (
        "usuario",
        "email",
        "canal",
        "versao_termos",
        "versao_privacidade",
        "ip",
        "user_agent",
        "aceito_em",
    )
    ordering = ("-aceito_em",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
