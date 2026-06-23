from __future__ import annotations

from datetime import date
from pathlib import Path

from django.core.management import call_command
from django.core.management.base import BaseCommand

from categorizacao.evaluation.behavioral import (
    export_eventos_csv,
    run_all_behavioral_scenarios,
    write_behavioral_csv,
    write_preview_json,
)
from categorizacao.evaluation.datasets import AVALIACAO_DIR, load_golden_csv, write_golden_csv
from categorizacao.evaluation.integration import (
    generate_ofx_fixtures,
    generate_xlsx_fixtures,
    run_ofx_preview,
    run_sugerir_api,
    run_xlsx_preview,
)
from categorizacao.evaluation.personas import ensure_personas, simular_aprendizado_cb07
from categorizacao.evaluation.ux import run_proxy_ux_assessment, write_ux_registro
from categorizacao.evaluation.report import gerar_relatorio, git_commit_curto
from categorizacao.evaluation.runner import (
    run_ablation,
    run_benchmark,
    write_metricas_consolidadas,
    write_resultados_csv,
)
from contas.models import Conta


class Command(BaseCommand):
    help = "Executa avaliação completa da categorização automática e gera relatório"

    def add_arguments(self, parser):
        parser.add_argument(
            "--skip-seed",
            action="store_true",
            help="Não executa seed_merchants_globais",
        )

    def handle(self, *args, **options):
        registros = AVALIACAO_DIR / "registros"
        registros.mkdir(parents=True, exist_ok=True)

        self.stdout.write("Gerando golden CSV...")
        write_golden_csv()
        cases = load_golden_csv()

        if not options["skip_seed"]:
            self.stdout.write("Seed merchants globais...")
            call_command("seed_merchants_globais")

        self.stdout.write("Gerando fixtures OFX/XLSX...")
        ofx_dir = AVALIACAO_DIR / "datasets" / "ofx"
        xlsx_dir = AVALIACAO_DIR / "datasets" / "xlsx"
        ofx_paths = generate_ofx_fixtures(ofx_dir)
        xlsx_paths = generate_xlsx_fixtures(xlsx_dir)

        self.stdout.write("Provisionando personas CB-01..CB-08...")
        personas = ensure_personas()
        cb01 = personas["CB-01"]
        cb03 = personas["CB-03"]
        cb06 = personas["CB-06"]

        conta_cb01 = Conta.objects.get(usuario=cb01, nome="Conta Avaliacao")
        conta_cb03 = Conta.objects.get(usuario=cb03, nome="Conta Avaliacao")
        conta_cb06 = Conta.objects.get(usuario=cb06, nome="Conta Avaliacao")

        simular_aprendizado_cb07(personas["CB-07"], Conta.objects.get(usuario=personas["CB-07"]))

        self.stdout.write("Benchmark golden offline...")
        bench_cb01 = run_benchmark(cb01, cases)
        bench_cb03 = run_benchmark(cb03, cases)
        bench_cb06 = run_benchmark(cb06, cases)
        write_resultados_csv(bench_cb01, registros / "resultados_golden_cb01.csv")

        self.stdout.write("Ablation (60 casos)...")
        ablation = run_ablation(cb01, cases, max_cases=60)

        self.stdout.write("Integração preview OFX/XLSX...")
        integracao = [
            run_ofx_preview(cb01, conta_cb01.pk, ofx_paths["ofx_30_merchants.ofx"], "CB-01"),
            run_ofx_preview(cb03, conta_cb03.pk, ofx_paths["ofx_30_merchants.ofx"], "CB-03"),
            run_ofx_preview(cb06, conta_cb06.pk, ofx_paths["ofx_30_merchants.ofx"], "CB-06"),
            run_ofx_preview(cb01, conta_cb01.pk, ofx_paths["ofx_50_ruidoso.ofx"], "CB-01-ruidoso"),
            run_ofx_preview(cb01, conta_cb01.pk, ofx_paths["ofx_20_ambiguos.ofx"], "CB-01-ambiguos"),
            run_xlsx_preview(cb01, conta_cb01.pk, xlsx_paths["xlsx_30_merchants.xlsx"], "CB-01"),
        ]
        carga = run_ofx_preview(cb01, conta_cb01.pk, ofx_paths["ofx_200_linhas.ofx"], "CB-01-carga")
        integracao.append(carga)

        # API manual sample
        api_samples = [
            ("IFOOD RESTAURANTE", "despesa"),
            ("PIX MARIA SILVA", "despesa"),
            ("PADARIA CENTRAL", "despesa"),
        ]
        api_path = registros / "api_sugerir_amostras.json"
        import json
        api_path.write_text(
            json.dumps(
                {d: run_sugerir_api(cb01, d, t) for d, t in api_samples},
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        hoje = date.today().strftime("%Y%m%d")

        summaries = {
            "golden_cb01": bench_cb01,
            "golden_cb03": bench_cb03,
            "golden_cb06": bench_cb06,
        }
        for nome, s in ablation.items():
            summaries[f"ablation_{nome}"] = s

        write_preview_json(integracao, registros / "preview_integracao.json")

        self.stdout.write("Cenários comportamentais CB-01..CB-08...")
        behavioral = run_all_behavioral_scenarios(personas, cases)
        write_behavioral_csv(behavioral, registros / "cenarios_comportamentais.csv")
        n_eventos = export_eventos_csv(registros / "eventos_categorizacao.csv")
        self.stdout.write(f"  EventosCategorizacao exportados: {n_eventos}")
        for br in behavioral:
            summaries[f"golden_{br.persona.lower()}"] = br.benchmark

        self.stdout.write("UX proxy (métricas derivadas)...")
        ux_scores = run_proxy_ux_assessment(benchmark_cb01=bench_cb01, integracao=integracao)
        ux_path = write_ux_registro(ux_scores, registros / f"sessao_UX_{hoje}.md")

        write_metricas_consolidadas(summaries, registros / "metricas_consolidadas.csv")

        relatorio_path = AVALIACAO_DIR / f"RELATORIO_CATEGORIZACAO_{hoje}.md"
        gerar_relatorio(
            benchmark_cb01=bench_cb01,
            benchmark_cb03=bench_cb03,
            benchmark_cb06=bench_cb06,
            ablation=ablation,
            integracao=integracao,
            behavioral=behavioral,
            ux_scores=ux_scores,
            commit=git_commit_curto(),
            output_path=relatorio_path,
        )
        template_preenchido = AVALIACAO_DIR / "RELATORIO_CATEGORIZACAO.md"
        template_preenchido.write_text(relatorio_path.read_text(encoding="utf-8"), encoding="utf-8")
        template_oficial = AVALIACAO_DIR / "TEMPLATE_RELATORIO_CATEGORIZACAO.md"
        template_oficial.write_text(relatorio_path.read_text(encoding="utf-8"), encoding="utf-8")

        self.stdout.write(self.style.SUCCESS(f"Avaliação concluída."))
        self.stdout.write(f"  Golden CB-01: cobertura={bench_cb01.cobertura:.1%} acurácia={bench_cb01.acuracia_top1:.1%}")
        self.stdout.write(f"  UX proxy: {ux_path}")
        self.stdout.write(f"  Relatório preenchido: {template_preenchido}")
        self.stdout.write(f"  Métricas: {registros / 'metricas_consolidadas.csv'}")
