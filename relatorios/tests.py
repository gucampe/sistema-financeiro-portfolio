from datetime import date

from django.contrib.auth import get_user_model
from django.http import QueryDict
from django.test import TestCase

from relatorios.services.filtros import RelatorioFiltros, parse_relatorio_filtros

User = get_user_model()


class RelatorioFiltrosParseTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="t@t.com", nome="T", password="x")

    def test_preset_este_mes(self):
        q = QueryDict(mutable=True)
        q["preset"] = "este_mes"
        f = parse_relatorio_filtros(q, usuario=self.user)
        self.assertEqual(f.preset, "este_mes")
        self.assertIn(f.data_inicio.month, range(1, 13))

    def test_custom_inicio_fim(self):
        q = QueryDict(mutable=True)
        q["inicio"] = "2026-01-10"
        q["fim"] = "2026-01-20"
        f = parse_relatorio_filtros(q, usuario=self.user)
        self.assertEqual(f.data_inicio, date(2026, 1, 10))
        self.assertEqual(f.data_fim, date(2026, 1, 20))
        self.assertEqual(f.preset, "custom")

    def test_drill_query_string_sem_categoria(self):
        f = RelatorioFiltros(
            data_inicio=date(2026, 4, 1),
            data_fim=date(2026, 4, 30),
            conta_ids=(1, 2),
            categoria_ids=(9,),
            tipos=("despesa",),
            preset="custom",
        )
        s = f.to_drill_transacoes_query_string()
        self.assertIn("inicio=2026-04-01", s)
        self.assertIn("fim=2026-04-30", s)
        self.assertIn("conta=1", s)
        self.assertNotIn("categoria", s)
