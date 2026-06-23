from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path

from categorizacao.evaluation.longitudinal.checkpoints import PersonaRunState
from categorizacao.evaluation.longitudinal.constants import LONGITUDINAL_DIR


@dataclass
class UXLongitudinalScore:
    persona: str
    checkpoint: str
    inteligencia: int
    confianca: int
    economia_tempo: int
    irritacao: int
    tempo_import_proxy: float
    percepcao_melhora: str
    notas: str


def _snap(st: PersonaRunState, cp: str):
    return next((s for s in st.snapshots if s.checkpoint == cp), None)


def run_ux_longitudinal_proxy(states: list[PersonaRunState]) -> list[UXLongitudinalScore]:
    """Proxy UX para LX-01, LX-02, LX-07 em T0, T2, T5."""
    target = {"LX-01", "LX-02", "LX-07"}
    checkpoints = ("T0", "T2", "T5")
    scores: list[UXLongitudinalScore] = []

    for st in states:
        if st.persona not in target:
            continue
        t0 = _snap(st, "T0")
        for cp in checkpoints:
            snap = _snap(st, cp)
            if not snap or not snap.reimport:
                continue
            r = snap.reimport
            cob = r.cobertura
            corr_rate = snap.feedback_corrigidas / max(
                snap.feedback_aceitas + snap.feedback_corrigidas, 1
            )
            share_hist = 0.0
            total_f = sum(c.get("TP", 0) + c.get("FP", 0) for c in r.por_fonte.values())
            if total_f:
                h = r.por_fonte.get("historico", {})
                share_hist = (h.get("TP", 0) + h.get("FP", 0)) / total_f

            intel = 5 if cob >= 0.75 and share_hist > 0.15 else (3 if cob >= 0.5 else 2)
            conf = 5 if cob >= 0.8 and r.acuracia_top1 >= 0.85 else (3 if cob >= 0.55 else 2)
            eco = 5 if r.fp + r.fn < 10 else (3 if r.fp + r.fn < 20 else 2)
            irr = 5 if corr_rate < 0.2 else (3 if corr_rate < 0.4 else 2)
            tempo = r.fp * 8 + r.fn * 15 + 30

            melhora = "nao"
            if t0 and t0.reimport and cp != "T0":
                delta = cob - t0.reimport.cobertura
                if delta >= 0.15:
                    melhora = "sim"
                elif delta >= 0.05:
                    melhora = "parcial"

            scores.append(
                UXLongitudinalScore(
                    persona=st.persona,
                    checkpoint=cp,
                    inteligencia=intel,
                    confianca=conf,
                    economia_tempo=eco,
                    irritacao=irr,
                    tempo_import_proxy=tempo,
                    percepcao_melhora=melhora,
                    notas=f"cobertura={cob:.1%} share_historico={share_hist:.1%}",
                )
            )
    return scores


def write_ux_registro(scores: list[UXLongitudinalScore], path: Path | None = None) -> Path:
    path = path or LONGITUDINAL_DIR / "registros" / f"sessao_UX_longitudinal_{date.today():%Y%m%d}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# UX Longitudinal — proxy automatizado",
        "",
        f"**Data:** {date.today().isoformat()}",
        "**Personas:** LX-01, LX-02, LX-07 | **Checkpoints:** T0, T2, T5",
        "",
        "| Persona | CP | Inteligência | Confiança | Economia | Irritação | Tempo proxy (s) | Melhora? |",
        "|---------|-----|--------------|-----------|----------|-----------|-----------------|----------|",
    ]
    for s in scores:
        lines.append(
            f"| {s.persona} | {s.checkpoint} | {s.inteligencia} | {s.confianca} | "
            f"{s.economia_tempo} | {s.irritacao} | {s.tempo_import_proxy:.0f} | {s.percepcao_melhora} |"
        )
    lines.extend(["", "## Notas", ""])
    for s in scores:
        lines.append(f"- **{s.persona} {s.checkpoint}:** {s.notas}")
    path.write_text("\n".join(lines), encoding="utf-8")

    json_path = path.with_suffix(".json")
    json_path.write_text(
        json.dumps([asdict(s) for s in scores], indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return path
