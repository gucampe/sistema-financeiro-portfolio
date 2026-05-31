"""Classes Tailwind reutilizáveis para widgets de formulário Django."""

from django import forms

# Componente `.input` definido em static/css/input.css (@layer components).
INPUT_CONTROL_CLASSES = "input"
MOEDA_INPUT_CLASSES = "input input-moeda"


class MoedaTextInput(forms.TextInput):
    """Input de moeda pt-BR; inicializado por static/js/moeda_input.js."""

    def __init__(self, attrs=None):
        base = {
            "type": "text",
            "inputmode": "decimal",
            "autocomplete": "off",
            "data-moeda-input": "1",
        }
        if attrs:
            base.update(attrs)
        super().__init__(attrs=base)


class IsoDateInput(forms.DateInput):
    """DateInput que sempre grava value em ISO (YYYY-MM-DD) para type=date."""

    input_type = "date"

    def format_value(self, value):
        if value in (None, ""):
            return ""
        if hasattr(value, "isoformat"):
            return value.isoformat()
        s = str(value).strip()
        if len(s) >= 10 and s[4:5] == "-":
            return s[:10]
        return s

CHECKBOX_CONTROL_CLASSES = (
    "h-4 w-4 rounded border border-gray-300 text-brand-600 shadow-sm "
    "focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-0"
)

FILE_INPUT_CONTROL_CLASSES = (
    "block w-full rounded-lg border border-gray-300 bg-white text-sm text-fg-muted shadow-sm "
    "outline-none transition file:mr-3 file:rounded-lg file:border-0 file:bg-gray-100 file:px-3 "
    "file:py-2 file:text-fg focus:border-brand-500 focus:outline-none focus:ring-2 "
    "focus:ring-brand-500 focus:ring-offset-0"
)
