from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client

from categorizacao.evaluation.datasets import AVALIACAO_DIR
from transacoes.tests.helpers.import_fixtures import build_ofx_bytes


@dataclass
class PreviewLineMetric:
    indice: int
    descricao: str
    tem_sugestao: bool
    categoria_sugerida_id: int | None
    categoria_sugerida_nome: str | None
    confianca: float | None
    fonte: str | None
    pre_preencher: bool


@dataclass
class IntegrationResult:
    superficie: str
    persona: str
    total_linhas: int = 0
    com_sugestao: int = 0
    pre_preenchidas: int = 0
    latencia_ms: float = 0.0
    linhas: list[PreviewLineMetric] = field(default_factory=list)
    erro: str | None = None

    @property
    def cobertura(self) -> float:
        return self.com_sugestao / self.total_linhas if self.total_linhas else 0.0

    @property
    def taxa_pre_preenchimento(self) -> float:
        return self.pre_preenchidas / self.com_sugestao if self.com_sugestao else 0.0


def _login_client(user) -> Client:
    client = Client(enforce_csrf_checks=False)
    client.force_login(user)
    return client


def _parse_preview_lines(payload: dict) -> list[PreviewLineMetric]:
    linhas = []
    for row in payload.get("linhas", []):
        linhas.append(
            PreviewLineMetric(
                indice=row.get("indice", 0),
                descricao=row.get("descricao", ""),
                tem_sugestao=bool(row.get("categoria_sugerida_id")),
                categoria_sugerida_id=row.get("categoria_sugerida_id"),
                categoria_sugerida_nome=row.get("categoria_sugerida_nome"),
                confianca=row.get("categoria_sugerida_confianca"),
                fonte=row.get("categoria_sugerida_fonte"),
                pre_preencher=bool(row.get("categoria_sugerida_pre_preencher")),
            )
        )
    return linhas


def run_ofx_preview(user, conta_id: int, ofx_path: Path, persona: str) -> IntegrationResult:
    client = _login_client(user)
    raw = ofx_path.read_bytes()
    upload = SimpleUploadedFile(ofx_path.name, raw, content_type="application/octet-stream")
    t0 = time.perf_counter()
    resp = client.post(
        "/transacoes/importar/ofx/preview/",
        {"conta_id": str(conta_id), "arquivo": upload},
    )
    latencia = (time.perf_counter() - t0) * 1000
    result = IntegrationResult(superficie="OFX", persona=persona, latencia_ms=latencia)
    if resp.status_code != 200:
        result.erro = f"HTTP {resp.status_code}: {resp.content[:200]}"
        return result
    payload = json.loads(resp.content)
    result.linhas = _parse_preview_lines(payload)
    result.total_linhas = len(result.linhas)
    result.com_sugestao = sum(1 for l in result.linhas if l.tem_sugestao)
    result.pre_preenchidas = sum(1 for l in result.linhas if l.pre_preencher)
    return result


