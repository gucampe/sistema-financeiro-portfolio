# financeiro/forms.py
from django import forms
from .models import Transacao

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
        usuario = kwargs.pop("usuario")  # passamos o usuário para filtrar categorias
        super().__init__(*args, **kwargs)
        self.fields["categoria"].queryset = Categoria.objects.filter(
            usuario=usuario
        ) | Categoria.objects.filter(padrao=True)
        self.fields["categoria"].required = True
