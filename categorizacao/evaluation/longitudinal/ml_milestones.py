from __future__ import annotations

import csv
from pathlib import Path

from django.core.management import call_command

from categorizacao.evaluation.longitudinal.constants import LONGITUDINAL_DIR, ML_MILESTONES
from categorizacao.evaluation.longitudinal.feedback_sim import ingest_row
from categorizacao.evaluation.longitudinal.ledger import load_ledger_csv
from categorizacao.evaluation.longitudinal.personas_lx import PERSONAS_BY_CODE, reset_persona_state
from categorizacao.evaluation.longitudinal.prova import prova_as_golden
from categorizacao.evaluation.runner import run_ablation, run_benchmark
from categorizacao.models import ModeloClassificacaoUsuario
from contas.models import Conta
from transacoes.models import Transacao


ML_PERSONAS = ("LX-04", "LX-08", "LX-CTRL-ML", "LX-CTRL-CORR", "LX-06")


def _ml_subset_cases():
    """30 casos M3-focused para benchmark ML."""
    prova = prova_as_golden()
    m3 = [c for c in prova if c.bucket in ("M3", "R2")]
    if len(m3) >= 30:
        return m3[:30]
    return prova[:30]


def run_ml_milestones_for_user(user, persona_code: str) -> list[dict]:
    """Trunca/replay histórico até N transações e mede ML em cada milestone."""
    spec = PERSONAS_BY_CODE[persona_code]
    ledger_path = LONGITUDINAL_DIR / "ledger" / f"{persona_code.lower()}_ledger.csv"
    rows = load_ledger_csv(ledger_path)
    conta = Conta.objects.get(usuario=user, nome="Conta Longitudinal")
    ml_cases = _ml_subset_cases()
    results: list[dict] = []

    for milestone in ML_MILESTONES:
        reset_persona_state(user)
        count = 0
        for row in rows:
            if count >= milestone:
                break
            ingest_row(user, conta, row, spec.feedback_policy)
            count += 1

        tx_n = Transacao.objects.filter(usuario=user).count()
        ml_ativo = False
        share_ml = 0.0
        ml_tp = 0

        if milestone >= 50:
            try:
                call_command("retreinar_modelos_usuario", usuario=user.pk, verbosity=0)
            except Exception:
                pass
            modelo = ModeloClassificacaoUsuario.objects.filter(usuario=user).first()
            ml_ativo = bool(modelo and modelo.amostras_treino and modelo.amostras_treino >= 50)

        bench = run_benchmark(user, ml_cases)
        ablation = run_ablation(user, ml_cases, max_cases=len(ml_cases))
        full = ablation.get("pipeline_completo")
        sem_ml = ablation.get("sem_ml")

        if full:
            total_fonte = sum(
                c.get("TP", 0) + c.get("FP", 0) for c in full.por_fonte.values()
            )
            ml_n = full.por_fonte.get("ml", {})
            share_ml = (ml_n.get("TP", 0) + ml_n.get("FP", 0)) / total_fonte if total_fonte else 0
            ml_tp = ml_n.get("TP", 0)

        delta_acuracia = 0.0
        if full and sem_ml:
            delta_acuracia = full.acuracia_top1 - sem_ml.acuracia_top1

        results.append(
            {
                "persona": persona_code,
                "milestone": milestone,
                "tx_count": tx_n,
                "ml_ativo": ml_ativo,
                "share_fonte_ml": share_ml,
                "ml_tp": ml_tp,
                "cobertura_ml_subset": bench.cobertura,
                "acuracia_ml_subset": bench.acuracia_top1,
                "delta_acuracia_vs_sem_ml": delta_acuracia,
                "taxa_sem_sugestao": bench.fn / bench.total if bench.total else 0,
            }
        )
    return results


def write_ml_milestones_csv(all_results: list[dict], path: Path | None = None) -> Path:
    path = path or LONGITUDINAL_DIR / "registros" / "ml_milestones.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    if not all_results:
        return path
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(all_results[0].keys()))
        writer.writeheader()
        writer.writerows(all_results)
    return path


def run_ml_milestones(users: dict[str, object], personas: list[str] | None = None) -> list[dict]:
    personas = personas or list(ML_PERSONAS)
    all_results: list[dict] = []
    for code in personas:
        if code not in users:
            continue
        all_results.extend(run_ml_milestones_for_user(users[code], code))
    return all_results
