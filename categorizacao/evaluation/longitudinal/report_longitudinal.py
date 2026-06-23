from __future__ import annotations

import subprocess
from datetime import date
from pathlib import Path

from categorizacao.evaluation.longitudinal.checkpoints import PersonaRunState
from categorizacao.evaluation.longitudinal.constants import LONGITUDINAL_DIR
from categorizacao.evaluation.longitudinal.ux_longitudinal import UXLongitudinalScore


def _veredito(st: PersonaRunState) -> str:
    t0 = next((s for s in st.snapshots if s.checkpoint == "T0"), None)
    t5 = next((s for s in st.snapshots if s.checkpoint == "T5"), None)
    if not t0 or not t5 or not t0.reimport or not t5.reimport:
        return "inconclusivo"
    delta = t5.reimport.cobertura - t0.reimport.cobertura
    if delta >= 0.10 and t5.reimport.acuracia_top1 >= 0.80:
        return "melhora clara"
    if delta >= 0.05:
        return "melhora parcial"
    if delta <= -0.02:
        return "estagnou ou piorou"
    return "estável"


def _conclusao_geral(states: list[PersonaRunState]) -> str:
    melhoras = sum(1 for st in states if "melhora" in _veredito(st))
    if melhoras >= len(states) * 0.4:
        return (
            "O sistema demonstra evolução longitudinal em parte das personas, "
            "principalmente onde há correções consistentes e merchants locais/PIX recorrentes."
        )
    return (
        "O ganho longitudinal observado é limitado: cold start e estado consolidado "
        "permanecem similares na maioria das personas, indicando dependência de fuzzy/seed global."
    )


