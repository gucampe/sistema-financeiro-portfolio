"""
Auditoria de performance — medições reais por rota (sem otimizar).

Uso:
  python manage.py audit_performance
  python manage.py audit_performance --email user@example.com
  python manage.py audit_performance --rounds 5
"""

from __future__ import annotations

import gzip
import json
import statistics
import time
from dataclasses import asdict, dataclass

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import connection, reset_queries
from django.test import Client
from django.urls import reverse


@dataclass
class RouteMeasurement:
    name: str
    path: str
    status: int
    rounds: int
    total_ms_p50: float
    total_ms_p95: float
    db_ms_p50: float
    db_queries_p50: int
    html_bytes: int
    gzip_bytes: int
    dom_nodes_est: int
    render_ms_p50: float = 0.0
    minify_ms_p50: float = 0.0
    htmx: bool = False


BENCHMARK_ROUTES = [
    ("ping", "/__benchmark/ping/"),
    ("ping_template", "/__benchmark/ping-template/"),
    ("ping_db", "/__benchmark/ping-db/"),
]

APP_ROUTES = [
    ("login", "usuarios:login", False),
    ("relatorios_home", "relatorios:home", True),
    ("transacoes_historico", "transacoes:historico", True),
    ("relatorios_orcamentos", "relatorios:orcamentos", True),
    ("relatorios_fluxo_caixa", "relatorios:fluxo_caixa", True),
    ("relatorios_por_conta", "relatorios:por_conta", True),
    ("cartoes_home", "cartoes:home", True),
]

DOM_ESTIMATE_TAGS = (
    "<div",
    "<tr",
    "<li",
    "<span",
    "<p",
    "<button",
    "<a ",
    "<td",
    "<th",
)


