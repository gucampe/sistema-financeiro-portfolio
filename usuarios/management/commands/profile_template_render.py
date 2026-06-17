"""
Medição isolada de renderização de templates (sem DB no loop).

Uso:
  python manage.py profile_template_render --rounds 20
"""

from __future__ import annotations

import statistics
import time

from django.core.management.base import BaseCommand
from django.template.loader import render_to_string

TEMPLATES = [
    ("relatorios/partials/home.html", "dashboard_minimal"),
    ("transacoes/partials/historico_linhas.html", "historico_linhas_minimal"),
    ("relatorios/partials/orcamentos_linhas_content.html", "orcamentos_linhas_minimal"),
]

MINIMAL_CONTEXT = {
    "dashboard_minimal": {
        "relatorio_nav": "home",
        "saudacao": "Bom dia",
        "nome_usuario": "Teste",
        "rotulo_periodo": "Resumo",
        "totais_mes": {"receitas": 0, "despesas": 0},
        "resultado_mes": 0,
        "patrimonio": {"contas": [], "patrimonio_total": 0, "total_contas": 0, "tem_mais": False},
        "cartoes_dashboard": {"cartoes": [], "total_faturas": 0, "quantidade": 0},
        "metas_financeiras": [],
        "tem_orcamentos_cadastrados": False,
        "tem_orcamentos_vigentes": False,
        "top_despesas_mes": [],
        "top_despesas_chart": [],
        "ocultar_valores_dashboard": False,
        "primeiros_passos": {"percentual": 0, "etapas": []},
        "filtros": None,
        "filtros_ativos_count": 0,
        "contas_ativas": [],
        "categorias_filtro": [],
    },
    "historico_linhas_minimal": {
        "transacoes_por_dia": [],
        "page": 1,
        "total_pages": 1,
        "ano": 2026,
        "mes": 6,
        "filtros_query_extra": "",
        "icon_fallback_url": "/static/contas/icons/genericos/bank.svg",
    },
    "orcamentos_linhas_minimal": {
        "linhas_orcamento": [],
        "periodo_orcamento_rotulo": "Junho de 2026",
        "drill_mes_qs": "",
    },
}


class Command(BaseCommand):
    help = "Mede render_ms puro de templates com contexto mínimo."

    def add_arguments(self, parser):
        parser.add_argument("--rounds", type=int, default=10)

    def handle(self, *args, **options):
        rounds = options["rounds"]
        self.stdout.write(self.style.MIGRATE_HEADING("\n=== PROFILE TEMPLATE RENDER ===\n"))
        for template, ctx_key in TEMPLATES:
            ctx = MINIMAL_CONTEXT[ctx_key]
            timings: list[float] = []
            for _ in range(rounds):
                t0 = time.perf_counter()
                render_to_string(template, ctx)
                timings.append((time.perf_counter() - t0) * 1000)
            self.stdout.write(
                f"{template:<50} p50={statistics.median(timings):.2f}ms "
                f"p95={sorted(timings)[max(0, int(len(timings)*0.95)-1)]:.2f}ms"
            )
