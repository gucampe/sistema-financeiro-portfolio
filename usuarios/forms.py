from django import forms
from django.contrib.auth.forms import PasswordChangeForm
from django.core.exceptions import ValidationError
from django.db.models import Q

from categorias.models import Categoria
from contas.models import Conta

from .models import Perfil, Usuario


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
        widget=forms.FileInput(
            attrs={
                "class": (
                    "block w-full rounded-lg border border-gray-300 bg-white text-sm text-gray-600 "
                    "shadow-sm outline-none transition file:mr-3 file:rounded-lg file:border-0 "
                    "file:bg-gray-100 file:px-3 file:py-2 focus:border-emerald-500 focus:outline-none "
                    "focus:ring-2 focus:ring-emerald-500 focus:ring-offset-0"
                ),
                "accept": "image/*",
            }
        ),
    )

    class Meta:
        model = Usuario
        fields = ("nome", "data_nascimento")
        widgets = {
            "nome": forms.TextInput(
                attrs={
                    "class": (
                        "w-full rounded-lg border border-gray-300 bg-white px-3 py-2 shadow-sm "
                        "outline-none transition focus:border-emerald-500 focus:outline-none "
                        "focus:ring-2 focus:ring-emerald-500 focus:ring-offset-0"
                    )
                }
            ),
            "data_nascimento": forms.DateInput(
                attrs={
                    "type": "date",
                    "class": (
                        "w-full rounded-lg border border-gray-300 bg-white px-3 py-2 shadow-sm "
                        "outline-none transition focus:border-emerald-500 focus:outline-none "
                        "focus:ring-2 focus:ring-emerald-500 focus:ring-offset-0"
                    ),
                }
            ),
        }

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
        self.order_fields(("nome", "data_nascimento", "foto"))

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
        )
        widgets = {
            "moeda": forms.Select(
                attrs={
                    "class": (
                        "w-full rounded-lg border border-gray-300 bg-white px-3 py-2 shadow-sm "
                        "outline-none transition focus:border-emerald-500 focus:outline-none "
                        "focus:ring-2 focus:ring-emerald-500 focus:ring-offset-0"
                    )
                }
            ),
            "tipo_transacao_padrao": forms.Select(
                attrs={
                    "class": (
                        "w-full rounded-lg border border-gray-300 bg-white px-3 py-2 shadow-sm "
                        "outline-none transition focus:border-emerald-500 focus:outline-none "
                        "focus:ring-2 focus:ring-emerald-500 focus:ring-offset-0"
                    )
                }
            ),
            "conta_padrao": forms.Select(
                attrs={
                    "class": (
                        "w-full rounded-lg border border-gray-300 bg-white px-3 py-2 shadow-sm "
                        "outline-none transition focus:border-emerald-500 focus:outline-none "
                        "focus:ring-2 focus:ring-emerald-500 focus:ring-offset-0"
                    )
                }
            ),
            "categoria_padrao": forms.Select(
                attrs={
                    "class": (
                        "w-full rounded-lg border border-gray-300 bg-white px-3 py-2 shadow-sm "
                        "outline-none transition focus:border-emerald-500 focus:outline-none "
                        "focus:ring-2 focus:ring-emerald-500 focus:ring-offset-0"
                    )
                }
            ),
            "ocultar_valores_dashboard": forms.CheckboxInput(
                attrs={
                    "class": (
                        "h-4 w-4 rounded border border-gray-300 text-emerald-600 shadow-sm "
                        "focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:ring-offset-0"
                    )
                }
            ),
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
        css = (
            "w-full rounded-lg border border-gray-300 bg-white px-3 py-2 shadow-sm outline-none "
            "transition focus:border-emerald-500 focus:outline-none focus:ring-2 "
            "focus:ring-emerald-500 focus:ring-offset-0"
        )
        for f in self.fields.values():
            f.widget.attrs.setdefault("class", css)
