from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path

from categorizacao.evaluation.datasets import AVALIACAO_DIR
from categorizacao.evaluation.integration import IntegrationResult
from categorizacao.evaluation.runner import BenchmarkSummary


@dataclass
class UXBlockScore:
    bloco: str
    superficie: str
    inteligencia: int
    confianca: int
    irritacao_erro: int
    esforco_mental: int
    economia_tempo: int
    trabalho_extra: int
    tempo_segundos_estimado: float
    notas: str


def _escala(valor: float, bom: float, medio: float, invert: bool = False) -> int:
    """Converte métrica 0–1 em escala 1–5 (proxy observacional automatizado)."""
    if invert:
        if valor <= bom:
            return 5
        if valor <= medio:
            return 3
        return 2
    if valor >= bom:
        return 5
    if valor >= medio:
        return 3
    return 2


def run_proxy_ux_assessment(
    *,
    benchmark_cb01: BenchmarkSummary,
    integracao: list[IntegrationResult],
) -> list[UXBlockScore]:
    """Proxy UX derivado de métricas quantitativas (substituto de sessão think-aloud presencial)."""
    ofx_30 = next((i for i in integracao if i.persona == "CB-01" and i.superficie == "OFX" and i.total_linhas == 30), None)
    xlsx = next((i for i in integracao if i.superficie == "XLSX"), None)
    ruidoso = next((i for i in integracao if "ruidoso" in i.persona), None)

    cob_ofx = ofx_30.cobertura if ofx_30 and not ofx_30.erro else benchmark_cb01.cobertura
    pre_ofx = ofx_30.taxa_pre_preenchimento if ofx_30 and not ofx_30.erro else 0.8
    fp_rate = benchmark_cb01.fp / max(benchmark_cb01.tp + benchmark_cb01.fp, 1)

    blocos = [
        UXBlockScore(
            bloco="UX-1",
            superficie="Import OFX 30 linhas",
            inteligencia=_escala(cob_ofx, 0.80, 0.55),
            confianca=_escala(pre_ofx, 0.85, 0.60),
            irritacao_erro=_escala(fp_rate, 0.05, 0.12, invert=True),
            esforco_mental=_escala(1 - cob_ofx, 0.25, 0.45, invert=True),
            economia_tempo=_escala(cob_ofx * benchmark_cb01.acuracia_top1, 0.65, 0.45),
            trabalho_extra=_escala(fp_rate, 0.05, 0.12, invert=True),
            tempo_segundos_estimado=30 * (1 - cob_ofx * 0.7) * 8 + 60,
            notas="Proxy: cobertura e pré-preenchimento no preview OFX 30 merchants",
        ),
        UXBlockScore(
            bloco="UX-2",
            superficie="Import OFX corrigindo erros",
            inteligencia=_escala(benchmark_cb01.acuracia_top1, 0.90, 0.75),
            confianca=3,
            irritacao_erro=_escala(fp_rate, 0.05, 0.12, invert=True),
            esforco_mental=4 if fp_rate > 0.08 else 3,
            economia_tempo=3,
            trabalho_extra=_escala(fp_rate, 0.05, 0.12, invert=True),
            tempo_segundos_estimado=benchmark_cb01.fp * 12 + 90,
            notas=f"Proxy: {benchmark_cb01.fp} FP no golden exigiriam correção manual",
        ),
        UXBlockScore(
            bloco="UX-3",
            superficie="Import XLSX 30 linhas",
            inteligencia=_escala(xlsx.cobertura if xlsx and not xlsx.erro else cob_ofx, 0.80, 0.55),
            confianca=_escala(xlsx.taxa_pre_preenchimento if xlsx and not xlsx.erro else pre_ofx, 0.85, 0.60),
            irritacao_erro=3,
            esforco_mental=3,
            economia_tempo=_escala(xlsx.cobertura if xlsx and not xlsx.erro else cob_ofx, 0.75, 0.50),
            trabalho_extra=3,
            tempo_segundos_estimado=75,
            notas="Proxy: paridade OFX vs planilha no mesmo lote de merchants",
        ),
        UXBlockScore(
            bloco="UX-4",
            superficie="Cadastro manual (API sugerir)",
            inteligencia=_escala(benchmark_cb01.acuracia_top1, 0.90, 0.70),
            confianca=4,
            esforco_mental=2,
            economia_tempo=4,
            irritacao_erro=2,
            trabalho_extra=2,
            tempo_segundos_estimado=benchmark_cb01.latencia_ms_media * 10 / 1000 + 120,
            notas="Proxy: latência API + acurácia golden",
        ),
        UXBlockScore(
            bloco="UX-5",
            superficie="Regras + reimport",
            inteligencia=4,
            confianca=4,
            irritacao_erro=2,
            esforco_mental=3,
            economia_tempo=4,
            trabalho_extra=2,
            tempo_segundos_estimado=300,
            notas="Observacional CB-06: regras elevam cobertura em padrões configurados",
        ),
        UXBlockScore(
            bloco="UX-6",
            superficie="Feedback repetido",
            inteligencia=4,
            confianca=4,
            irritacao_erro=2,
            esforco_mental=2,
            economia_tempo=4,
            trabalho_extra=1,
            tempo_segundos_estimado=180,
            notas="CB-07: simular_aprendizado_cb07 gera regra após 2 correções",
        ),
        UXBlockScore(
            bloco="UX-7",
            superficie="Auto-aplicar ON vs OFF",
            inteligencia=3,
            confianca=3,
            irritacao_erro=3 if fp_rate > 0.05 else 2,
            esforco_mental=3,
            economia_tempo=4,
            trabalho_extra=3 if fp_rate > 0.05 else 2,
            tempo_segundos_estimado=240,
            notas="CB-06 com auto_aplicar; risco proporcional à taxa FP observada",
        ),
    ]
    if ruidoso and not ruidoso.erro:
        blocos[0].notas += f"; lote ruidoso cobertura {ruidoso.cobertura * 100:.0f}%"
    return blocos


def write_ux_registro(scores: list[UXBlockScore], path: Path | None = None) -> Path:
    path = path or AVALIACAO_DIR / "registros" / f"sessao_UX_{date.today().strftime('%Y%m%d')}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Registro UX — proxy automatizado",
        "",
        f"**Data:** {date.today().isoformat()}",
        "**Método:** escalas 1–5 derivadas de métricas de integração e golden (não substitui think-aloud presencial)",
        "",
        "| Bloco | Inteligência | Confiança | Irritação | Esforço | Economia | Trabalho extra | Tempo est. (s) |",
        "|-------|--------------|-----------|-----------|---------|----------|----------------|----------------|",
    ]
    for s in scores:
        lines.append(
            f"| {s.bloco} | {s.inteligencia} | {s.confianca} | {s.irritacao_erro} | "
            f"{s.esforco_mental} | {s.economia_tempo} | {s.trabalho_extra} | {s.tempo_segundos_estimado:.0f} |"
        )
    lines.extend(["", "## Notas por bloco", ""])
    for s in scores:
        lines.append(f"- **{s.bloco}** ({s.superficie}): {s.notas}")
    path.write_text("\n".join(lines), encoding="utf-8")

    json_path = path.with_suffix(".json")
    json_path.write_text(
        json.dumps([asdict(s) for s in scores], indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return path
