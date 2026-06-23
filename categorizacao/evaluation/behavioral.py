from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from categorizacao.evaluation.datasets import AVALIACAO_DIR, GoldenCase, load_golden_csv
from categorizacao.evaluation.runner import BenchmarkSummary, run_benchmark
from categorizacao.models import EventoCategorizacao, RegraCategorizacao


@dataclass
class BehavioralResult:
    persona: str
    descricao: str
    benchmark: BenchmarkSummary
    regras_ativas: int = 0
    eventos_categorizacao: int = 0
    notas: str = ""


def run_all_behavioral_scenarios(
    personas: dict,
    cases: list[GoldenCase] | None = None,
) -> list[BehavioralResult]:
    cases = cases or load_golden_csv()
    specs = {
        "CB-01": "Iniciante — cobertura inicial seed+fuzzy",
        "CB-02": "Histórico parcial (30 tx) — ML limitado",
        "CB-03": "Histórico consolidado (80 tx)",
        "CB-04": "Categorias custom (Comida)",
        "CB-05": "Desorganizado (20 tx)",
        "CB-06": "Avançado — 5 regras + auto-aplicar",
        "CB-07": "Corretor compulsivo — regra aprendida",
        "CB-08": "Ignorador — histórico sem feedback",
    }
    results: list[BehavioralResult] = []
    for code, desc in specs.items():
        user = personas.get(code)
        if not user:
            continue
        bench = run_benchmark(user, cases)
        notas = ""
        if code == "CB-04":
            ifood = next((r for r in bench.resultados if "IFOOD" in r.case.descricao.upper()), None)
            if ifood:
                notas = f"IFOOD → {ifood.sugestao_nome or 'sem sugestão'}"
        if code == "CB-07":
            regras_aprendidas = RegraCategorizacao.objects.filter(
                usuario=user, origem="aprendida"
            ).count()
            notas = f"Regras aprendidas: {regras_aprendidas}"
        results.append(
            BehavioralResult(
                persona=code,
                descricao=desc,
                benchmark=bench,
                regras_ativas=RegraCategorizacao.objects.filter(usuario=user, ativa=True).count(),
                eventos_categorizacao=EventoCategorizacao.objects.filter(usuario=user).count(),
                notas=notas,
            )
        )
    return results


def write_behavioral_csv(results: list[BehavioralResult], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "persona",
                "descricao",
                "regras_ativas",
                "eventos",
                "total",
                "tp",
                "fp",
                "fn",
                "cobertura",
                "acuracia",
                "recall",
                "notas",
            ]
        )
        for r in results:
            s = r.benchmark
            writer.writerow(
                [
                    r.persona,
                    r.descricao,
                    r.regras_ativas,
                    r.eventos_categorizacao,
                    s.total,
                    s.tp,
                    s.fp,
                    s.fn,
                    f"{s.cobertura:.4f}",
                    f"{s.acuracia_top1:.4f}",
                    f"{s.recall:.4f}",
                    r.notas,
                ]
            )


def export_eventos_csv(path: Path) -> int:
    import csv

    from categorizacao.models import EventoCategorizacao

    path.parent.mkdir(parents=True, exist_ok=True)
    qs = EventoCategorizacao.objects.select_related("usuario").order_by("criado_em")
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "id",
                "usuario_email",
                "acao",
                "descricao_original",
                "categoria_sugerida_id",
                "categoria_final_id",
                "fonte",
                "confianca",
                "criado_em",
            ]
        )
        for ev in qs:
            writer.writerow(
                [
                    ev.pk,
                    ev.usuario.email,
                    ev.acao,
                    ev.descricao_original,
                    ev.categoria_sugerida_id,
                    ev.categoria_final_id,
                    ev.fonte,
                    ev.confianca,
                    ev.criado_em.isoformat(),
                ]
            )
    return qs.count()


def write_preview_json(integracao, path: Path) -> None:
    import json

    path.parent.mkdir(parents=True, exist_ok=True)
    payload = []
    for ir in integracao:
        payload.append(
            {
                "superficie": ir.superficie,
                "persona": ir.persona,
                "total_linhas": ir.total_linhas,
                "com_sugestao": ir.com_sugestao,
                "cobertura": ir.cobertura,
                "latencia_ms": ir.latencia_ms,
                "erro": ir.erro,
                "amostra_linhas": [
                    {
                        "descricao": l.descricao,
                        "categoria": l.categoria_sugerida_nome,
                        "confianca": l.confianca,
                        "fonte": l.fonte,
                        "pre_preencher": l.pre_preencher,
                    }
                    for l in ir.linhas[:5]
                ],
            }
        )
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