def run_xlsx_preview(user, conta_id: int, xlsx_path: Path, persona: str) -> IntegrationResult:
    client = _login_client(user)
    raw = xlsx_path.read_bytes()
    upload = SimpleUploadedFile(
        xlsx_path.name,
        raw,
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    t0 = time.perf_counter()
    resp = client.post(
        "/transacoes/importar/planilha/preview/",
        {"conta_id": str(conta_id), "arquivo": upload},
    )
    latencia = (time.perf_counter() - t0) * 1000
    result = IntegrationResult(superficie="XLSX", persona=persona, latencia_ms=latencia)
    if resp.status_code != 200:
        result.erro = f"HTTP {resp.status_code}"
        return result
    payload = json.loads(resp.content)
    result.linhas = _parse_preview_lines(payload)
    result.total_linhas = len(result.linhas)
    result.com_sugestao = sum(1 for l in result.linhas if l.tem_sugestao)
    result.pre_preenchidas = sum(1 for l in result.linhas if l.pre_preencher)
    return result


def run_sugerir_api(user, descricao: str, tipo: str = "despesa") -> dict:
    client = _login_client(user)
    resp = client.get(
        "/categorizacao/sugerir/",
        {"descricao": descricao, "tipo": tipo},
        HTTP_X_REQUESTED_WITH="XMLHttpRequest",
    )
    return json.loads(resp.content)


def generate_ofx_fixtures(out_dir: Path) -> dict[str, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    merchants_30 = [
        {"fitid": f"m30-{i:03d}", "trnamt": f"-{20 + i}.00", "name": name}
        for i, name in enumerate(
            [
                "IFOOD RESTAURANTE",
                "UBER TRIP",
                "NETFLIX COM",
                "DROGASIL",
                "CARREFOUR",
                "SPOTIFY",
                "SHELL POSTO",
                "MCDONALDS",
                "AMAZON BR",
                "SHOPEE",
                "RAPPI",
                "99 POP",
                "ENEL SP",
                "CLARO MOVEL",
                "PETZ",
                "RENNER",
                "LATAM",
                "ALURA",
                "CINEMARK",
                "PAO DE ACUCAR",
                "ATACADAO",
                "MAGAZINE LUIZA",
                "COBASI",
                "OUTBACK",
                "SMART FIT",
                "BOOKING COM",
                "GITHUB",
                "FIGMA",
                "STEAM",
                "PADARIA CENTRAL",
            ]
        )
    ]
    ruidoso_50 = merchants_30 + [
        {"fitid": f"r50-{i:03d}", "trnamt": "-15.00", "name": f"DEBITO COMPRA CARTAO LOJA {i} SAO PAULO BR"}
        for i in range(20)
    ]
    ambiguos_20 = [
        {"fitid": f"a20-{i:03d}", "trnamt": "-40.00", "name": name}
        for i, name in enumerate(
            [
                "PIX ENVIADO JOAO",
                "PIX MARIA SILVA",
                "AMAZON BR",
                "MERCADO MUNICIPAL",
                "UBER EATS",
                "IFOOD MERCADO",
                "POSTO IPIRANGA CONVENIENCIA",
                "LOJAS AMERICANAS 03/10",
                "PARCELA 5/12 MAGALU",
                "PADARIA DO BAIRRO",
                "PIX RECEBIDO SALARIO",
                "TRANSFERENCIA ENTRE CONTAS",
                "PAGAMENTO FATURA CARTAO",
                "RESTAURANTE SUSHI",
                "FARMACIA POPULAR",
                "DOACAO ONG",
                "MATERIAL ESCRITORIO",
                "SEGURO AUTO MENSAL",
                "CONDOMINIO TAXA",
                "SERVICOS GERAIS",
            ]
        )
    ]
    paths = {}
    for name, txs in [
        ("ofx_30_merchants.ofx", merchants_30),
        ("ofx_50_ruidoso.ofx", ruidoso_50),
        ("ofx_20_ambiguos.ofx", ambiguos_20),
    ]:
        p = out_dir / name
        p.write_bytes(build_ofx_bytes(txs))
        paths[name] = p

    # 200 linhas para carga
    txs200 = [
        {"fitid": f"ld-{i:04d}", "trnamt": f"-{10 + (i % 50)}.00", "name": merchants_30[i % 30]["name"]}
        for i in range(200)
    ]
    p200 = out_dir / "ofx_200_linhas.ofx"
    p200.write_bytes(build_ofx_bytes(txs200))
    paths["ofx_200_linhas.ofx"] = p200
    return paths


def generate_xlsx_fixtures(out_dir: Path) -> dict[str, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    from datetime import date
    from openpyxl import Workbook
    from transacoes.xlsx_parse import PLANILHA_CABECALHOS

    descricoes = [
        "IFOOD RESTAURANTE",
        "UBER TRIP",
        "NETFLIX COM",
        "DROGASIL",
        "CARREFOUR",
    ] * 6

    wb = Workbook()
    ws = wb.active
    ws.append(list(PLANILHA_CABECALHOS))
    for i, desc in enumerate(descricoes[:30]):
        ws.append([date(2025, 6, 1 + (i % 28)), desc, -25.0 - i])
    p30 = out_dir / "xlsx_30_merchants.xlsx"
    wb.save(p30)

    wb2 = Workbook()
    ws2 = wb2.active
    ws2.append(list(PLANILHA_CABECALHOS))
    for i, desc in enumerate(descricoes[:20]):
        ws2.append([date(2025, 7, 1 + (i % 28)), desc, -30.0])
    p20 = out_dir / "xlsx_20_merchants.xlsx"
    wb2.save(p20)
    return {"xlsx_30_merchants.xlsx": p30, "xlsx_20_merchants.xlsx": p20}
