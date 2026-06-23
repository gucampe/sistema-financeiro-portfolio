from django import forms
from django.db.models import Q

from categorias.models import Categoria
from categorizacao.models import RegraCategorizacao
from categorizacao.services.normalizer import normalizar_padrao_regra


class RegraCategorizacaoForm(forms.ModelForm):
    class Meta:
        model = RegraCategorizacao
        fields = [
            "tipo_regra",
            "padrao",
            "categoria",
            "tipo_transacao",
            "prioridade",
            "confianca_base",
        ]
        widgets = {
            "padrao": forms.TextInput(
                attrs={
                    "class": (
                        "w-full rounded-lg border border-gray-300 px-3 py-2 text-sm "
                        "focus:outline-none focus:ring-2 focus:ring-emerald-500"
                    ),
                    "placeholder": "Ex: IFOOD ou uber",
                }
            ),
            "tipo_regra": forms.Select(
                attrs={
                    "class": (
                        "w-full rounded-lg border border-gray-300 px-3 py-2 text-sm "
                        "focus:outline-none focus:ring-2 focus:ring-emerald-500"
                    )
                }
            ),
            "categoria": forms.Select(
                attrs={
                    "class": (
                        "w-full rounded-lg border border-gray-300 px-3 py-2 text-sm "
                        "focus:outline-none focus:ring-2 focus:ring-emerald-500"
                    )
                }
            ),
            "tipo_transacao": forms.Select(
                attrs={
                    "class": (
                        "w-full rounded-lg border border-gray-300 px-3 py-2 text-sm "
                        "focus:outline-none focus:ring-2 focus:ring-emerald-500"
                    )
                }
            ),
            "prioridade": forms.NumberInput(
                attrs={
                    "class": (
                        "w-full rounded-lg border border-gray-300 px-3 py-2 text-sm "
                        "focus:outline-none focus:ring-2 focus:ring-emerald-500"
                    )
                }
            ),
            "confianca_base": forms.NumberInput(
                attrs={
                    "class": (
                        "w-full rounded-lg border border-gray-300 px-3 py-2 text-sm "
                        "focus:outline-none focus:ring-2 focus:ring-emerald-500"
                    ),
                    "step": "0.01",
                    "min": "0",
                    "max": "1",
                }
            ),
        }

    def __init__(self, *args, usuario=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.usuario = usuario
        if usuario:
            self.fields["categoria"].queryset = Categoria.objects.filter(
                Q(usuario=usuario) | Q(padrao=True),
                ativa=True,
            ).order_by("tipo", "nome")

    def clean(self):
        cleaned = super().clean()
        padrao = cleaned.get("padrao", "")
        if padrao:
            cleaned["padrao_normalizado"] = normalizar_padrao_regra(padrao)
        return cleaned

    def save(self, commit=True):
        obj = super().save(commit=False)
        obj.usuario = self.usuario
        obj.padrao_normalizado = normalizar_padrao_regra(obj.padrao)
        obj.origem = "manual"
        obj.ativa = True
        if commit:
            obj.save()
        return obj
