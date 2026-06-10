"""Factories determinísticas para testes de importação OFX/XLSX."""

from __future__ import annotations

import io
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from openpyxl import Workbook

from transacoes.xlsx_parse import PLANILHA_CABECALHOS

_OFX_HEADER = """OFXHEADER:100
DATA:OFXSGML
VERSION:102
SECURITY:NONE
ENCODING:USASCII
CHARSET:1252
COMPRESSION:NONE
OLDFILEUID:NONE
NEWFILEUID:NONE

<OFX>
<BANKMSGSRSV1>
<STMTTRNRS>
<STMTRS>
<CURDEF>BRL
<BANKACCTFROM>
<BANKID>001
<ACCTID>12345-6
<ACCTTYPE>CHECKING
</BANKACCTFROM>
<BANKTRANLIST>
<DTSTART>20240101000000
<DTEND>20241231235959
"""

_OFX_FOOTER = """</BANKTRANLIST>
</STMTRS>
</STMTTRNRS>
</BANKMSGSRSV1>
</OFX>
"""


def _stmttrn(
    *,
    fitid: str,
    trnamt: str,
    dtposted: str = "20240115120000",
    name: str = "LANCAMENTO",
    memo: str = "",
    trntype: str = "DEBIT",
) -> str:
    memo_tag = f"<MEMO>{memo}\n" if memo else ""
    return f"""<STMTTRN>
<TRNTYPE>{trntype}
<DTPOSTED>{dtposted}
<TRNAMT>{trnamt}
<FITID>{fitid}
<NAME>{name}
{memo_tag}</STMTTRN>
"""


def build_ofx_bytes(
    transactions: list[dict[str, Any]] | None = None,
    *,
    encoding: str = "utf-8",
) -> bytes:
    """OFX mínimo com STMTTRN controlados."""
    if not transactions:
        transactions = [
            {
                "fitid": "default-1",
                "trnamt": "-10.00",
                "name": "Teste",
            }
        ]
    body = _OFX_HEADER
    for tx in transactions:
        body += _stmttrn(
            fitid=tx.get("fitid", "x"),
            trnamt=tx.get("trnamt", "-1.00"),
            dtposted=tx.get("dtposted", "20240115120000"),
            name=tx.get("name", "LANC"),
            memo=tx.get("memo", ""),
            trntype=tx.get("trntype", "DEBIT"),
        )
    body += _OFX_FOOTER
    return body.encode(encoding)


def build_ofx_corrupto(tipo: str) -> bytes:
    """vazio | lixo | truncado | sem_stmttrn"""
    if tipo == "vazio":
        return b"   \n\t  "
    if tipo == "lixo":
        return b"not ofx content at all"
    if tipo == "truncado":
        return build_ofx_bytes([{"fitid": "t1", "trnamt": "-1.00"}])[:120]
    if tipo == "sem_stmttrn":
        return (
            _OFX_HEADER.replace("<BANKTRANLIST>", "<BANKTRANLIST>\n") + _OFX_FOOTER
        ).encode("utf-8")
    raise ValueError(f"tipo corrupto desconhecido: {tipo}")


def build_ofx_dup(cenario: str, *, fitid_base: str = "dup-seed-fitid") -> bytes:
    """fitid_igual | fitid_diff_chave | heuristica_cruzada"""
    if cenario == "fitid_igual":
        return build_ofx_bytes(
            [
                {
                    "fitid": fitid_base,
                    "trnamt": "-42.50",
                    "name": "PADARIA CENTRAL",
                    "dtposted": "20240115120000",
                }
            ]
        )
    if cenario == "fitid_diff_chave":
        return build_ofx_bytes(
            [
                {
                    "fitid": fitid_base,
                    "trnamt": "-99.00",
                    "name": "OUTRO LANC",
                    "dtposted": "20240201120000",
                }
            ]
        )
    if cenario == "heuristica_cruzada":
        return build_ofx_bytes(
            [
                {
                    "fitid": "heur-only-file",
                    "trnamt": "-20.00",
                    "name": "mercado sao jose",
                    "dtposted": "20240401120000",
                }
            ]
        )
    raise ValueError(f"cenario dup desconhecido: {cenario}")


def build_ofx_concorrente(n: int, *, prefix: str = "conc-fit") -> bytes:
    """N transações com FITIDs únicos determinísticos."""
    txs = []
    base = date(2024, 6, 1)
    for i in range(n):
        d = base + timedelta(days=i)
        txs.append(
            {
                "fitid": f"{prefix}-{i:04d}",
                "trnamt": f"-{10 + i}.00",
                "name": f"Conc {i}",
                "dtposted": f"{d.strftime('%Y%m%d')}120000",
            }
        )
    return build_ofx_bytes(txs)


