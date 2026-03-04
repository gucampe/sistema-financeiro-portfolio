from django import forms
from .models import Conta


class ContaForm(forms.ModelForm):
    class Meta:
        model = Conta
        fields = ["nome", "tipo"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "w-full px-4 py-2 border rounded-lg")
