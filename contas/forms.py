from django import forms

from core.forms_ui import INPUT_CONTROL_CLASSES

from .models import Conta


class ContaForm(forms.ModelForm):
    class Meta:
        model = Conta
        fields = ["nome", "tipo"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", INPUT_CONTROL_CLASSES)
