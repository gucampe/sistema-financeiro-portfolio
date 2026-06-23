from __future__ import annotations

import csv
from pathlib import Path

from categorizacao.evaluation.datasets import (
    AVALIACAO_DIR,
    GoldenCase,
    _row,
    load_golden_csv,
)

LLM_DIR = AVALIACAO_DIR / "llm"
DATASETS_DIR = LLM_DIR / "datasets"

LLM_DATASET_BUCKETS = {
    "golden_llm_m3_v1": ("M3", 30),
    "golden_llm_r2_v1": ("R2", 20),
    "golden_llm_c1_v1": ("C1", 20),
    "golden_llm_r1_v1": ("R1", 15),
    "golden_llm_ineditos_v1": ("INEDITOS", 50),
}


def _ineditos_cases() -> list[GoldenCase]:
    raw = [
        ("IN-001", "FEIRA ORGANICA BAIRRO NOVO", "Supermercado|Alimentação"),
        ("IN-002", "PIX ENVIADO CONDOMINIO RESIDENCIAL", "Moradia"),
        ("IN-003", "LOJA ROUPAS OUTLET CENTER", "Roupas|Compras"),
        ("IN-004", "SERVICO LIMPEZA RESIDENCIAL", "Moradia|Diversos"),
        ("IN-005", "TRANSFERENCIA PIX AMIGA", "Presentes e doações|Família"),
        ("IN-006", "RESTAURANTE VEGETARIANO VILA", "Alimentação|Restaurantes e bares"),
        ("IN-007", "CLINICA FISIOTERAPIA", "Saúde"),
        ("IN-008", "ASSINATURA CANVA PRO", "Serviços e Assinaturas"),
        ("IN-009", "MERCADINHO DA ESQUINA 24H", "Supermercado"),
        ("IN-010", "PIX RECEBIDO ALUGUEL QUARTO", "Moradia|Receitas diversas"),
    ]
    cases = [
        _row(cid, desc, cat, "INEDITOS", notas="caso inédito sintético")
        for cid, desc, cat in raw
    ]
    # Completa até 50 reutilizando variações dos buckets existentes com sufixo
    base = load_golden_csv()
    idx = len(cases) + 1
    for case in base:
        if case.bucket not in ("M3", "R2"):
            continue
        if len(cases) >= 50:
            break
        cases.append(
            _row(
                f"IN-{idx:03d}",
                f"{case.descricao} FILIAL NOVA",
                case.categorias_aceitaveis or case.categoria_esperada,
                "INEDITOS",
                tipo=case.tipo,
                valor=case.valor,
                notas="derivado inédito",
            )
        )
        idx += 1
    return cases[:50]


def filter_golden_by_bucket(cases: list[GoldenCase], bucket: str, limit: int | None = None) -> list[GoldenCase]:
    if bucket == "INEDITOS":
        filtered = [c for c in cases if c.bucket == "INEDITOS"]
        if not filtered:
            filtered = _ineditos_cases()
    else:
        filtered = [c for c in cases if c.bucket == bucket]
    if limit is not None:
        return filtered[:limit]
    return filtered


def write_llm_datasets(cases: list[GoldenCase] | None = None) -> dict[str, Path]:
    cases = cases or load_golden_csv()
    ineditos = _ineditos_cases()
    cases = cases + [c for c in ineditos if c.id not in {x.id for x in cases}]
    DATASETS_DIR.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}
    for name, (bucket, limit) in LLM_DATASET_BUCKETS.items():
        subset = filter_golden_by_bucket(cases, bucket, limit)
        path = DATASETS_DIR / f"{name}.csv"
        with path.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(
                fh,
                fieldnames=[
                    "id",
                    "descricao",
                    "tipo",
                    "valor",
                    "categoria_esperada",
                    "categorias_aceitaveis",
                    "bucket",
                    "banco_origem",
                    "notas_avaliador",
                ],
            )
            writer.writeheader()
            for c in subset:
                writer.writerow(
                    {
                        "id": c.id,
                        "descricao": c.descricao,
                        "tipo": c.tipo,
                        "valor": c.valor,
                        "categoria_esperada": c.categoria_esperada,
                        "categorias_aceitaveis": c.categorias_aceitaveis,
                        "bucket": c.bucket,
                        "banco_origem": c.banco_origem,
                        "notas_avaliador": c.notas_avaliador,
                    }
                )
        paths[name] = path
    return paths


def load_llm_focus_cases() -> list[GoldenCase]:
    """M3 + R2 + C1 + R1 + inéditos para benchmark LLM."""
    cases = load_golden_csv()
    ineditos = _ineditos_cases()
    merged = cases + [c for c in ineditos if c.id not in {x.id for x in cases}]
    out: list[GoldenCase] = []
    for _, (bucket, limit) in LLM_DATASET_BUCKETS.items():
        out.extend(filter_golden_by_bucket(merged, bucket, limit))
    return out
