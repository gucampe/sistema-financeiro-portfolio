from __future__ import annotations

from decimal import Decimal, InvalidOperation

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
            "inicio_ano",
            "inicio_mes",
            "fim_ano",
            "fim_mes",
            "ativo",
        )
        widgets = {
            "categoria": forms.Select(attrs={"class": INPUT_CONTROL_CLASSES}),
            "inicio_ano": forms.NumberInput(attrs={"class": INPUT_CONTROL_CLASSES, "min": 2000, "max": 2100}),
            "inicio_mes": forms.NumberInput(attrs={"class": INPUT_CONTROL_CLASSES, "min": 1, "max": 12}),
            "fim_ano": forms.NumberInput(attrs={"class": INPUT_CONTROL_CLASSES, "min": 2000, "max": 2100}),
            "fim_mes": forms.NumberInput(attrs={"class": INPUT_CONTROL_CLASSES, "min": 1, "max": 12}),
            "ativo": forms.CheckboxInput(attrs={"class": "rounded border-gray-300 text-brand-600 focus:ring-brand-500"}),
        }

    def __init__(self, *args, usuario=None, **kwargs):
        self.usuario = usuario
        super().__init__(*args, **kwargs)
        if usuario:
            qs = Categoria.objects.filter(usuario=usuario, tipo="despesa", ativa=True).order_by("nome")
            padrao = Categoria.objects.filter(padrao=True, tipo="despesa", ativa=True).order_by("nome")
            self.fields["categoria"].queryset = (qs | padrao).distinct().order_by("nome")
        self.fields["fim_ano"].required = False
        self.fields["fim_mes"].required = False

    def clean(self):
        cleaned = super().clean()
        fim_ano = cleaned.get("fim_ano")
        fim_mes = cleaned.get("fim_mes")
        if (fim_ano is None) ^ (fim_mes is None):
            raise ValidationError("Informe mês e ano de fim, ou deixe ambos vazios.")
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


def parse_mes_ano_post(data, prefix_inicio: str = "inicio", prefix_fim: str = "fim") -> dict:
    """Auxiliar para POST com campos separados mês/ano."""
    out = {}
    for prefix, keys in (
        (prefix_inicio, ("inicio_ano", "inicio_mes")),
        (prefix_fim, ("fim_ano", "fim_mes")),
    ):
        ano = data.get(f"{prefix}_ano") or data.get(keys[0])
        mes = data.get(f"{prefix}_mes") or data.get(keys[1])
        if ano == "":
            ano = None
        if mes == "":
            mes = None
        try:
            out[keys[0]] = int(ano) if ano is not None else None
            out[keys[1]] = int(mes) if mes is not None else None
        except (TypeError, ValueError, InvalidOperation) as exc:
            raise ValidationError("Período inválido.") from exc
    return out
