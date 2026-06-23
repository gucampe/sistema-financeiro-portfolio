from __future__ import annotations

import csv
import json
from dataclasses import dataclass, field
from pathlib import Path

from categorizacao.evaluation.datasets import GoldenCase
from categorizacao.evaluation.longitudinal.constants import LONGITUDINAL_DIR
from categorizacao.evaluation.runner import BenchmarkSummary, run_benchmark
from categorizacao.models import MemoriaMerchantUsuario, ModeloClassificacaoUsuario, RegraCategorizacao
from transacoes.models import Transacao


@dataclass
class CheckpointSnapshot:
    persona: str
    checkpoint: str
    semana: int
    tx_count: int
    memoria_count: int
    memoria_score_alto: int
    regras_aprendidas: int
    regras_manuais: int
    eventos_total: int
    ml_ativo: bool
    ml_amostras: int
    reimport: BenchmarkSummary | None = None
    prova: BenchmarkSummary | None = None
    feedback_aceitas: int = 0
    feedback_corrigidas: int = 0
    feedback_ignoradas: int = 0


@dataclass
class PersonaRunState:
    persona: str
    snapshots: list[CheckpointSnapshot] = field(default_factory=list)
    feedback_total: dict[str, int] = field(default_factory=lambda: {
        "aceitas": 0, "corrigidas": 0, "ignoradas": 0,
    })


def capture_snapshot(
    user,
    persona: str,
    checkpoint: str,
    semana: int,
    reimport_cases: list[GoldenCase],
    prova_cases: list[GoldenCase],
    feedback_delta: dict[str, int] | None = None,
) -> CheckpointSnapshot:
    from categorizacao.models import EventoCategorizacao

    mem_qs = MemoriaMerchantUsuario.objects.filter(usuario=user)
    ml = ModeloClassificacaoUsuario.objects.filter(usuario=user).first()
    snap = CheckpointSnapshot(
        persona=persona,
        checkpoint=checkpoint,
        semana=semana,
        tx_count=Transacao.objects.filter(usuario=user).count(),
        memoria_count=mem_qs.count(),
        memoria_score_alto=mem_qs.filter(score__gte=0.65).count(),
        regras_aprendidas=RegraCategorizacao.objects.filter(
            usuario=user, origem="aprendida", ativa=True
        ).count(),
        regras_manuais=RegraCategorizacao.objects.filter(
            usuario=user, origem="manual", ativa=True
        ).count(),
        eventos_total=EventoCategorizacao.objects.filter(usuario=user).count(),
        ml_ativo=bool(ml and ml.amostras_treino and ml.amostras_treino >= 50),
        ml_amostras=ml.amostras_treino if ml else 0,
        reimport=run_benchmark(user, reimport_cases),
        prova=run_benchmark(user, prova_cases),
    )
    if feedback_delta:
        snap.feedback_aceitas = feedback_delta.get("aceitas", 0)
        snap.feedback_corrigidas = feedback_delta.get("corrigidas", 0)
        snap.feedback_ignoradas = feedback_delta.get("ignoradas", 0)
    return snap


def export_memoria_csv(user, persona: str, checkpoint: str, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"memoria_{persona}_{checkpoint}.csv"
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            ["merchant_key", "categoria", "confirmacoes", "correcoes", "score"]
        )
        for m in MemoriaMerchantUsuario.objects.filter(usuario=user).select_related("categoria"):
            writer.writerow(
                [m.merchant_key, m.categoria.nome, m.confirmacoes, m.correcoes, m.score]
            )
    return path


def save_checkpoint_json(snapshot: CheckpointSnapshot, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    def _bench_dict(b: BenchmarkSummary | None) -> dict | None:
        if b is None:
            return None
        return {
            "total": b.total,
            "tp": b.tp,
            "fp": b.fp,
            "fn": b.fn,
            "sem_sugestao_ok": b.sem_sugestao_ok,
            "cobertura": b.cobertura,
            "acuracia_top1": b.acuracia_top1,
            "recall": b.recall,
            "por_bucket": dict(b.por_bucket),
            "por_fonte": {k: dict(v) for k, v in b.por_fonte.items()},
        }

    payload = {
        "persona": snapshot.persona,
        "checkpoint": snapshot.checkpoint,
        "semana": snapshot.semana,
        "tx_count": snapshot.tx_count,
        "memoria_count": snapshot.memoria_count,
        "memoria_score_alto": snapshot.memoria_score_alto,
        "regras_aprendidas": snapshot.regras_aprendidas,
        "regras_manuais": snapshot.regras_manuais,
        "eventos_total": snapshot.eventos_total,
        "ml_ativo": snapshot.ml_ativo,
        "ml_amostras": snapshot.ml_amostras,
        "feedback_aceitas": snapshot.feedback_aceitas,
        "feedback_corrigidas": snapshot.feedback_corrigidas,
        "feedback_ignoradas": snapshot.feedback_ignoradas,
        "reimport": _bench_dict(snapshot.reimport),
        "prova": _bench_dict(snapshot.prova),
    }
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def checkpoints_dir() -> Path:
    return LONGITUDINAL_DIR / "checkpoints"
