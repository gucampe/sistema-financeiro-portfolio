"""Pipeline HTTP de importação para testes (preview → confirmar, sem UI)."""

from __future__ import annotations

import json

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client
from django.urls import reverse

from contas.models import Conta

_XLSX_CT = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def xlsx_upload(raw: bytes, name: str = "test.xlsx") -> SimpleUploadedFile:
    return SimpleUploadedFile(name, raw, content_type=_XLSX_CT)


def ofx_upload(raw: bytes, name: str = "test.ofx") -> SimpleUploadedFile:
    return SimpleUploadedFile(name, raw, content_type="application/x-ofx")


def linhas_confirmar_padrao_ui(
    preview: dict,
    *,
    categoria_despesa_id: int,
    categoria_receita_id: int,
) -> list[dict]:
    """REGRA-DUP-03: linhas não marcadas como duplicata."""
    linhas = []
    for row in preview["linhas"]:
        if row.get("duplicata_por_fitid") or row.get("duplicata_por_heuristica"):
            continue
        tipo = row["tipo"]
        cat_id = (
            categoria_receita_id
            if tipo in ("receita", "ajuste")
            else categoria_despesa_id
        )
        item = {
            "indice": row["indice"],
            "data": row["data"],
            "valor": row["valor"],
            "tipo": tipo,
            "descricao": row["descricao"],
            "categoria_id": cat_id,
        }
        if row.get("ofx_fitid"):
            item["ofx_fitid"] = row["ofx_fitid"]
        linhas.append(item)
    return linhas


def preview_ofx(client: Client, conta: Conta, raw: bytes) -> tuple[int, dict]:
    r = client.post(
        reverse("transacoes:importar_ofx_preview"),
        {"conta_id": conta.pk, "arquivo": ofx_upload(raw)},
    )
    try:
        body = r.json()
    except Exception:
        body = {"status": "error", "message": r.content.decode("utf-8", errors="replace")}
    return r.status_code, body


def preview_xlsx(client: Client, conta: Conta, raw: bytes) -> tuple[int, dict]:
    r = client.post(
        reverse("transacoes:importar_planilha_preview"),
        {"conta_id": conta.pk, "arquivo": xlsx_upload(raw)},
    )
    try:
        body = r.json()
    except Exception:
        body = {"status": "error", "message": r.content.decode("utf-8", errors="replace")}
    return r.status_code, body


def confirmar(
    client: Client,
    conta: Conta,
    linhas: list[dict],
) -> tuple[int, dict]:
    r = client.post(
        reverse("transacoes:importar_ofx_confirmar"),
        data=json.dumps({"conta_id": conta.pk, "linhas": linhas}),
        content_type="application/json",
    )
    try:
        body = r.json()
    except Exception:
        body = {"status": "error", "message": r.content.decode("utf-8", errors="replace")}
    return r.status_code, body


def importar_ofx_completo(
    client: Client,
    conta: Conta,
    raw: bytes,
    *,
    categoria_despesa_id: int,
    categoria_receita_id: int,
) -> tuple[int, dict, list[dict]]:
    """Preview + confirmar com seleção padrão UI. Retorna (status_confirm, body, linhas)."""
    status, preview = preview_ofx(client, conta, raw)
    if status != 200 or preview.get("status") != "ok":
        return status, preview, []
    linhas = linhas_confirmar_padrao_ui(
        preview,
        categoria_despesa_id=categoria_despesa_id,
        categoria_receita_id=categoria_receita_id,
    )
    st, body = confirmar(client, conta, linhas)
    return st, body, linhas
