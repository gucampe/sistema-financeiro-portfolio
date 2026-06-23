from __future__ import annotations

import csv
import subprocess
from datetime import date
from pathlib import Path

from categorizacao.evaluation.llm.cost_sim import estimate_cost, project_monthly
from categorizacao.evaluation.llm.datasets_llm import LLM_DIR
from categorizacao.evaluation.llm.runner_llm import LLMBenchmarkSummary, LLMCompareResult, bucket_metrics


def git_commit_curto() -> str:
    try:
        return (
            subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], stderr=subprocess.DEVNULL)
            .decode()
            .strip()
        )
    except Exception:
        return "unknown"


def write_comparativo_csv(comparacoes: list[LLMCompareResult], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=[
                "id",
                "bucket",
                "descricao",
                "hibrido_nome",
                "hibrido_resultado",
                "llm_nome",
                "llm_resultado",
                "llm_fonte",
                "ganho_llm",
                "regressao_llm",
            ],
        )
        writer.writeheader()
        for c in comparacoes:
            writer.writerow(
                {
                    "id": c.case.id,
                    "bucket": c.case.bucket,
                    "descricao": c.case.descricao[:80],
                    "hibrido_nome": c.hibrido_nome or "",
                    "hibrido_resultado": c.hibrido_resultado,
                    "llm_nome": c.llm_nome or "",
                    "llm_resultado": c.llm_resultado,
                    "llm_fonte": c.llm_fonte or "",
                    "ganho_llm": c.ganho_llm,
                    "regressao_llm": c.regressao_llm,
                }
            )
    return path


def gerar_relatorio_llm(
    *,
    hibrido: LLMBenchmarkSummary,
    llm: LLMBenchmarkSummary,
    comparacoes: list[LLMCompareResult],
    modelos: dict[str, LLMBenchmarkSummary] | None = None,
    commit: str,
    output_path: Path,
) -> Path:
    hoje = date.today().isoformat()
    ganhos = sum(1 for c in comparacoes if c.ganho_llm)
    regressoes = sum(1 for c in comparacoes if c.regressao_llm)
    m3_h = bucket_metrics(hibrido, "M3")
    m3_l = bucket_metrics(llm, "M3")
    r2_h = bucket_metrics(hibrido, "R2")
    r2_l = bucket_metrics(llm, "R2")

    cost_per_call = estimate_cost(llm.variant, 450, 80)
    cost_month = project_monthly(categorizacoes_dia=1000, llm_invocation_rate=0.15)

    lines = [
        "# Comparativo — Fallback LLM (Gemini) vs Pipeline Híbrido",
        "",
        f"**Data:** {hoje}  ",
        f"**Commit:** `{commit}`  ",
        f"**Variante LLM:** {llm.variant}  ",
        "",
        "## Resumo executivo",
        "",
        f"| Métrica | Híbrido | Com LLM | Δ |",
        f"|---------|---------|---------|---|",
        f"| Cobertura global | {hibrido.cobertura:.1%} | {llm.cobertura:.1%} | {(llm.cobertura - hibrido.cobertura):+.1%} |",
        f"| Acurácia top-1 | {hibrido.acuracia_top1:.1%} | {llm.acuracia_top1:.1%} | {(llm.acuracia_top1 - hibrido.acuracia_top1):+.1%} |",
        f"| Recall | {hibrido.recall:.1%} | {llm.recall:.1%} | {(llm.recall - hibrido.recall):+.1%} |",
        f"| Latência média (ms) | {hibrido.latencia_ms_media:.1f} | {llm.latencia_ms_media:.1f} | — |",
        f"| Invocações LLM | 0 | {llm.llm_invocations} | — |",
        "",
        "## Buckets críticos (M3 + R2)",
        "",
        f"| Bucket | Cobertura híbrido | Cobertura LLM | Recall híbrido | Recall LLM |",
        f"|--------|-------------------|---------------|----------------|------------|",
        f"| M3 | {m3_h['cobertura']:.1%} | {m3_l['cobertura']:.1%} | {m3_h['recall']:.1%} | {m3_l['recall']:.1%} |",
        f"| R2 | {r2_h['cobertura']:.1%} | {r2_l['cobertura']:.1%} | {r2_h['recall']:.1%} | {r2_l['recall']:.1%} |",
        "",
        "## Ganhos e regressões",
        "",
        f"- **Ganhos LLM** (FN→TP): {ganhos}",
        f"- **Regressões** (TP→FP): {regressoes}",
        "",
        "## Custo estimado (simulação)",
        "",
        f"- Por chamada (~450 in / 80 out tokens): **${cost_per_call.cost_usd:.6f}**",
        f"- Projeção mensal (1000 cat/dia, 15% LLM): **${cost_month.cost_usd:.2f}**",
        "",
    ]

    if modelos:
        lines.extend(
            [
                "## Comparativo por modelo",
                "",
                "| Modelo | Cobertura | Recall | Latência ms | Invocações LLM |",
                "|--------|-----------|--------|-------------|----------------|",
            ]
        )
        for model_id, s in modelos.items():
            lines.append(
                f"| {model_id} | {s.cobertura:.1%} | {s.recall:.1%} | {s.latencia_ms_media:.1f} | {s.llm_invocations} |"
            )
        lines.append("")

    lines.extend(
        [
            "## Kill switch",
            "",
            "Defina `ENABLE_CATEGORIZACAO_LLM=False` para desativar instantaneamente o fallback LLM.",
            "",
            "## Próximos passos",
            "",
            "1. Validar em staging com opt-in interno",
            "2. Benchmark com API real (fora do CI)",
            "3. Monitorar `LLMRequestLog` no admin",
            "",
        ]
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")
    canonical = LLM_DIR / "COMPARATIVO_MODELOS_GEMINI.md"
    canonical.write_text(output_path.read_text(encoding="utf-8"), encoding="utf-8")
    return output_path
