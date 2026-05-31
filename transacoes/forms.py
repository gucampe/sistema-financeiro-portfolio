# transacoes/forms.py
from django import forms

from core.forms_ui import INPUT_CONTROL_CLASSES, MOEDA_INPUT_CLASSES, MoedaTextInput
from core.moeda import parse_decimal_moeda_br

from cartoes.models import Cartao
from .models import Transacao
from categorias.models import Categoria
from contas.models import Conta


class TransacaoForm(forms.ModelForm):
    class Meta:
        model = Transacao
        fields = ["tipo", "conta", "cartao", "categoria", "descricao", "valor", "data"]
        widgets = {
            "data": forms.DateInput(attrs={"type": "date"}),
            "valor": MoedaTextInput(attrs={"class": MOEDA_INPUT_CLASSES}),
        }

    def __init__(self, *args, **kwargs):
        self.usuario = kwargs.pop("usuario", None)
        self.tipo_inicial = kwargs.pop("tipo_inicial", "despesa")
        super().__init__(*args, **kwargs)

        if self.usuario is not None:
            from django.db.models import Q

            self.fields["conta"].queryset = Conta.objects.filter(
                usuario=self.usuario, ativa=True
            ).order_by("nome")
            self.fields["cartao"].queryset = (
                Cartao.objects.filter(usuario=self.usuario, ativa=True)
                .select_related("conta_padrao")
                .order_by("nome")
            )
            # Categorias do cadastro são receita/despesa; "ajuste" usa categorias de receita (ex.: saldo inicial).
            tipo_cat = self.tipo_inicial
            if tipo_cat == "ajuste":
                tipo_cat = "receita"
            self.fields["categoria"].queryset = Categoria.objects.filter(
                Q(usuario=self.usuario) | Q(padrao=True),
                tipo=tipo_cat,
                ativa=True,
            ).order_by("nome")
        else:
            self.fields["conta"].queryset = Conta.objects.none()
            self.fields["cartao"].queryset = Cartao.objects.none()
            self.fields["categoria"].queryset = Categoria.objects.none()

        self.fields["conta"].empty_label = "Selecione uma conta"
        self.fields["conta"].required = False
        self.fields["conta"].widget = forms.HiddenInput()
        self.fields["conta"].label = ""
        self.fields["cartao"].empty_label = "Selecione um cartão"
        self.fields["cartao"].required = False
        self.fields["cartao"].widget = forms.HiddenInput()
        self.fields["cartao"].label = ""
        self.fields["categoria"].empty_label = "Selecione uma categoria"
        self.fields["categoria"].required = True

        for name, field in self.fields.items():
            if name in ("conta", "cartao"):
                continue
            if name == "valor":
                field.widget.attrs.setdefault("class", MOEDA_INPUT_CLASSES)
                continue
            field.widget.attrs.update({"class": INPUT_CONTROL_CLASSES})

    def clean_valor(self):
        raw = self.data.get("valor")
        if raw in (None, ""):
            raise forms.ValidationError("Informe o valor.")
        try:
            valor = parse_decimal_moeda_br(raw)
        except ValueError:
            raise forms.ValidationError("Valor inválido.")
        if valor < 0:
            raise forms.ValidationError("O valor não pode ser negativo.")
        return valor

    def clean_conta(self):
        conta = self.cleaned_data.get("conta")
        if not conta:
            return None
        if self.usuario and conta.usuario_id != self.usuario.id:
            raise forms.ValidationError("Conta inválida.")
        if not conta.ativa:
            raise forms.ValidationError("Conta inválida ou inativa.")
        return conta

    def clean_cartao(self):
        cartao = self.cleaned_data.get("cartao")
        if not cartao:
            return None
        if self.usuario and cartao.usuario_id != self.usuario.id:
            raise forms.ValidationError("Cartão inválido.")
        if not cartao.ativa:
            raise forms.ValidationError("Cartão inválido ou inativo.")
        return cartao

    def clean_categoria(self):
        cat = self.cleaned_data.get("categoria")
        if not cat:
            raise forms.ValidationError("Selecione uma categoria.")

        tipo_transacao = self.cleaned_data.get("tipo") or self.tipo_inicial
        if self.usuario and not (cat.padrao or cat.usuario_id == self.usuario.id):
            raise forms.ValidationError("Categoria inválida.")
        if tipo_transacao == "ajuste":
            if cat.tipo != "receita":
                raise forms.ValidationError(
                    "Para ajuste, selecione uma categoria de receita (ex.: saldo inicial)."
                )
        elif cat.tipo != tipo_transacao:
            raise forms.ValidationError("Categoria deve ser do mesmo tipo da transação.")
        if not cat.ativa:
            raise forms.ValidationError("Categoria inválida ou arquivada.")
        return cat

    def clean(self):
        cleaned = super().clean()
        if cleaned is None:
            return cleaned
        cartao = cleaned.get("cartao")
        if cartao:
            pad = cartao.conta_padrao
            if pad is None:
                raise forms.ValidationError(
                    {"cartao": "Este cartão não possui conta padrão configurada."}
                )
            cleaned["conta"] = pad
        conta = cleaned.get("conta")
        if not conta:
            raise forms.ValidationError({"conta": "Selecione uma conta ou cartão."})
        if self.usuario and conta.usuario_id != self.usuario.id:
            raise forms.ValidationError({"conta": "Conta inválida."})
        if not conta.ativa:
            raise forms.ValidationError({"conta": "Conta inválida ou inativa."})
        return cleaned
