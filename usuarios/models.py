from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _
from .managers import UsuarioManager  # Manager customizado

# Mesmos valores que transacoes.Transacao.TIPO_CHOICES (evita import cruzado na carga de apps).
TIPO_TRANSACAO_PADRAO_CHOICES = (
    ("receita", _("Receita")),
    ("despesa", _("Despesa")),
    ("ajuste", _("Ajuste")),
)


class Usuario(AbstractUser):
    username = None  # remove o campo username
    first_name = None  # remove first_name herdado
    last_name = None   # remove last_name herdado
    date_joined = None # substituído por 'criado_em'

    ORIGEM_ADMIN = "admin"
    ORIGEM_PRIMEIROS_DONOS = "primeiros_donos"
    ORIGEM_CHOICES = (
        (ORIGEM_ADMIN, _("Admin")),
        (ORIGEM_PRIMEIROS_DONOS, _("Primeiros Donos")),
    )

    email = models.EmailField(_('E-mail'), unique=True)
    nome = models.CharField(_('Nome completo'), max_length=100)
    data_nascimento = models.DateField(_('Data de nascimento'), null=True, blank=True)
    whatsapp = models.CharField(_('WhatsApp'), max_length=20, blank=True, default="")
    origem = models.CharField(
        _('Origem'),
        max_length=32,
        choices=ORIGEM_CHOICES,
        default=ORIGEM_ADMIN,
        db_index=True,
    )
    criado_em = models.DateTimeField(_('Criado em'), auto_now_add=True)
    atualizado_em = models.DateTimeField(_('Atualizado em'), auto_now=True)
    ativo = models.BooleanField(_('Usuário ativo'), default=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['nome']

    objects = UsuarioManager()

    def __str__(self):
        return f'{self.nome} <{self.email}>'


class Perfil(models.Model):
    """Preferências de produto + avatar; dados pessoais ficam em Usuario."""

    MOEDA_BRL = "BRL"
    MOEDA_USD = "USD"
    MOEDA_CHOICES = (
        (MOEDA_BRL, _("Real (BRL)")),
        (MOEDA_USD, _("Dólar (USD)")),
    )

    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="perfil",
        verbose_name=_("Usuário"),
    )
    foto = models.ImageField(_("Foto de perfil"), upload_to="perfis/fotos/", blank=True, null=True)
    moeda = models.CharField(_("Moeda padrão"), max_length=3, choices=MOEDA_CHOICES, default=MOEDA_BRL)
    tipo_transacao_padrao = models.CharField(
        _("Tipo padrão ao criar transação"),
        max_length=10,
        choices=TIPO_TRANSACAO_PADRAO_CHOICES,
        default="despesa",
    )
    conta_padrao = models.ForeignKey(
        "contas.Conta",
        verbose_name=_("Conta padrão"),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="perfis_conta_padrao",
    )
    categoria_padrao = models.ForeignKey(
        "categorias.Categoria",
        verbose_name=_("Categoria padrão"),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="perfis_categoria_padrao",
    )
    ocultar_valores_dashboard = models.BooleanField(
        _("Ocultar valores nos relatórios"),
        default=False,
        help_text=_("Mascara valores sensíveis na tela inicial."),
    )
    ocultar_atalho_primeiros_passos = models.BooleanField(
        _("Ocultar atalho de primeiros passos"),
        default=False,
        help_text=_("Não mostra o atalho flutuante no dashboard, em qualquer dispositivo."),
    )
    categorizacao_auto_aplicar = models.BooleanField(
        _("Aplicar categorias automaticamente"),
        default=False,
        help_text=_("Preenche a categoria sem confirmação quando a confiança for alta."),
    )
    categorizacao_limiar_auto = models.FloatField(
        _("Limiar de confiança para auto-aplicar"),
        default=0.90,
    )
    categorizacao_contribuir_globais = models.BooleanField(
        _("Contribuir com dados anonimizados"),
        default=False,
        help_text=_("Permite usar padrões agregados (sem descrições) para melhorar sugestões globais."),
    )

    class Meta:
        verbose_name = _("Perfil")
        verbose_name_plural = _("Perfis")

    def __str__(self):
        return f"Perfil de {self.usuario_id}"

    def defaults_transacao_form(self) -> tuple[dict, str]:
        """Valores iniciais e tipo para `TransacaoForm` (modal / relatórios)."""
        tipo = self.tipo_transacao_padrao or "despesa"
        initial: dict = {"tipo": tipo}
        if self.conta_padrao_id:
            initial["conta"] = self.conta_padrao_id
        cat = self.categoria_padrao
        if cat:
            compativel = (tipo in ("receita", "despesa") and cat.tipo == tipo) or (
                tipo == "ajuste" and cat.tipo == "receita"
            )
            if compativel:
                initial["categoria"] = cat.pk
        return initial, tipo