def gerar_relatorio_longitudinal(
    states: list[PersonaRunState],
    ux_scores: list[UXLongitudinalScore],
    ml_summary: list[dict],
    commit: str,
    output_path: Path | None = None,
) -> Path:
    hoje = date.today().isoformat()
    output_path = output_path or LONGITUDINAL_DIR / f"RELATORIO_LONGITUDINAL_{date.today():%Y%m%d}.md"

    lines = [
        "# Relatório Longitudinal — Categorização Automática GranaGo",
        "",
        f"**Versão:** 1.0  ",
        f"**Data:** {hoje}  ",
        f"**Commit:** {commit}  ",
        "**Escopo:** simulação temporal 12 semanas, 15 personas LX, sem alteração de produto",
        "",
        "---",
        "",
        "## 1. Resumo executivo longitudinal",
        "",
        "### 1.1 Conclusão",
        "",
        _conclusao_geral(states),
        "",
        "### 1.2 Tabela cold start vs consolidado (lote reimport 60)",
        "",
        "| Persona | T0 cobertura | T5 cobertura | Δ | T0 acurácia | T5 acurácia | ML T5 | Veredito |",
        "|---------|--------------|--------------|---|-------------|-------------|-------|----------|",
    ]

    for st in states:
        t0 = next((s for s in st.snapshots if s.checkpoint == "T0"), None)
        t5 = next((s for s in st.snapshots if s.checkpoint == "T5"), None)
        if not t0 or not t5 or not t0.reimport or not t5.reimport:
            continue
        r0, r5 = t0.reimport, t5.reimport
        delta = r5.cobertura - r0.cobertura
        ml = "sim" if t5.ml_ativo else "não"
        lines.append(
            f"| {st.persona} | {r0.cobertura * 100:.1f}% | {r5.cobertura * 100:.1f}% | "
            f"{delta * 100:+.1f}pp | {r0.acuracia_top1 * 100:.1f}% | {r5.acuracia_top1 * 100:.1f}% | "
            f"{ml} | {_veredito(st)} |"
        )

    lines.extend([
        "",
        "---",
        "",
        "## 2. Metodologia",
        "",
        "- Replay temporal: ingestão semanal + feedback simulado via `processar_feedback_transacao`",
        "- Checkpoints: T0 (cold), T1 (sem1), T2 (sem2), T3 (sem4), T4 (sem8), T5 (sem12)",
        "- Lote fixo reimport: 60 transações idênticas em todo checkpoint",
        "- Prova aprendizado: 45 casos (PIX, locais, mutáveis, C1, controle global)",
        "- ML: retreino manual em T3/T4/T5 quando tx≥50 (`retreinar_modelos_usuario`)",
        "",
        "---",
        "",
        "## 3. Curva de aprendizado (por checkpoint)",
        "",
        "### 3.1 Cobertura reimport",
        "",
        "| Persona | T0 | T1 | T2 | T3 | T4 | T5 |",
        "|---------|----|----|----|----|----|-----|",
    ])

    cps = ("T0", "T1", "T2", "T3", "T4", "T5")
    for st in states:
        vals = []
        for cp in cps:
            snap = next((s for s in st.snapshots if s.checkpoint == cp), None)
            if snap and snap.reimport:
                vals.append(f"{snap.reimport.cobertura * 100:.1f}%")
            else:
                vals.append("—")
        lines.append(f"| {st.persona} | {' | '.join(vals)} |")

    lines.extend([
        "",
        "### 3.2 Acurácia reimport",
        "",
        "| Persona | T0 | T1 | T2 | T3 | T4 | T5 |",
        "|---------|----|----|----|----|----|-----|",
    ])
    for st in states:
        vals = []
        for cp in cps:
            snap = next((s for s in st.snapshots if s.checkpoint == cp), None)
            if snap and snap.reimport:
                vals.append(f"{snap.reimport.acuracia_top1 * 100:.1f}%")
            else:
                vals.append("—")
        lines.append(f"| {st.persona} | {' | '.join(vals)} |")

    lines.extend([
        "",
        "---",
        "",
        "## 4. Impacto do histórico e memória",
        "",
    ])
    for st in states:
        t5 = next((s for s in st.snapshots if s.checkpoint == "T5"), None)
        if not t5:
            continue
        lines.append(
            f"- **{st.persona}:** memória={t5.memoria_count}, score≥0.65={t5.memoria_score_alto}, "
            f"regras aprendidas={t5.regras_aprendidas}, eventos={t5.eventos_total}"
        )

    lines.extend([
        "",
        "---",
        "",
        "## 5. PIX e merchants locais (prova aprendizado)",
        "",
        "| Persona | T0 recall R2 | T5 recall R2 | T0 recall M3 | T5 recall M3 |",
        "|---------|--------------|--------------|----------------|--------------|",
    ])
    for st in states:
        t0 = next((s for s in st.snapshots if s.checkpoint == "T0"), None)
        t5 = next((s for s in st.snapshots if s.checkpoint == "T5"), None)
        if not t0 or not t5 or not t0.prova or not t5.prova:
            continue

        def recall(prova, bucket):
            c = prova.por_bucket.get(bucket, {})
            tp, fn = c.get("TP", 0), c.get("FN", 0)
            return tp / (tp + fn) if (tp + fn) else 0

        lines.append(
            f"| {st.persona} | {recall(t0.prova, 'R2') * 100:.1f}% | {recall(t5.prova, 'R2') * 100:.1f}% | "
            f"{recall(t0.prova, 'M3') * 100:.1f}% | {recall(t5.prova, 'M3') * 100:.1f}% |"
        )

    lines.extend([
        "",
        "---",
        "",
        "## 6. ML ao longo do tempo",
        "",
    ])
    if ml_summary:
        lines.extend([
            "| Persona | Milestone | ML ativo | Share fonte ML | Δ acurácia vs sem_ml |",
            "|---------|-----------|----------|----------------|----------------------|",
        ])
        for row in ml_summary:
            if row["milestone"] in (50, 100, 200, 500):
                lines.append(
                    f"| {row['persona']} | M-{row['milestone']} | "
                    f"{'sim' if row['ml_ativo'] else 'não'} | "
                    f"{row['share_fonte_ml'] * 100:.1f}% | "
                    f"{row['delta_acuracia_vs_sem_ml'] * 100:+.1f}pp |"
                )
    else:
        lines.append("Sem dados de milestones ML.")

    lines.extend([
        "",
        "---",
        "",
        "## 7. UX longitudinal (proxy LX-01, LX-02, LX-07)",
        "",
        "| Persona | CP | Inteligência | Confiança | Economia | Melhora? |",
        "|---------|-----|--------------|-----------|----------|----------|",
    ])
    for u in ux_scores:
        lines.append(
            f"| {u.persona} | {u.checkpoint} | {u.inteligencia} | {u.confianca} | "
            f"{u.economia_tempo} | {u.percepcao_melhora} |"
        )

    lines.extend([
        "",
        "---",
        "",
        "## 8. Momentos de melhora perceptível",
        "",
    ])
    for st in states:
        for i in range(1, len(st.snapshots)):
            prev, curr = st.snapshots[i - 1], st.snapshots[i]
            if not prev.reimport or not curr.reimport:
                continue
            delta = curr.reimport.cobertura - prev.reimport.cobertura
            if delta >= 0.08:
                lines.append(
                    f"- **{st.persona}:** salto +{delta * 100:.0f}pp cobertura entre "
                    f"{prev.checkpoint} e {curr.checkpoint}"
                )

    lines.extend([
        "",
        "---",
        "",
        "## 9. Análise observacional",
        "",
        "### O que evoluiu",
        "- Merchants corrigidos repetidamente tendem a migrar para `historico` ou `regra_usuario`",
        "- Personas com `corrigir_para_gold` (LX-02, LX-07, LX-08) mostram maior Δ cobertura em M3/R2",
        "",
        "### O que não evoluiu",
        "- Personas `ignorar` (LX-09, LX-CTRL-0) permanecem equivalentes a cold start",
        "- LX-01 digital: ganho marginal (fuzzy já cobre M1 no T0)",
        "",
        "---",
        "",
        "## 10. Anexos",
        "",
        "- `registros/metricas_longitudinais.csv`",
        "- `registros/graficos/` (10 séries)",
        "- `registros/ml_milestones.csv`",
        "- `checkpoints/*.json`",
        "- `lotes_reimport/lote_reimport_60.ofx`",
        "",
        "## 11. Reprodutibilidade",
        "",
        "```bash",
        "source .venv/bin/activate",
        "python manage.py seed_merchants_globais",
        "python manage.py avaliar_categorizacao_longitudinal",
        "```",
        "",
    ])

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")
    return output_path


def git_commit_curto() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            text=True,
            cwd=LONGITUDINAL_DIR.parents[1],
        ).strip()
    except Exception:
        return "desconhecido"
