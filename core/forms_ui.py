"""Classes Tailwind reutilizáveis para widgets de formulário Django."""

# Componente `.input` definido em static/css/input.css (@layer components).
INPUT_CONTROL_CLASSES = "input"

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
