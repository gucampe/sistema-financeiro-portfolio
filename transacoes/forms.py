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
            if tipo_cat in ("ajuste", "transferencia"):
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
        if tipo_transacao in ("ajuste", "transferencia"):
            if cat.tipo != "receita":
                raise forms.ValidationError(
                    "Para ajuste/transferência, selecione uma categoria de receita."
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
        if cleaned.get("tipo") == "transferencia":
            raise forms.ValidationError(
                "Use o fluxo de transferência (origem e destino) para este tipo."
            )
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

    def _post_clean(self):
        # Se o formulário já é inválido (ex.: tipo=transferencia), não rode
        # full_clean do model — campos transfer_id/papel não existem no form e
        # gerariam ValueError/HTTP 500 em vez de 400 com mensagem clara.
        if self.errors:
            return
        super()._post_clean()


class TransferenciaForm(forms.Form):
    """Formulário dedicado à transferência entre contas (dupla partida + transfer_id)."""

    conta_origem = forms.ModelChoiceField(
        queryset=Conta.objects.none(),
        empty_label="Conta de origem",
        required=True,
    )
    conta_destino = forms.ModelChoiceField(
        queryset=Conta.objects.none(),
        empty_label="Conta de destino",
        required=True,
    )
    valor = forms.CharField(widget=MoedaTextInput(attrs={"class": MOEDA_INPUT_CLASSES}))
    descricao = forms.CharField(max_length=255, required=False)
    data = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}))
    transfer_id = forms.UUIDField(required=False, widget=forms.HiddenInput())

    def __init__(self, *args, **kwargs):
        self.usuario = kwargs.pop("usuario", None)
        super().__init__(*args, **kwargs)
        qs = Conta.objects.none()
        if self.usuario is not None:
            qs = Conta.objects.filter(usuario=self.usuario, ativa=True).order_by("nome")
        self.fields["conta_origem"].queryset = qs
        self.fields["conta_destino"].queryset = qs
        for name, field in self.fields.items():
            if name in ("transfer_id", "valor"):
                continue
            field.widget.attrs.update({"class": INPUT_CONTROL_CLASSES})

    def clean_valor(self):
        raw = self.cleaned_data.get("valor")
        if raw in (None, ""):
            raise forms.ValidationError("Informe o valor.")
        try:
            valor = parse_decimal_moeda_br(raw)
        except ValueError:
            raise forms.ValidationError("Valor inválido.")
        if valor <= 0:
            raise forms.ValidationError("O valor deve ser maior que zero.")
        return valor

    def clean(self):
        cleaned = super().clean()
        if cleaned is None:
            return cleaned
        origem = cleaned.get("conta_origem")
        destino = cleaned.get("conta_destino")
        if origem and destino and origem.pk == destino.pk:
            raise forms.ValidationError(
                {"conta_destino": "Conta de origem e destino devem ser diferentes."}
            )
        return cleaned
