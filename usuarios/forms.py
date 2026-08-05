from django import forms
from django.contrib.auth.forms import PasswordChangeForm
from django.core.exceptions import ValidationError
from django.db.models import Q

from categorias.models import Categoria
from contas.models import Conta
from core.forms_ui import (
    CHECKBOX_CONTROL_CLASSES,
    FILE_INPUT_CONTROL_CLASSES,
    INPUT_CONTROL_CLASSES,
    IsoDateInput,
)

from .models import LeadPrimeirosDonos, Perfil, Usuario


def categoria_compativel_com_tipo_transacao_padrao(categoria: Categoria, tipo_tx: str) -> bool:
    """
    Receita/despesa: tipos devem coincidir.
    Ajuste: categorias do cadastro são só receita/despesa; alinhamos ao import OFX (categoria tipo receita).
    """
    if tipo_tx in ("receita", "despesa"):
        return categoria.tipo == tipo_tx
    if tipo_tx == "ajuste":
        return categoria.tipo == "receita"
    return False


class DadosPessoaisForm(forms.ModelForm):
    _max_foto_bytes = 2 * 1024 * 1024
    _tipos_mime_foto = {"image/jpeg", "image/png", "image/webp", "image/gif"}

    foto = forms.ImageField(
        label="Foto de perfil",
        required=False,
        widget=forms.FileInput(attrs={"class": FILE_INPUT_CONTROL_CLASSES, "accept": "image/*"}),
    )
    data_nascimento = forms.DateField(
        label="Data de nascimento",
        required=False,
        input_formats=["%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"],
        widget=IsoDateInput(
            format="%Y-%m-%d",
            attrs={"class": INPUT_CONTROL_CLASSES},
        ),
    )

    class Meta:
        model = Usuario
        fields = ("nome", "data_nascimento")
        widgets = {
            "nome": forms.TextInput(attrs={"class": INPUT_CONTROL_CLASSES}),
        }

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
        self.order_fields(("nome", "data_nascimento", "foto"))

    @property
    def data_nascimento_valor_iso(self):
        """Valor para o atributo value do input type=date (sempre YYYY-MM-DD)."""
        if self.is_bound:
            raw = (self.data.get("data_nascimento") or "").strip()
            if raw:
                return raw[:10]
        if self.instance and self.instance.pk and self.instance.data_nascimento:
            return self.instance.data_nascimento.isoformat()
        return ""

    def clean(self):
        cleaned = super().clean()
        # Campo vazio no POST não deve apagar data já salva (input sem value no navegador).
        if self.instance.pk and self.instance.data_nascimento:
            posted = (self.data.get("data_nascimento") or "").strip()
            if not posted:
                cleaned["data_nascimento"] = self.instance.data_nascimento
        return cleaned

    def clean_foto(self):
        foto = self.cleaned_data.get("foto")
        if not foto:
            return foto
        if foto.size > self._max_foto_bytes:
            raise ValidationError("A imagem deve ter no máximo 2 MB.")
        content_type = getattr(foto, "content_type", None) or getattr(
            getattr(foto, "file", None), "content_type", None
        )
        if content_type and content_type not in self._tipos_mime_foto:
            raise ValidationError("Use JPEG, PNG, WebP ou GIF.")
        return foto