def build_xlsx_bytes(
    n_linhas: int = 1,
    *,
    data_inicio: date | None = None,
    descricao: str = "Import linha",
    valor: float = -10.0,
    valor_por_linha: bool = True,
) -> bytes:
    """Planilha padronizada com n linhas de dados."""
    d0 = data_inicio or date(2024, 3, 1)
    wb = Workbook()
    ws = wb.active
    ws.append(list(PLANILHA_CABECALHOS))
    for i in range(n_linhas):
        d = d0 + timedelta(days=i % 28)
        v = valor - i if valor_por_linha else valor
        ws.append([d, f"{descricao} {i}", v])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def build_xlsx_invalid(tipo: str) -> bytes:
    """cabecalho_errado | vazio | linha_data_invalida"""
    if tipo == "vazio":
        wb = Workbook()
        ws = wb.active
        buf = io.BytesIO()
        wb.save(buf)
        return buf.getvalue()
    if tipo == "cabecalho_errado":
        wb = Workbook()
        ws = wb.active
        ws.append(["col_a", "col_b", "col_c"])
        ws.append([date.today(), "x", -1])
        buf = io.BytesIO()
        wb.save(buf)
        return buf.getvalue()
    if tipo == "linha_data_invalida":
        wb = Workbook()
        ws = wb.active
        ws.append(list(PLANILHA_CABECALHOS))
        ws.append(["nao-e-data", "desc", -5])
        buf = io.BytesIO()
        wb.save(buf)
        return buf.getvalue()
    raise ValueError(f"tipo xlsx invalido desconhecido: {tipo}")


def build_ofx_real_world_messy() -> bytes:
    """
    OFX “quase real”: datas fora de ordem, espaços, MEMO inconsistentes, encoding misto.
    """
    txs = [
        {
            "fitid": "rw-003",
            "trnamt": "-33.00",
            "name": "  PADARIA   CENTRAL  ",
            "memo": "compra",
            "dtposted": "20240915120000",
        },
        {
            "fitid": "rw-001",
            "trnamt": "-11.00",
            "name": "Mercado",
            "memo": "  MEMO   EXTRA  ",
            "dtposted": "20240101120000",
        },
        {
            "fitid": "rw-002",
            "trnamt": "50.00",
            "name": "Salário",
            "memo": "",
            "dtposted": "20240630120000",
        },
    ]
    body = _OFX_HEADER
    for tx in txs:
        body += _stmttrn(
            fitid=tx["fitid"],
            trnamt=tx["trnamt"],
            dtposted=tx["dtposted"],
            name=tx["name"],
            memo=tx["memo"],
            trntype="DEBIT" if tx["trnamt"].startswith("-") else "CREDIT",
        )
    body += _OFX_FOOTER
    return body.encode("utf-8")


def build_ofx_real_world_latin1() -> bytes:
    """Nome com bytes Latin-1 em arquivo UTF-8 (parser deve normalizar ou rejeitar controlado)."""
    txs = [
        {
            "fitid": "rw-lat-1",
            "trnamt": "-7.50",
            "name": "Café São João",
            "dtposted": "20240510120000",
        }
    ]
    return build_ofx_bytes(txs, encoding="latin-1")


def build_xlsx_real_world_messy() -> bytes:
    """Colunas extras, linhas vazias intercaladas, espaços e valores mistos."""
    wb = Workbook()
    ws = wb.active
    ws.append(list(PLANILHA_CABECALHOS) + ["ignorar", "outra"])
    ws.append([None, None, None, "vazio"])
    ws.append([date(2024, 7, 1), "  Real World  ", -15.0, "x"])
    ws.append([date(2024, 7, 2), "Linha parcial", -8.5])
    ws.append([None, None, None])
    ws.append([date(2024, 7, 3), "Receita RW", 120.0, "extra"])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def build_xlsx_real_world_missing_header_col() -> bytes:
    """Cabeçalho válido; uma linha sem valor (deve falhar no parse)."""
    wb = Workbook()
    ws = wb.active
    ws.append(list(PLANILHA_CABECALHOS))
    ws.append([date(2024, 7, 10), "Sem valor", None])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def build_xlsx_oversized_bytes(min_bytes: int = 6 * 1024 * 1024 + 1) -> bytes:
    """Arquivo .xlsx válido mínimo + padding para exceder limite de upload."""
    base = build_xlsx_bytes(1)
    if len(base) >= min_bytes:
        return base
    return base + b"\x00" * (min_bytes - len(base))
