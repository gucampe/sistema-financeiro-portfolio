from __future__ import annotations

from pathlib import Path

LONGITUDINAL_DIR = (
    Path(__file__).resolve().parents[3] / "docs" / "categorizacao" / "longitudinal"
)

CHECKPOINTS = ("T0", "T1", "T2", "T3", "T4", "T5")

# Semana simulada → checkpoint de benchmark pesado
WEEK_TO_CHECKPOINT: dict[int, str] = {
    0: "T0",
    1: "T1",
    2: "T2",
    4: "T3",
    8: "T4",
    12: "T5",
}

ML_MILESTONES = (30, 50, 100, 200, 500)

PERSONA_PREFIX = "avaliacao-lx"

LEDGER_HEADER = [
    "tx_id",
    "persona",
    "semana_simulada",
    "data",
    "descricao",
    "tipo",
    "valor",
    "categoria_gold",
    "bucket",
    "merchant_mutacao",
    "eh_reimport",
    "notas",
]

PROVA_HEADER = [
    "id",
    "descricao",
    "tipo",
    "valor",
    "categoria_esperada",
    "categorias_aceitaveis",
    "bucket",
    "grupo",
    "notas",
]
