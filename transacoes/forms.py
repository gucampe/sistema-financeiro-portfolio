# transacoes/forms.py
from django import forms
from .models import Transacao
from categorias.models import Categoria
from contas.models import Conta


class TransacaoForm(forms.ModelForm):
    class Meta:
        model = Transacao
        fields = ["tipo", "conta", "categoria", "descricao", "valor", "data"]
        widgets = {
            "data": forms.DateInput(attrs={"type": "date"}),
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
            self.fields["categoria"].queryset = Categoria.objects.none()

        self.fields["conta"].empty_label = "Selecione uma conta"
        self.fields["conta"].required = True
        self.fields["conta"].error_messages["required"] = "Selecione uma conta."
        self.fields["categoria"].empty_label = "Selecione uma categoria"
        self.fields["categoria"].required = True

        for field in self.fields.values():
            field.widget.attrs.update({
                "class": "w-full px-4 py-2 border rounded-md"
            })

    def clean_conta(self):
        conta = self.cleaned_data.get("conta")
        if not conta:
            raise forms.ValidationError("Selecione uma conta.")
        if self.usuario and conta.usuario_id != self.usuario.id:
            raise forms.ValidationError("Conta inválida.")
        if not conta.ativa:
            raise forms.ValidationError("Conta inválida ou inativa.")
        return conta

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