class AuditLog(models.Model):
    """Registro mínimo de ações sensíveis (LGPD / segurança)."""

    ACAO_DELETE_ACCOUNT = "delete_account"
    ACAO_EXPORT_REQUESTED = "export_requested"
    ACAO_PASSWORD_CHANGE = "password_change"
    ACAO_LOGIN_FAILED = "login_failed"
    ACAO_SIGNUP = "signup"

    ACAO_CHOICES = (
        (ACAO_DELETE_ACCOUNT, "Exclusão de conta"),
        (ACAO_EXPORT_REQUESTED, "Exportação solicitada"),
        (ACAO_PASSWORD_CHANGE, "Alteração de senha"),
        (ACAO_LOGIN_FAILED, "Falha de login"),
        (ACAO_SIGNUP, "Cadastro"),
    )

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
    )
    acao = models.CharField(max_length=40, choices=ACAO_CHOICES, db_index=True)
    ip = models.GenericIPAddressField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = _("Log de auditoria")
        verbose_name_plural = _("Logs de auditoria")
        ordering = ["-criado_em"]
        indexes = [
            models.Index(fields=["acao", "criado_em"], name="usuarios_audit_acao_dt"),
        ]

    def __str__(self):
        return f"{self.acao} ({self.usuario_id})"


class LeadPrimeirosDonos(models.Model):
    """Lead da página de captura do programa Primeiros Donos."""

    nome = models.CharField(_("Nome"), max_length=120)
    email = models.EmailField(_("E-mail"), unique=True)
    whatsapp = models.CharField(_("WhatsApp"), max_length=20)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="leads_primeiros_donos",
        verbose_name=_("Usuário"),
    )
    criado_em = models.DateTimeField(_("Criado em"), auto_now_add=True, db_index=True)
    atualizado_em = models.DateTimeField(_("Atualizado em"), auto_now=True)

    class Meta:
        verbose_name = _("Lead Primeiros Donos")
        verbose_name_plural = _("Leads Primeiros Donos")
        ordering = ["-criado_em"]

    def __str__(self):
        return f"{self.nome} <{self.email}>"


class Consentimento(models.Model):
    """Evidência de clickwrap (aceite de Termos e Privacidade). Não é a base legal do tratamento."""

    CANAL_CAPTURA = "captura"
    CANAL_CHOICES = (
        (CANAL_CAPTURA, _("Captura Primeiros Donos")),
    )

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="consentimentos",
        verbose_name=_("Usuário"),
    )
    email = models.EmailField(_("E-mail"))
    canal = models.CharField(_("Canal"), max_length=32, choices=CANAL_CHOICES, default=CANAL_CAPTURA)
    versao_termos = models.CharField(_("Versão dos Termos"), max_length=32)
    versao_privacidade = models.CharField(_("Versão da Privacidade"), max_length=32)
    ip = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(_("User-Agent"), max_length=256, blank=True, default="")
    aceito_em = models.DateTimeField(_("Aceito em"), auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = _("Aceite de documentos")
        verbose_name_plural = _("Aceites de documentos")
        ordering = ["-aceito_em"]

    def __str__(self):
        return f"{self.email} ({self.canal} {self.aceito_em:%Y-%m-%d})"
