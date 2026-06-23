from __future__ import annotations

import csv
import time
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from typing import Callable

from django.contrib.auth import get_user_model

from categorizacao.evaluation.datasets import (
    AVALIACAO_DIR,
    GoldenCase,
    categorias_aceitaveis_set,
    load_golden_csv,
    write_golden_csv,
)
from categorizacao.services.pipeline import CAMADAS, classificar, sugerir, _construir_contexto
from categorizacao.types import PredicaoCategorizacao

User = get_user_model()


@dataclass
class CaseResult:
    case: GoldenCase
    sugestao_nome: str | None
    sugestao_id: int | None
    confianca: float | None
    fonte: str | None
    resultado: str
    merchant_key: str | None = None


@dataclass
class BenchmarkSummary:
    total: int = 0
    tp: int = 0
    fp: int = 0
    fn: int = 0
    sem_sugestao: int = 0
    sem_sugestao_ok: int = 0
    por_bucket: dict[str, dict[str, int]] = field(default_factory=dict)
    por_fonte: dict[str, dict[str, int]] = field(default_factory=dict)
    resultados: list[CaseResult] = field(default_factory=list)
    latencia_ms_media: float = 0.0

    @property
    def cobertura(self) -> float:
        return (self.tp + self.fp) / self.total if self.total else 0.0

    @property
    def acuracia_top1(self) -> float:
        denom = self.tp + self.fp
        return self.tp / denom if denom else 0.0

    @property
    def recall(self) -> float:
        denom = self.tp + self.fn
        return self.tp / denom if denom else 0.0


def _classificar_resultado(case: GoldenCase, sugestao_nome: str | None) -> str:
    aceitaveis = categorias_aceitaveis_set(case)
    if sugestao_nome:
        if aceitaveis and sugestao_nome in aceitaveis:
            return "TP"
        if case.categoria_esperada and sugestao_nome == case.categoria_esperada:
            return "TP"
        if not case.categoria_esperada and not aceitaveis:
            return "FP"
        return "FP"
    if case.categoria_esperada or aceitaveis:
        return "FN"
    return "SEM_SUGESTAO_OK"


def run_benchmark(usuario, cases: list[GoldenCase] | None = None) -> BenchmarkSummary:
    cases = cases or load_golden_csv()
    summary = BenchmarkSummary()
    latencias: list[float] = []

    for case in cases:
        t0 = time.perf_counter()
        sug = sugerir(usuario, case.descricao, case.tipo, Decimal(case.valor.replace(",", ".")))
        latencias.append((time.perf_counter() - t0) * 1000)

        sug_nome = sug.categoria_nome if sug else None
        resultado = _classificar_resultado(case, sug_nome)
        cr = CaseResult(
            case=case,
            sugestao_nome=sug_nome,
            sugestao_id=sug.categoria_id if sug else None,
            confianca=sug.confianca if sug else None,
            fonte=sug.fonte if sug else None,
            resultado=resultado,
            merchant_key=sug.merchant_key if sug else None,
        )
        summary.resultados.append(cr)
        summary.total += 1
        if resultado == "TP":
            summary.tp += 1
        elif resultado == "FP":
            summary.fp += 1
        elif resultado == "FN":
            summary.fn += 1
        elif resultado == "SEM_SUGESTAO_OK":
            summary.sem_sugestao_ok += 1
        else:
            summary.sem_sugestao += 1

        bucket = case.bucket
        summary.por_bucket.setdefault(bucket, Counter())
        summary.por_bucket[bucket][resultado] += 1

        if sug and sug.fonte:
            summary.por_fonte.setdefault(sug.fonte, Counter())
            summary.por_fonte[sug.fonte][resultado] += 1

    summary.latencia_ms_media = sum(latencias) / len(latencias) if latencias else 0.0
    return summary


def run_ablation(usuario, cases: list[GoldenCase], max_cases: int = 60) -> dict[str, BenchmarkSummary]:
    subset = cases[:max_cases]
    configs: dict[str, Callable] = {
        "pipeline_completo": lambda ctx: classificar(ctx),
        "sem_historico": _classificar_sem_camadas({"historico"}),
        "sem_fuzzy": _classificar_sem_camadas({"fuzzy"}),
        "sem_ml": _classificar_sem_camadas({"ml"}),
        "so_regras": _classificar_so_camadas({"regra_usuario", "regra_global"}),
    }
    out: dict[str, BenchmarkSummary] = {}
    for nome, fn in configs.items():
        summary = BenchmarkSummary()
        for case in subset:
            ctx = _construir_contexto(
                usuario, case.descricao, case.tipo, Decimal(case.valor.replace(",", "."))
            )
            pred: PredicaoCategorizacao | None = fn(ctx)
            sug_nome = pred.categoria_nome if pred else None
            resultado = _classificar_resultado(case, sug_nome)
            summary.resultados.append(
                CaseResult(
                    case=case,
                    sugestao_nome=sug_nome,
                    sugestao_id=pred.categoria_id if pred else None,
                    confianca=pred.confianca if pred else None,
                    fonte=pred.fonte if pred else None,
                    resultado=resultado,
                )
            )
            summary.total += 1
            if resultado == "TP":
                summary.tp += 1
            elif resultado == "FP":
                summary.fp += 1
            elif resultado == "FN":
                summary.fn += 1
            elif resultado == "SEM_SUGESTAO_OK":
                summary.sem_sugestao_ok += 1
        out[nome] = summary
    return out


def _classificar_sem_camadas(excluir: set[str]):
    camadas = [(n, f) for n, f in CAMADAS if n not in excluir]

    def _fn(ctx):
        melhor = None
        for nome, fn in camadas:
            pred = fn(ctx)
            if pred is None:
                continue
            from categorizacao.services.pipeline import LIMIARES_PARADA
            limiar = LIMIARES_PARADA.get(nome, 0.70)
            if pred.confianca >= limiar:
                return pred
            if melhor is None or pred.confianca > melhor.confianca:
                melhor = pred
        return melhor

    return _fn


def _classificar_so_camadas(incluir: set[str]):
    camadas = [(n, f) for n, f in CAMADAS if n in incluir]

    def _fn(ctx):
        for _, fn in camadas:
            pred = fn(ctx)
            if pred is not None:
                return pred
        return None

    return _fn


def write_resultados_csv(summary: BenchmarkSummary, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "id",
                "bucket",
                "descricao",
                "categoria_esperada",
                "sugestao",
                "confianca",
                "fonte",
                "resultado",
            ]
        )
        for r in summary.resultados:
            writer.writerow(
                [
                    r.case.id,
                    r.case.bucket,
                    r.case.descricao,
                    r.case.categoria_esperada,
                    r.sugestao_nome or "",
                    r.confianca or "",
                    r.fonte or "",
                    r.resultado,
                ]
            )


def write_metricas_consolidadas(
    summaries: dict[str, BenchmarkSummary],
    path: Path,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "contexto",
                "total",
                "tp",
                "fp",
                "fn",
                "sem_sugestao_ok",
                "cobertura",
                "acuracia_top1",
                "recall",
                "latencia_ms_media",
            ]
        )
        for ctx, s in summaries.items():
            writer.writerow(
                [
                    ctx,
                    s.total,
                    s.tp,
                    s.fp,
                    s.fn,
                    s.sem_sugestao_ok,
                    f"{s.cobertura:.4f}",
                    f"{s.acuracia_top1:.4f}",
                    f"{s.recall:.4f}",
                    f"{s.latencia_ms_media:.2f}",
                ]
            )
