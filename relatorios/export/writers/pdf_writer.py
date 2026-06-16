from __future__ import annotations

from django.template import TemplateDoesNotExist, TemplateSyntaxError
from django.template.loader import render_to_string

from relatorios.export.base import ExportResult


def write_pdf_from_template(template_name: str, context: dict, nome_arquivo: str) -> ExportResult:
  try:
    html = render_to_string(template_name, context)
  except (TemplateDoesNotExist, TemplateSyntaxError, KeyError, AttributeError) as exc:
    raise RuntimeError(f"Erro ao montar o PDF: {exc}") from exc

  try:
    from weasyprint import HTML
  except ImportError as exc:
    raise RuntimeError("WeasyPrint não está instalado.") from exc

  try:
    content = HTML(string=html).write_pdf()
  except Exception as exc:
    raise RuntimeError(f"Erro ao gerar o PDF: {exc}") from exc
  nome = nome_arquivo if nome_arquivo.endswith(".pdf") else f"{nome_arquivo}.pdf"
  return ExportResult(
    content=content,
    nome_arquivo=nome,
    linhas_count=0,
    tamanho_bytes=len(content),
    content_type="application/pdf",
  )
