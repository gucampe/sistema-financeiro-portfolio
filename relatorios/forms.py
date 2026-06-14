from __future__ import annotations

from decimal import Decimal

from django import forms
from django.core.exceptions import ValidationError

from categorias.models import Categoria
from core.forms_ui import INPUT_CONTROL_CLASSES, MOEDA_INPUT_CLASSES, MoedaTextInput
from relatorios.models import OrcamentoCategoria


class OrcamentoCategoriaForm(forms.ModelForm):
    valor_planejado = forms.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=Decimal("0.01"),
        widget=MoedaTextInput(attrs={"class": MOEDA_INPUT_CLASSES, "placeholder": "0,00"}),
        label="Valor mensal",
    )

    class Meta:
        model = OrcamentoCategoria
        fields = (
            "categoria",
            "valor_planejado",
            "ativo",
        )
        widgets = {
            "categoria": forms.Select(attrs={"class": INPUT_CONTROL_CLASSES}),
            "ativo": forms.CheckboxInput(attrs={"class": "rounded border-gray-300 text-brand-600 focus:ring-brand-500"}),
        }

    def __init__(self, *args, usuario=None, **kwargs):
        self.usuario = usuario
        super().__init__(*args, **kwargs)
        if usuario:
            qs = Categoria.objects.filter(usuario=usuario, tipo="despesa", ativa=True).order_by("nome")
            padrao = Categoria.objects.filter(padrao=True, tipo="despesa", ativa=True).order_by("nome")
            self.fields["categoria"].queryset = (qs | padrao).distinct().order_by("nome")

    def clean(self):
        cleaned = super().clean()
        categoria = cleaned.get("categoria")
        if self.usuario and categoria:
            qs = OrcamentoCategoria.objects.filter(usuario=self.usuario, categoria=categoria)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                self.add_error("categoria", "Já existe orçamento para esta categoria.")
        return cleaned

    def save(self, commit=True):
        obj = super().save(commit=False)
        if self.usuario:
            obj.usuario = self.usuario
        if commit:
            obj.save()
        return obj

    def _post_clean(self):
        if self.usuario:
            self.instance.usuario = self.usuario
        super()._post_clean()
