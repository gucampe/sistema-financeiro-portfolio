from __future__ import annotations

import time
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from decimal import Decimal

from categorizacao.evaluation.datasets import GoldenCase, categorias_aceitaveis_set
from categorizacao.evaluation.runner import _classificar_resultado
from categorizacao.services.llm.orchestrator import classificar_com_llm
from categorizacao.services.pipeline import _construir_contexto, classificar, sugerir


@dataclass
class LLMCompareResult:
    case: GoldenCase
    hibrido_nome: str | None
    hibrido_fonte: str | None
    llm_nome: str | None
    llm_fonte: str | None
    hibrido_resultado: str
    llm_resultado: str
    ganho_llm: bool = False
    regressao_llm: bool = False


@dataclass
class LLMBenchmarkSummary:
    variant: str
    total: int = 0
    tp: int = 0
    fp: int = 0
    fn: int = 0
    sem_sugestao: int = 0
    por_bucket: dict[str, Counter] = field(default_factory=dict)
    por_fonte: dict[str, Counter] = field(default_factory=dict)
    latencia_ms_media: float = 0.0
    llm_invocations: int = 0
    comparacoes: list[LLMCompareResult] = field(default_factory=list)

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


def _sugestao_nome_from_pred(pred) -> str | None:
    return pred.categoria_nome if pred else None


def run_hybrid_benchmark(usuario, cases: list[GoldenCase], variant: str = "hibrido") -> LLMBenchmarkSummary:
    summary = LLMBenchmarkSummary(variant=variant, total=len(cases))
    latencias: list[float] = []
    for case in cases:
        t0 = time.perf_counter()
        ctx = _construir_contexto(usuario, case.descricao, case.tipo, Decimal(case.valor.replace(",", ".")))
        pred = classificar(ctx)
        latencias.append((time.perf_counter() - t0) * 1000)
        nome = _sugestao_nome_from_pred(pred)
        resultado = _classificar_resultado(case, nome)
        _accumulate(summary, case, resultado, pred.fonte if pred else None)
    summary.latencia_ms_media = sum(latencias) / len(latencias) if latencias else 0.0
    return summary


def run_llm_benchmark(usuario, cases: list[GoldenCase], variant: str = "llm_mock") -> LLMBenchmarkSummary:
    summary = LLMBenchmarkSummary(variant=variant, total=len(cases))
    latencias: list[float] = []
    for case in cases:
        t0 = time.perf_counter()
        ctx = _construir_contexto(usuario, case.descricao, case.tipo, Decimal(case.valor.replace(",", ".")))
        pred = classificar_com_llm(ctx)
        latencias.append((time.perf_counter() - t0) * 1000)
        nome = _sugestao_nome_from_pred(pred)
        resultado = _classificar_resultado(case, nome)
        if pred and pred.fonte == "llm_gemini":
            summary.llm_invocations += 1
        _accumulate(summary, case, resultado, pred.fonte if pred else None)
    summary.latencia_ms_media = sum(latencias) / len(latencias) if latencias else 0.0
    return summary


def run_sugerir_benchmark(usuario, cases: list[GoldenCase], variant: str = "sugerir_llm") -> LLMBenchmarkSummary:
    summary = LLMBenchmarkSummary(variant=variant, total=len(cases))
    latencias: list[float] = []
    for case in cases:
        t0 = time.perf_counter()
        sug = sugerir(usuario, case.descricao, case.tipo, Decimal(case.valor.replace(",", ".")))
        latencias.append((time.perf_counter() - t0) * 1000)
        nome = sug.categoria_nome if sug else None
        resultado = _classificar_resultado(case, nome)
        if sug and sug.fonte == "llm_gemini":
            summary.llm_invocations += 1
        _accumulate(summary, case, resultado, sug.fonte if sug else None)
    summary.latencia_ms_media = sum(latencias) / len(latencias) if latencias else 0.0
    return summary


def compare_hybrid_vs_llm(usuario, cases: list[GoldenCase]) -> list[LLMCompareResult]:
    out: list[LLMCompareResult] = []
    for case in cases:
        valor = Decimal(case.valor.replace(",", "."))
        ctx = _construir_contexto(usuario, case.descricao, case.tipo, valor)
        pred_h = classificar(ctx)
        pred_l = classificar_com_llm(ctx)
        h_nome = _sugestao_nome_from_pred(pred_h)
        l_nome = _sugestao_nome_from_pred(pred_l)
        h_res = _classificar_resultado(case, h_nome)
        l_res = _classificar_resultado(case, l_nome)
        ganho = h_res in ("FN", "SEM_SUGESTAO_OK") and l_res == "TP"
        regressao = h_res == "TP" and l_res == "FP"
        out.append(
            LLMCompareResult(
                case=case,
                hibrido_nome=h_nome,
                hibrido_fonte=pred_h.fonte if pred_h else None,
                llm_nome=l_nome,
                llm_fonte=pred_l.fonte if pred_l else None,
                hibrido_resultado=h_res,
                llm_resultado=l_res,
                ganho_llm=ganho,
                regressao_llm=regressao,
            )
        )
    return out


def _accumulate(summary: LLMBenchmarkSummary, case: GoldenCase, resultado: str, fonte: str | None) -> None:
    if resultado == "TP":
        summary.tp += 1
    elif resultado == "FP":
        summary.fp += 1
    elif resultado == "FN":
        summary.fn += 1
    elif resultado == "SEM_SUGESTAO_OK":
        summary.sem_sugestao += 1
    else:
        summary.sem_sugestao += 1
    summary.por_bucket.setdefault(case.bucket, Counter())[resultado] += 1
    if fonte:
        summary.por_fonte.setdefault(fonte, Counter())[resultado] += 1


def bucket_metrics(summary: LLMBenchmarkSummary, bucket: str) -> dict[str, float]:
    ctr = summary.por_bucket.get(bucket, Counter())
    total = sum(ctr.values())
    tp = ctr.get("TP", 0)
    fp = ctr.get("FP", 0)
    fn = ctr.get("FN", 0)
    cobertura = (tp + fp) / total if total else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    return {"total": total, "cobertura": cobertura, "recall": recall, "tp": tp, "fp": fp, "fn": fn}
