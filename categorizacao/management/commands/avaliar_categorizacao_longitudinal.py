from __future__ import annotations

from datetime import date

from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.test.utils import override_settings

from categorizacao.evaluation.longitudinal.ledger import write_all_datasets
from categorizacao.evaluation.longitudinal.metrics_ts import (
    write_charts_data,
    write_metricas_longitudinais,
)
from categorizacao.evaluation.longitudinal.ml_milestones import (
    ML_PERSONAS,
    run_ml_milestones,
    write_ml_milestones_csv,
)
from categorizacao.evaluation.longitudinal.personas_lx import PERSONAS_LX, ensure_personas_lx
from categorizacao.evaluation.longitudinal.replay import ReplayConfig, run_all_replays
from categorizacao.evaluation.longitudinal.report_longitudinal import (
    gerar_relatorio_longitudinal,
    git_commit_curto,
)
from categorizacao.evaluation.longitudinal.constants import LONGITUDINAL_DIR
from categorizacao.evaluation.longitudinal.ux_longitudinal import (
    run_ux_longitudinal_proxy,
    write_ux_registro,
)


class Command(BaseCommand):
    help = "Avaliação longitudinal da categorização (simulação temporal 12 semanas)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--personas",
            type=str,
            default="",
            help="Lista separada por vírgula (ex: LX-02,LX-07). Vazio = todas.",
        )
        parser.add_argument(
            "--checkpoints",
            type=str,
            default="T0,T1,T2,T3,T4,T5",
            help="Checkpoints de benchmark",
        )
        parser.add_argument("--weeks", type=int, default=12, help="Semanas simuladas")
        parser.add_argument("--skip-seed", action="store_true")
        parser.add_argument(
            "--skip-ml-milestones",
            action="store_true",
            help="Não executa benchmarks ML M-30..500",
        )
        parser.add_argument(
            "--quick",
            action="store_true",
            help="Personas reduzidas: LX-01,LX-02,LX-07,LX-09 + controles",
        )
        parser.add_argument(
            "--with-llm",
            action="store_true",
            help="Habilita fallback LLM (mock) durante replay e checkpoints",
        )

    def handle(self, *args, **options):
        if options["quick"]:
            codes = ["LX-01", "LX-02", "LX-07", "LX-09", "LX-CTRL-0", "LX-CTRL-CORR"]
        elif options["personas"]:
            codes = [c.strip() for c in options["personas"].split(",") if c.strip()]
        else:
            codes = [p.code for p in PERSONAS_LX]

        checkpoints = tuple(c.strip() for c in options["checkpoints"].split(",") if c.strip())
        weeks = options["weeks"]

        self.stdout.write("Gerando datasets longitudinais...")
        write_all_datasets(weeks=weeks)

        if not options["skip_seed"]:
            self.stdout.write("Seed merchants globais...")
            call_command("seed_merchants_globais")

        self.stdout.write(f"Provisionando personas: {', '.join(codes)}")
        users = ensure_personas_lx(codes)

        config = ReplayConfig(weeks=weeks, checkpoints=checkpoints)
        self.stdout.write(f"Replay temporal ({weeks} semanas)...")
        llm_settings = {}
        if options["with_llm"]:
            llm_settings = {
                "ENABLE_CATEGORIZACAO_LLM": True,
                "CATEGORIZACAO_LLM_USE_MOCK": True,
                "CATEGORIZACAO_LLM_MODEL": "mock-llm",
            }
            self.stdout.write("  LLM habilitado (mock) — controle admin simulado via settings")

        if llm_settings:
            with override_settings(**llm_settings):
                states = run_all_replays(users, config)
        else:
            states = run_all_replays(users, config)

        self.stdout.write("Exportando métricas temporais...")
        metricas_path = write_metricas_longitudinais(states)
        charts = write_charts_data(states)

        ml_results: list[dict] = []
        if not options["skip_ml_milestones"]:
            ml_codes = [c for c in ML_PERSONAS if c in users]
            self.stdout.write(f"ML milestones: {', '.join(ml_codes)}")
            ml_results = run_ml_milestones(users, ml_codes)
            write_ml_milestones_csv(ml_results)
            write_charts_data(states)

        self.stdout.write("UX longitudinal (proxy)...")
        ux_scores = run_ux_longitudinal_proxy(states)
        ux_path = write_ux_registro(ux_scores)

        hoje = date.today().strftime("%Y%m%d")
        relatorio_path = LONGITUDINAL_DIR / f"RELATORIO_LONGITUDINAL_{hoje}.md"
        gerar_relatorio_longitudinal(
            states=states,
            ux_scores=ux_scores,
            ml_summary=ml_results,
            commit=git_commit_curto(),
            output_path=relatorio_path,
        )
        template_path = LONGITUDINAL_DIR / "TEMPLATE_RELATORIO_LONGITUDINAL.md"
        template_path.write_text(relatorio_path.read_text(encoding="utf-8"), encoding="utf-8")
        canonical = LONGITUDINAL_DIR / "RELATORIO_LONGITUDINAL.md"
        canonical.write_text(relatorio_path.read_text(encoding="utf-8"), encoding="utf-8")

        self.stdout.write(self.style.SUCCESS("Avaliação longitudinal concluída."))
        self.stdout.write(f"  Personas: {len(states)}")
        self.stdout.write(f"  Métricas: {metricas_path}")
        self.stdout.write(f"  Gráficos: {charts.get('cobertura', '—')}")
        self.stdout.write(f"  UX: {ux_path}")
        self.stdout.write(f"  Relatório: {relatorio_path}")
