from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path

from categorizacao.evaluation.longitudinal.checkpoints import CheckpointSnapshot, PersonaRunState
from categorizacao.evaluation.longitudinal.constants import LONGITUDINAL_DIR
from categorizacao.evaluation.runner import BenchmarkSummary


def _metric_rows_from_snapshot(snap: CheckpointSnapshot) -> list[tuple[str, str, str, float]]:
    rows: list[tuple[str, str, str, float]] = []
    persona, cp = snap.persona, snap.checkpoint

    def add(metrica: str, valor: float) -> None:
        rows.append((persona, cp, metrica, valor))

    add("tx_count", float(snap.tx_count))
    add("memoria_count", float(snap.memoria_count))
    add("memoria_score_alto", float(snap.memoria_score_alto))
    add("regras_aprendidas", float(snap.regras_aprendidas))
    add("eventos_total", float(snap.eventos_total))
    add("ml_ativo", 1.0 if snap.ml_ativo else 0.0)
    add("ml_amostras", float(snap.ml_amostras))
    add("feedback_aceitas", float(snap.feedback_aceitas))
    add("feedback_corrigidas", float(snap.feedback_corrigidas))
    add("feedback_ignoradas", float(snap.feedback_ignoradas))

    if snap.reimport:
        r = snap.reimport
        add("cobertura_reimport", r.cobertura)
        add("acuracia_reimport", r.acuracia_top1)
        add("recall_reimport", r.recall)
        add("fp_reimport", float(r.fp))
        add("fn_reimport", float(r.fn))
        add("taxa_sem_sugestao_reimport", (r.fn + r.sem_sugestao_ok) / r.total if r.total else 0)
        add("tempo_revisao_proxy", r.fp * 8 + r.fn * 15)
        _add_fonte_shares(add, r, "reimport")
        _add_bucket_recall(add, r, "reimport")

    if snap.prova:
        p = snap.prova
        add("cobertura_prova", p.cobertura)
        add("acuracia_prova", p.acuracia_top1)
        add("recall_prova", p.recall)
        _add_fonte_shares(add, p, "prova")
        _add_bucket_recall(add, p, "prova")

        historico_tp = sum(
            1 for res in p.resultados
            if res.resultado == "TP" and res.fonte in ("historico", "regra_usuario")
        )
        com_sug = p.tp + p.fp
        add("taxa_reaproveitamento_prova", historico_tp / com_sug if com_sug else 0)

    return rows


def _add_fonte_shares(add, bench: BenchmarkSummary, prefix: str) -> None:
    total_com_fonte = sum(
        counts.get("TP", 0) + counts.get("FP", 0)
        for counts in bench.por_fonte.values()
    )
    if not total_com_fonte:
        return
    for fonte, counts in bench.por_fonte.items():
        n = counts.get("TP", 0) + counts.get("FP", 0)
        add(f"share_fonte_{fonte}_{prefix}", n / total_com_fonte)


def _add_bucket_recall(add, bench: BenchmarkSummary, prefix: str) -> None:
    for bucket in ("M1", "M3", "R2", "C1", "MUT"):
        counts = bench.por_bucket.get(bucket, {})
        tp = counts.get("TP", 0)
        fn = counts.get("FN", 0)
        denom = tp + fn
        add(f"recall_{bucket}_{prefix}", tp / denom if denom else 0)


def write_metricas_longitudinais(states: list[PersonaRunState], path: Path | None = None) -> Path:
    path = path or LONGITUDINAL_DIR / "registros" / "metricas_longitudinais.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    all_rows: list[tuple[str, str, str, float]] = []
    for state in states:
        for snap in state.snapshots:
            all_rows.extend(_metric_rows_from_snapshot(snap))

    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["persona", "checkpoint", "metrica", "valor"])
        for row in all_rows:
            writer.writerow(row)
    return path


