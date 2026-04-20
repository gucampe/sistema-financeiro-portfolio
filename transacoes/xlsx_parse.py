"""
Parser de planilha .xlsx padronizada (sem Django).

Primeira aba, linha 1: cabeçalhos exatos data | descricao | valor.
Linhas 2+: lançamentos. Linhas totalmente vazias são ignoradas.
"""

from __future__ import annotations

import io
from datetime import date, datetime, time
from typing import Any

from openpyxl import Workbook, load_workbook

from .ofx_parse import LinhaOfx, valor_e_tipo_de_importacao

# Ordem e texto exatos da linha de cabeçalho (colunas A, B, C).
PLANILHA_CABECALHOS: tuple[str, str, str] = ("data", "descricao", "valor")


def _normalizar_cabecalho_celula(val: Any) -> str:
    if val is None:
        return ""
    s = str(val).strip().casefold()
    return s


def _linha_cabecalho_valida(cells: tuple[Any, Any, Any]) -> bool:
    return tuple(_normalizar_cabecalho_celula(c) for c in cells) == PLANILHA_CABECALHOS


def _celula_para_data(val: Any, num_linha: int) -> date:
    if val is None or (isinstance(val, str) and not val.strip()):
        raise ValueError(f"Linha {num_linha}: data ausente.")
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, date):
        return val
    # openpyxl pode ler hora pura em alguns casos raros
    if isinstance(val, time):
        raise ValueError(f"Linha {num_linha}: data inválida (hora sem data).")
    s = str(val).strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Linha {num_linha}: data inválida (use YYYY-MM-DD).")


def _celula_para_descricao(val: Any, num_linha: int) -> str:
    if val is None:
        desc = ""
    else:
        desc = str(val).strip()
    if not desc:
        desc = "Sem descrição"
    if len(desc) > 255:
        desc = desc[:252] + "..."
    return desc


def _celula_vazia(val: Any) -> bool:
    if val is None:
        return True
    if isinstance(val, str) and not val.strip():
        return True
    return False


def _linha_totalmente_vazia(data_v: Any, desc_v: Any, valor_v: Any) -> bool:
    return (
        _celula_vazia(data_v)
        and _celula_vazia(desc_v)
        and (valor_v is None or (isinstance(valor_v, str) and not valor_v.strip()))
    )


def parse_planilha_padrao_bytes(data: bytes) -> list[LinhaOfx]:
    """
    Lê bytes de um .xlsx e devolve linhas no mesmo formato do OFX (ofx_fitid sempre None).
    """
    if not data or not data.strip():
        raise ValueError("Arquivo vazio.")

    try:
        wb = load_workbook(io.BytesIO(data), read_only=True, data_only=True)
    except Exception as exc:
        raise ValueError("Planilha inválida ou corrompida.") from exc

    try:
        ws = wb.worksheets[0]
        linhas: list[LinhaOfx] = []

        rows_iter = ws.iter_rows(min_row=1, max_col=3, values_only=True)
        primeira = next(rows_iter, None)
        if primeira is None or not _linha_cabecalho_valida(
            (primeira[0], primeira[1], primeira[2])
        ):
            raise ValueError(
                "Cabeçalho inválido. A primeira linha deve ser exatamente: "
                "data | descricao | valor (aba ativa)."
            )

        for idx, row in enumerate(rows_iter, start=2):
            data_v, desc_v, valor_v = row[0], row[1], row[2]
            if _linha_totalmente_vazia(data_v, desc_v, valor_v):
                continue

            data_tx = _celula_para_data(data_v, idx)
            descricao = _celula_para_descricao(desc_v, idx)
            valor, tipo = valor_e_tipo_de_importacao(
                valor_v,
                mensagem_valor_invalido=f"Linha {idx}: valor inválido.",
            )

            linhas.append(
                LinhaOfx(
                    data=data_tx,
                    valor=valor,
                    tipo=tipo,
                    descricao=descricao,
                    ofx_fitid=None,
                )
            )

        return linhas
    finally:
        wb.close()


def gerar_workbook_modelo() -> Workbook:
    """Workbook em memória com cabeçalhos oficiais e uma linha de exemplo (opcional)."""
    wb = Workbook()
    ws = wb.active
    assert ws is not None
    ws.title = "Lancamentos"
    ws.append(list(PLANILHA_CABECALHOS))
    ws.append([date.today().replace(day=1), "Exemplo de despesa", -10.50])
    ws.append([date.today().replace(day=1), "Exemplo de receita", 100.00])
    return wb
