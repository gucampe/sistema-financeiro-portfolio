"""
Snapshot financeiro JSON para comparação antes/depois de otimizações.

Uso:
  python manage.py perf_snapshot --email user@example.com
  python manage.py perf_snapshot --email user@example.com --output snapshot.json
"""

from __future__ import annotations

import json
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.urls import reverse
from django.test import Client

from relatorios.services.dashboard_context import snapshot_dashboard_financeiro
from relatorios.services.orcamentos import (
    _filtros_orcamento_despesas,
    filtros_mes,
    listar_orcamentos,
    painel_mes_orcamento,
    referencia_mes_orcamento,
    resumo_linhas_orcamento,
)
from relatorios.services.request_cache import RelatorioRequestCache


class Command(BaseCommand):
    help = "Gera snapshot JSON de agregações financeiras para validação de consistência."

    def add_arguments(self, parser):
        parser.add_argument("--email", required=True, help="E-mail do usuário")
        parser.add_argument("--output", default="", help="Arquivo de saída (stdout se vazio)")

    def handle(self, *args, **options):
        User = get_user_model()
        user = User.objects.get(email=options["email"])
        cache = RelatorioRequestCache(user)

        dashboard = snapshot_dashboard_financeiro(user, cache)

        from datetime import date

        hoje = date.today()
        filtros = _filtros_orcamento_despesas(filtros_mes(hoje.year, hoje.month))
        ano_ref, mes_ref = referencia_mes_orcamento(filtros)
        linhas = listar_orcamentos(
            user,
            filtros,
            ano_ref=ano_ref,
            mes_ref=mes_ref,
            exibir_inativos=True,
        )
        resumo = resumo_linhas_orcamento(linhas)
        painel = painel_mes_orcamento(linhas, resumo)

        client = Client(enforce_csrf_checks=False)
        client.force_login(user)
        hist_resp = client.get(reverse("transacoes:historico"), {"ano": hoje.year, "mes": hoje.month})
        historico = {}
        if hist_resp.status_code == 200:
            ctx = hist_resp.context
            historico = {
                "total_receitas": str(ctx.get("total_receitas", "")),
                "total_despesas": str(ctx.get("total_despesas", "")),
                "saldo_mes": str(ctx.get("saldo_mes", "")),
            }

        payload = {
            "email": options["email"],
            "dashboard": dashboard,
            "orcamentos": {
                "painel_mes": {k: str(v) if isinstance(v, Decimal) else v for k, v in painel.items()},
                "linhas": [
                    {
                        "categoria_id": l.categoria_id,
                        "planejado": str(l.planejado),
                        "realizado": str(l.realizado),
                        "percentual": l.percentual,
                    }
                    for l in linhas
                    if l.planejado > 0
                ],
            },
            "historico": historico,
        }

        text = json.dumps(payload, indent=2, ensure_ascii=False)
        if options["output"]:
            with open(options["output"], "w", encoding="utf-8") as f:
                f.write(text)
            self.stdout.write(self.style.SUCCESS(f"Snapshot salvo em {options['output']}"))
        else:
            self.stdout.write(text)