class PreferenciasFinanceirasForm(forms.ModelForm):
    class Meta:
        model = Perfil
        fields = (
            "moeda",
            "tipo_transacao_padrao",
            "conta_padrao",
            "categoria_padrao",
            "ocultar_valores_dashboard",
            "categorizacao_auto_aplicar",
            "categorizacao_limiar_auto",
            "categorizacao_contribuir_globais",
        )
        widgets = {
            "moeda": forms.Select(attrs={"class": INPUT_CONTROL_CLASSES}),
            "tipo_transacao_padrao": forms.Select(attrs={"class": INPUT_CONTROL_CLASSES}),
            "conta_padrao": forms.Select(attrs={"class": INPUT_CONTROL_CLASSES}),
            "categoria_padrao": forms.Select(attrs={"class": INPUT_CONTROL_CLASSES}),
            "ocultar_valores_dashboard": forms.CheckboxInput(attrs={"class": CHECKBOX_CONTROL_CLASSES}),
            "categorizacao_auto_aplicar": forms.CheckboxInput(attrs={"class": CHECKBOX_CONTROL_CLASSES}),
            "categorizacao_limiar_auto": forms.NumberInput(
                attrs={"class": INPUT_CONTROL_CLASSES, "step": "0.01", "min": "0.5", "max": "1"}
            ),
            "categorizacao_contribuir_globais": forms.CheckboxInput(attrs={"class": CHECKBOX_CONTROL_CLASSES}),
        }

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
        if user is None:
            self.fields["conta_padrao"].queryset = Conta.objects.none()
            self.fields["categoria_padrao"].queryset = Categoria.objects.none()
            return

        self.fields["conta_padrao"].queryset = Conta.objects.filter(usuario=user, ativa=True).order_by("nome")
        self.fields["conta_padrao"].required = False
        self.fields["conta_padrao"].empty_label = "Nenhuma"
        self.fields["categoria_padrao"].empty_label = "Nenhuma"
        self.fields["categoria_padrao"].queryset = Categoria.objects.filter(
            Q(usuario=user) | Q(padrao=True),
            ativa=True,
        ).order_by("tipo", "nome")
        self.fields["categoria_padrao"].required = False

    def clean_conta_padrao(self):
        conta = self.cleaned_data.get("conta_padrao")
        if not conta:
            return conta
        if self.user and conta.usuario_id != self.user.id:
            raise ValidationError("Conta inválida.")
        if not conta.ativa:
            raise ValidationError("Conta inativa.")
        return conta

    def clean_categoria_padrao(self):
        cat = self.cleaned_data.get("categoria_padrao")
        if not cat:
            return cat
        if self.user and not (cat.padrao or cat.usuario_id == self.user.id):
            raise ValidationError("Categoria inválida.")
        if not cat.ativa:
            raise ValidationError("Categoria inativa.")
        return cat

    def clean(self):
        cleaned = super().clean()
        tipo = cleaned.get("tipo_transacao_padrao")
        cat = cleaned.get("categoria_padrao")
        if tipo and cat and not categoria_compativel_com_tipo_transacao_padrao(cat, tipo):
            self.add_error(
                "categoria_padrao",
                "A categoria padrão deve ser compatível com o tipo de transação padrão (para Ajuste, use uma categoria de receita).",
            )
        return cleaned


class ConfiguracoesPasswordChangeForm(PasswordChangeForm):
    """Mesmo comportamento do PasswordChangeForm, com widgets alinhados ao restante da página."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Mesmo padding horizontal/vertical dos demais inputs; !pr-12 reserva área do botão “olho”.
        css = f"{INPUT_CONTROL_CLASSES} !pr-12"
        for f in self.fields.values():
            f.widget.attrs.setdefault("class", css)
        # Regras exibidas no template (painel interativo); validadores do Django permanecem ativos.
        self.fields["new_password1"].help_text = ""
        # Evita foco automático em "senha antiga" ao abrir a página de configurações.
        self.fields["old_password"].widget.attrs.pop("autofocus", None)


class CapturaLeadForm(forms.ModelForm):
    """Formulário da página de captura — Primeiros Donos."""

    class Meta:
        model = LeadPrimeirosDonos
        fields = ("nome", "email", "whatsapp")
        widgets = {
            "nome": forms.TextInput(
                attrs={
                    "class": "input w-full",
                    "placeholder": "Seu nome",
                    "autocomplete": "name",
                    "required": True,
                }
            ),
            "email": forms.EmailInput(
                attrs={
                    "class": "input w-full",
                    "placeholder": "seu@email.com",
                    "autocomplete": "email",
                    "required": True,
                    "inputmode": "email",
                }
            ),
            "whatsapp": forms.TextInput(
                attrs={
                    "class": "input w-full",
                    "placeholder": "(11) 99999-9999",
                    "autocomplete": "tel",
                    "inputmode": "tel",
                    "required": True,
                    "maxlength": "16",
                }
            ),
        }

    def clean_nome(self):
        nome = (self.cleaned_data.get("nome") or "").strip()
        if len(nome) < 2:
            raise ValidationError("Informe seu nome.")
        return nome

    def clean_email(self):
        email = (self.cleaned_data.get("email") or "").strip().lower()
        # Permite reenvio: update_or_create na view atualiza o lead existente.
        return email

    def validate_unique(self):
        # Unicidade tratada na view via update_or_create.
        return

    def clean_whatsapp(self):
        raw = (self.cleaned_data.get("whatsapp") or "").strip()
        digits = "".join(ch for ch in raw if ch.isdigit())
        if len(digits) < 10 or len(digits) > 13:
            raise ValidationError("Informe um WhatsApp válido com DDD.")
        return raw
