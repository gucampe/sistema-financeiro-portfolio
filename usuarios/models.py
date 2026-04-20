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
    

    email = models.EmailField(_('E-mail'), unique=True)
    nome = models.CharField(_('Nome completo'), max_length=100)
    data_nascimento = models.DateField(_('Data de nascimento'), null=True, blank=True)
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
        _("Ocultar valores no dashboard"),
        default=False,
        help_text=_("Mascara valores sensíveis na tela inicial."),
    )

    class Meta:
        verbose_name = _("Perfil")
        verbose_name_plural = _("Perfis")

    def __str__(self):
        return f"Perfil de {self.usuario_id}"

    def defaults_transacao_form(self) -> tuple[dict, str]:
        """Valores iniciais e tipo para `TransacaoForm` (modal / dashboard)."""
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
