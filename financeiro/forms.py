# financeiro/forms.py
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
        super().__init__(*args, **kwargs)

        if self.usuario is not None:
            self.fields["categoria"].queryset = (
                Categoria.objects.filter(usuario=self.usuario) |
                Categoria.objects.filter(padrao=True)
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

        # segurança: a categoria deve ser do usuário ou padrão
        if self.usuario and not (cat.padrao or cat.usuario_id == self.usuario.id):
            raise forms.ValidationError("Categoria inválida.")
        return cat