def write_charts_data(states: list[PersonaRunState], out_dir: Path | None = None) -> dict[str, Path]:
    """Exporta CSVs para os 10 gráficos previstos no plano."""
    out_dir = out_dir or LONGITUDINAL_DIR / "registros" / "graficos"
    out_dir.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}

    # 1-2: cobertura e acurácia reimport por checkpoint
    p1 = out_dir / "01_cobertura_reimport.csv"
    with p1.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["persona", "checkpoint", "cobertura", "acuracia"])
        for st in states:
            for snap in st.snapshots:
                if snap.reimport:
                    w.writerow([snap.persona, snap.checkpoint, snap.reimport.cobertura, snap.reimport.acuracia_top1])
    paths["cobertura"] = p1

    # 3: correções por checkpoint
    p3 = out_dir / "03_correcoes_por_checkpoint.csv"
    with p3.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["persona", "checkpoint", "aceitas", "corrigidas", "ignoradas"])
        for st in states:
            for snap in st.snapshots:
                w.writerow([
                    snap.persona, snap.checkpoint,
                    snap.feedback_aceitas, snap.feedback_corrigidas, snap.feedback_ignoradas,
                ])
    paths["correcoes"] = p3

    # 4: distribuição fontes (T5)
    p4 = out_dir / "04_distribuicao_fontes_t5.csv"
    with p4.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["persona", "fonte", "tp", "fp"])
        for st in states:
            t5 = next((s for s in st.snapshots if s.checkpoint == "T5"), None)
            if not t5 or not t5.reimport:
                continue
            for fonte, counts in t5.reimport.por_fonte.items():
                w.writerow([st.persona, fonte, counts.get("TP", 0), counts.get("FP", 0)])
    paths["fontes"] = p4

    # 5: merchants aprendidos
    p5 = out_dir / "05_merchants_aprendidos.csv"
    with p5.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["persona", "checkpoint", "memoria_count", "regras_aprendidas"])
        for st in states:
            for snap in st.snapshots:
                w.writerow([snap.persona, snap.checkpoint, snap.memoria_count, snap.regras_aprendidas])
    paths["merchants"] = p5

    # 6: PIX FN rate (R2 recall reimport)
    p6 = out_dir / "06_pix_recall_r2.csv"
    with p6.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["persona", "checkpoint", "recall_r2"])
        for st in states:
            for snap in st.snapshots:
                if snap.reimport:
                    c = snap.reimport.por_bucket.get("R2", {})
                    tp, fn = c.get("TP", 0), c.get("FN", 0)
                    recall = tp / (tp + fn) if (tp + fn) else 0
                    w.writerow([snap.persona, snap.checkpoint, recall])
    paths["pix"] = p6

    # 7: confiança média (prova TP vs FP)
    p7 = out_dir / "07_confianca_media.csv"
    with p7.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["persona", "checkpoint", "conf_tp", "conf_fp"])
        for st in states:
            for snap in st.snapshots:
                if not snap.prova:
                    continue
                tp_c = [r.confianca for r in snap.prova.resultados if r.resultado == "TP" and r.confianca]
                fp_c = [r.confianca for r in snap.prova.resultados if r.resultado == "FP" and r.confianca]
                w.writerow([
                    snap.persona, snap.checkpoint,
                    sum(tp_c) / len(tp_c) if tp_c else 0,
                    sum(fp_c) / len(fp_c) if fp_c else 0,
                ])
    paths["confianca"] = p7

    # 8: ML milestones (extraído de snapshots + ml runs)
    p8 = out_dir / "08_ml_milestones.csv"
    if (LONGITUDINAL_DIR / "registros" / "ml_milestones.csv").exists():
        paths["ml"] = LONGITUDINAL_DIR / "registros" / "ml_milestones.csv"
    else:
        paths["ml"] = p8

    # 9: delta cold vs T5 por bucket
    p9 = out_dir / "09_delta_bucket_t0_t5.csv"
    with p9.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["persona", "bucket", "recall_t0", "recall_t5", "delta"])
        for st in states:
            t0 = next((s for s in st.snapshots if s.checkpoint == "T0"), None)
            t5 = next((s for s in st.snapshots if s.checkpoint == "T5"), None)
            if not t0 or not t5 or not t0.prova or not t5.prova:
                continue
            for bucket in ("M1", "M3", "R2", "C1", "MUT"):
                def recall(snap, b):
                    c = snap.prova.por_bucket.get(b, {})
                    tp, fn = c.get("TP", 0), c.get("FN", 0)
                    return tp / (tp + fn) if (tp + fn) else 0
                r0, r5 = recall(t0, bucket), recall(t5, bucket)
                w.writerow([st.persona, bucket, r0, r5, r5 - r0])
    paths["delta_bucket"] = p9

    # 10: fricção proxy
    p10 = out_dir / "10_friccao_proxy.csv"
    with p10.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["persona", "checkpoint", "tempo_revisao_proxy"])
        for st in states:
            for snap in st.snapshots:
                if snap.reimport:
                    w.writerow([
                        snap.persona, snap.checkpoint,
                        snap.reimport.fp * 8 + snap.reimport.fn * 15,
                    ])
    paths["friccao"] = p10

    return paths