class Command(BaseCommand):
    help = "Mede tempo, queries e payload por rota (auditoria de performance)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--email",
            default="campelogustavo11@gmail.com",
            help="Usuário para rotas autenticadas",
        )
        parser.add_argument("--rounds", type=int, default=3, help="Repetições por rota")
        parser.add_argument("--json", action="store_true", help="Saída JSON")
        parser.add_argument(
            "--htmx",
            action="store_true",
            help="Mede rotas HTMX (header HX-Request) para orçamentos e histórico",
        )
        parser.add_argument(
            "--output",
            default="",
            help="Salvar JSON em arquivo (ex: docs/performance/baseline.json)",
        )
        parser.add_argument(
            "--host",
            default="testserver",
            help="HTTP_HOST para requests de medição",
        )

    def handle(self, *args, **options):
        if not getattr(settings, "ENABLE_BENCHMARK_ROUTES", False):
            self.stderr.write(
                self.style.WARNING(
                    "ENABLE_BENCHMARK_ROUTES não está ativo; rotas /__benchmark/* não serão medidas."
                )
            )

        email = options["email"]
        rounds = options["rounds"]
        host = options["host"]
        User = get_user_model()

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            self.stderr.write(self.style.ERROR(f"Usuário não encontrado: {email}"))
            return

        client = Client(enforce_csrf_checks=False)
        client.force_login(user)
        anon = Client(enforce_csrf_checks=False)

        results: list[RouteMeasurement] = []
        meta = {
            "debug": settings.DEBUG,
            "session_engine": settings.SESSION_ENGINE,
            "middleware_count": len(settings.MIDDLEWARE),
            "middleware": settings.MIDDLEWARE,
            "minify_html": "django_minify_html" in str(settings.MIDDLEWARE),
            "database": settings.DATABASES["default"].get("HOST", "local"),
            "conn_max_age": settings.DATABASES["default"].get("CONN_MAX_AGE"),
            "user_email": email,
            "user_id": user.pk,
        }

        if settings.ENABLE_BENCHMARK_ROUTES:
            results.append(
                self._measure(
                    anon,
                    "ping_auth",
                    "/__benchmark/ping-auth/",
                    rounds,
                    host,
                    auth_client=client,
                )
            )
            for name, path in BENCHMARK_ROUTES:
                results.append(self._measure(anon, name, path, rounds, host))

        for name, url_name, auth in APP_ROUTES:
            path = reverse(url_name)
            c = client if auth else anon
            results.append(self._measure(c, name, path, rounds, host))

        if options["htmx"]:
            results.append(
                self._measure(
                    client,
                    "orcamentos_htmx",
                    reverse("relatorios:orcamentos"),
                    rounds,
                    host,
                    extra_headers={"HTTP_HX_REQUEST": "true"},
                )
            )
            results.append(
                self._measure(
                    client,
                    "historico_htmx_p2",
                    reverse("transacoes:historico") + "?page=2",
                    rounds,
                    host,
                    extra_headers={"HTTP_HX_REQUEST": "true"},
                )
            )

        payload = {"meta": meta, "routes": [asdict(r) for r in results]}
        if options["json"] or options["output"]:
            text = json.dumps(payload, indent=2)
            if options["output"]:
                with open(options["output"], "w", encoding="utf-8") as f:
                    f.write(text)
                self.stdout.write(self.style.SUCCESS(f"Baseline salvo em {options['output']}"))
            if options["json"]:
                self.stdout.write(text)
        else:
            self._print_report(meta, results)

    def _measure(
        self,
        client: Client,
        name: str,
        path: str,
        rounds: int,
        host: str,
        auth_client: Client | None = None,
        extra_headers: dict | None = None,
    ) -> RouteMeasurement:
        totals: list[float] = []
        db_times: list[float] = []
        query_counts: list[int] = []
        render_times: list[float] = []
        minify_times: list[float] = []
        status = 0
        html_bytes = 0
        gzip_bytes = 0
        dom_nodes = 0
        headers = extra_headers or {}

        measure_client = auth_client or client
        for i in range(rounds):
            reset_queries()
            connection.force_debug_cursor = True
            t0 = time.perf_counter()
            try:
                response = measure_client.get(
                    path,
                    HTTP_HOST=host,
                    secure=True,
                    follow=True,
                    **headers,
                )
            finally:
                connection.force_debug_cursor = False
            total_ms = (time.perf_counter() - t0) * 1000
            db_ms = sum(float(q.get("time", 0)) for q in connection.queries) * 1000
            totals.append(total_ms)
            db_times.append(db_ms)
            query_counts.append(len(connection.queries))
            status = response.status_code

            perf_header = response.get("X-Perf-Timing")
            if perf_header:
                try:
                    perf = json.loads(perf_header)
                    render_times.append(float(perf.get("render_ms", 0)))
                    minify_times.append(float(perf.get("minify_ms", 0)))
                except (json.JSONDecodeError, TypeError, ValueError):
                    pass

            if i == rounds - 1 and hasattr(response, "content"):
                raw = response.content
                html_bytes = len(raw)
                gzip_bytes = len(gzip.compress(raw, compresslevel=6))
                dom_nodes = sum(raw.count(tag.encode()) for tag in DOM_ESTIMATE_TAGS)

        return RouteMeasurement(
            name=name,
            path=path,
            status=status,
            rounds=rounds,
            total_ms_p50=round(statistics.median(totals), 1),
            total_ms_p95=round(sorted(totals)[max(0, int(len(totals) * 0.95) - 1)], 1),
            db_ms_p50=round(statistics.median(db_times), 1),
            db_queries_p50=int(statistics.median(query_counts)),
            html_bytes=html_bytes,
            gzip_bytes=gzip_bytes,
            dom_nodes_est=dom_nodes,
            render_ms_p50=round(statistics.median(render_times), 1) if render_times else 0.0,
            minify_ms_p50=round(statistics.median(minify_times), 1) if minify_times else 0.0,
            htmx=bool(headers.get("HTTP_HX_REQUEST")),
        )

    def _print_report(self, meta: dict, results: list[RouteMeasurement]) -> None:
        self.stdout.write(self.style.MIGRATE_HEADING("\n=== AUDITORIA DE PERFORMANCE ===\n"))
        for k, v in meta.items():
            if k != "middleware":
                self.stdout.write(f"  {k}: {v}")
        self.stdout.write(f"  middleware ({meta['middleware_count']}):")
        for m in meta["middleware"]:
            self.stdout.write(f"    - {m}")

        self.stdout.write(self.style.MIGRATE_HEADING("\n--- Medições por rota ---\n"))
        header = f"{'rota':<22} {'status':>6} {'p50 ms':>8} {'p95 ms':>8} {'db ms':>8} {'queries':>8} {'HTML KB':>8} {'gzip KB':>8} {'DOM~':>6}"
        self.stdout.write(header)
        self.stdout.write("-" * len(header))
        for r in results:
            self.stdout.write(
                f"{r.name:<22} {r.status:>6} {r.total_ms_p50:>8.1f} {r.total_ms_p95:>8.1f} "
                f"{r.db_ms_p50:>8.1f} {r.db_queries_p50:>8} {r.html_bytes/1024:>8.1f} "
                f"{r.gzip_bytes/1024:>8.1f} {r.dom_nodes_est:>6}"
            )
