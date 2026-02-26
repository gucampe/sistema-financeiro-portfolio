# transacoes/forms.py
from django import forms
from .models import Transacao
from categorias.models import Categoria

class TransacaoForm(forms.ModelForm):
    class Meta:
        model = Transacao
        fields = ["tipo", "categoria", "descricao", "valor", "data"]
        widgets = {
            "data": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, **kwargs):
        self.usuario = kwargs.pop("usuario", None)
        self.tipo_inicial = kwargs.pop("tipo_inicial", "despesa")
        super().__init__(*args, **kwargs)

        if self.usuario is not None:
            from django.db.models import Q
            self.fields["categoria"].queryset = Categoria.objects.filter(
                Q(usuario=self.usuario) | Q(padrao=True),
                tipo=self.tipo_inicial,
                ativa=True
            ).order_by("nome")
        else:
            self.fields["categoria"].queryset = Categoria.objects.none()

        self.fields["categoria"].empty_label = "Selecione uma categoria"
        self.fields["categoria"].required = True

        for field in self.fields.values():
            field.widget.attrs.update({
                "class": "w-full px-4 py-2 border rounded-md"
            })

    def clean_categoria(self):
        cat = self.cleaned_data.get("categoria")
        if not cat:
            raise forms.ValidationError("Selecione uma categoria.")

        tipo_transacao = self.cleaned_data.get("tipo") or self.tipo_inicial
        if self.usuario and not (cat.padrao or cat.usuario_id == self.usuario.id):
            raise forms.ValidationError("Categoria inválida.")
        if cat.tipo != tipo_transacao:
            raise forms.ValidationError("Categoria deve ser do mesmo tipo da transação.")
        if not cat.ativa:
            raise forms.ValidationError("Categoria inválida ou arquivada.")
        return cat
