from __future__ import annotations

from dataclasses import dataclass

from django.core.management import call_command
from categorizacao.evaluation.datasets import GoldenCase
from categorizacao.evaluation.longitudinal.checkpoints import (
    PersonaRunState,
    capture_snapshot,
    checkpoints_dir,
    export_memoria_csv,
    save_checkpoint_json,
)
from categorizacao.evaluation.longitudinal.constants import LONGITUDINAL_DIR, WEEK_TO_CHECKPOINT
from categorizacao.evaluation.longitudinal.feedback_sim import ingest_row
from categorizacao.evaluation.longitudinal.ledger import (
    load_ledger_csv,
    load_reimport_ledger,
)
from categorizacao.evaluation.longitudinal.personas_lx import PERSONAS_BY_CODE, reset_persona_state
from categorizacao.evaluation.longitudinal.prova import prova_as_golden
from contas.models import Conta


@dataclass
class ReplayConfig:
    weeks: int = 12
    checkpoints: tuple[str, ...] = ("T0", "T1", "T2", "T3", "T4", "T5")
    retreinar_ml_em: tuple[str, ...] = ("T3", "T4", "T5")
    min_tx_ml: int = 50


def _week_checkpoint_map(weeks: int) -> dict[int, str]:
    mapping = dict(WEEK_TO_CHECKPOINT)
    if weeks < 12:
        mapping[weeks] = "T5"
    return {w: cp for w, cp in mapping.items() if w <= weeks}


def run_persona_replay(
    user,
    persona_code: str,
    config: ReplayConfig | None = None,
) -> PersonaRunState:
    config = config or ReplayConfig()
    spec = PERSONAS_BY_CODE[persona_code]
    reset_persona_state(user)
    conta = Conta.objects.get(usuario=user, nome="Conta Longitudinal")

    ledger_path = LONGITUDINAL_DIR / "ledger" / f"{persona_code.lower()}_ledger.csv"
    if not ledger_path.exists():
        from categorizacao.evaluation.longitudinal.ledger import write_all_datasets
        write_all_datasets(weeks=config.weeks)

    all_rows = load_ledger_csv(ledger_path)
    reimport_cases: list[GoldenCase] = [r.to_golden() for r in load_reimport_ledger()]
    prova_cases = prova_as_golden()
    week_cp = _week_checkpoint_map(config.weeks)
    active_cps = set(config.checkpoints)

    state = PersonaRunState(persona=persona_code)
    cp_dir = checkpoints_dir()

    if "T0" in active_cps:
        snap = capture_snapshot(user, persona_code, "T0", 0, reimport_cases, prova_cases)
        state.snapshots.append(snap)
        save_checkpoint_json(snap, cp_dir / f"{persona_code}_T0.json")
        export_memoria_csv(user, persona_code, "T0", LONGITUDINAL_DIR / "registros" / "memoria")

    week_feedback: dict[str, int] = {"aceitas": 0, "corrigidas": 0, "ignoradas": 0}

    for semana in range(1, config.weeks + 1):
        sem_rows = [r for r in all_rows if r.semana_simulada == semana]
        for row in sem_rows:
            stats = ingest_row(user, conta, row, spec.feedback_policy)
            week_feedback["aceitas"] += stats.aceitas
            week_feedback["corrigidas"] += stats.corrigidas
            week_feedback["ignoradas"] += stats.ignoradas
            state.feedback_total["aceitas"] += stats.aceitas
            state.feedback_total["corrigidas"] += stats.corrigidas
            state.feedback_total["ignoradas"] += stats.ignoradas

        cp = week_cp.get(semana)
        if cp and cp in active_cps and cp != "T0":
            from transacoes.models import Transacao
            tx_count = Transacao.objects.filter(usuario=user).count()
            if tx_count >= config.min_tx_ml and cp in config.retreinar_ml_em:
                try:
                    call_command("retreinar_modelos_usuario", usuario=user.pk, verbosity=0)
                except Exception:
                    pass

            snap = capture_snapshot(
                user,
                persona_code,
                cp,
                semana,
                reimport_cases,
                prova_cases,
                feedback_delta=dict(week_feedback),
            )
            state.snapshots.append(snap)
            save_checkpoint_json(snap, cp_dir / f"{persona_code}_{cp}.json")
            export_memoria_csv(user, persona_code, cp, LONGITUDINAL_DIR / "registros" / "memoria")
            week_feedback = {"aceitas": 0, "corrigidas": 0, "ignoradas": 0}

    return state


def run_all_replays(
    users: dict[str, object],
    config: ReplayConfig | None = None,
) -> list[PersonaRunState]:
    states: list[PersonaRunState] = []
    for code, user in users.items():
        states.append(run_persona_replay(user, code, config))
    return states
