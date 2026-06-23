from __future__ import annotations

from datetime import date

from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.test.utils import override_settings

from categorizacao.evaluation.llm.datasets_llm import LLM_DIR, load_llm_focus_cases, write_llm_datasets
from categorizacao.evaluation.llm.report_llm import gerar_relatorio_llm, git_commit_curto, write_comparativo_csv
from categorizacao.evaluation.llm.runner_llm import (
    compare_hybrid_vs_llm,
    run_hybrid_benchmark,
    run_llm_benchmark,
)
from categorizacao.evaluation.personas import ensure_personas
from categorizacao.services.llm.providers.registry import MODEL_REGISTRY


class Command(BaseCommand):
    help = "Avaliação A/B do fallback LLM (Gemini) — datasets M3/R2/C1/R1/inéditos"

    def add_arguments(self, parser):
        parser.add_argument("--skip-seed", action="store_true")
        parser.add_argument(
            "--persona",
            type=str,
            default="CB-01",
            help="Persona de avaliação (default CB-01)",
        )
        parser.add_argument(
            "--compare-models",
            action="store_true",
            help="Compara modelos registrados (mock por padrão no CI)",
        )
        parser.add_argument(
            "--models",
            type=str,
            default="",
            help="Lista de modelos separada por vírgula (default: mock-llm, gemini-2.0-flash, gemini-2.0-flash-lite)",
        )

    def handle(self, *args, **options):
        registros = LLM_DIR / "registros"
        registros.mkdir(parents=True, exist_ok=True)

        self.stdout.write("Gerando datasets LLM (M3/R2/C1/R1/inéditos)...")
        write_llm_datasets()
        cases = load_llm_focus_cases()
        self.stdout.write(f"  {len(cases)} casos no lote foco LLM")

        if not options["skip_seed"]:
            self.stdout.write("Seed merchants globais...")
            call_command("seed_merchants_globais")

        personas = ensure_personas()
        usuario = personas[options["persona"]]

        self.stdout.write("Benchmark híbrido (sem LLM)...")
        with override_settings(ENABLE_CATEGORIZACAO_LLM=False):
            hibrido = run_hybrid_benchmark(usuario, cases, variant="hibrido")

        modelos_resultados: dict[str, object] = {}
        if options["compare_models"]:
            model_ids = [
                m.strip()
                for m in (
                    options["models"]
                    or "mock-llm,gemini-2.5-flash-lite,gemini-2.5-flash,gemini-1.5-pro"
                ).split(",")
                if m.strip()
            ]
            for model_id in model_ids:
                if model_id not in MODEL_REGISTRY and model_id != "mock-llm":
                    self.stdout.write(self.style.WARNING(f"  Modelo desconhecido ignorado: {model_id}"))
                    continue
                use_mock = model_id == "mock-llm"
                self.stdout.write(f"Benchmark LLM modelo={model_id} (mock={use_mock})...")
                with override_settings(
                    ENABLE_CATEGORIZACAO_LLM=True,
                    CATEGORIZACAO_LLM_USE_MOCK=use_mock,
                    CATEGORIZACAO_LLM_MODEL=model_id,
                ):
                    modelos_resultados[model_id] = run_llm_benchmark(usuario, cases, variant=model_id)
            llm = modelos_resultados.get("mock-llm") or next(iter(modelos_resultados.values()))
        else:
            self.stdout.write("Benchmark com LLM (mock provider)...")
            with override_settings(
                ENABLE_CATEGORIZACAO_LLM=True,
                CATEGORIZACAO_LLM_USE_MOCK=True,
                CATEGORIZACAO_LLM_MODEL="mock-llm",
            ):
                llm = run_llm_benchmark(usuario, cases, variant="mock-llm")

        with override_settings(
            ENABLE_CATEGORIZACAO_LLM=True,
            CATEGORIZACAO_LLM_USE_MOCK=True,
            CATEGORIZACAO_LLM_MODEL="mock-llm",
        ):
            comparacoes = compare_hybrid_vs_llm(usuario, cases)

        write_comparativo_csv(comparacoes, registros / "comparativo_hibrido_vs_llm.csv")

        hoje = date.today().strftime("%Y%m%d")
        relatorio_path = LLM_DIR / f"RELATORIO_LLM_{hoje}.md"
        gerar_relatorio_llm(
            hibrido=hibrido,
            llm=llm,
            comparacoes=comparacoes,
            modelos=modelos_resultados or None,
            commit=git_commit_curto(),
            output_path=relatorio_path,
        )

        self.stdout.write(self.style.SUCCESS("Avaliação LLM concluída."))
        self.stdout.write(
            f"  Híbrido: cobertura={hibrido.cobertura:.1%} recall={hibrido.recall:.1%}"
        )
        self.stdout.write(
            f"  Com LLM: cobertura={llm.cobertura:.1%} recall={llm.recall:.1%} "
            f"invocações={llm.llm_invocations}"
        )
        if modelos_resultados:
            self.stdout.write(f"  Modelos comparados: {', '.join(modelos_resultados.keys())}")
        self.stdout.write(f"  Relatório: {relatorio_path}")
        self.stdout.write(f"  Comparativo: {LLM_DIR / 'COMPARATIVO_MODELOS_GEMINI.md'}")
