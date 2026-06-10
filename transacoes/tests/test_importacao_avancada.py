"""UNIT-IMP-01..16 — importação OFX/XLSX avançada."""

from __future__ import annotations

import json
from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from ofxparse import OfxParserException

from categorias.models import Categoria
from contas.models import Conta
from transacoes.models import Transacao
from transacoes.ofx_duplicatas import (
    chave_fingerprint_linha,
    normalizar_descricao,
)
from transacoes.ofx_parse import LinhaOfx, parse_ofx_bytes
from transacoes.tests.helpers.import_expectativa import (
    expectativa_confirmacao,
    expectativa_duplicatas,
    expectativa_importacao,
    expectativa_parse,
)
from transacoes.tests.helpers.import_fixtures import (
    build_ofx_bytes,
    build_ofx_corrupto,
    build_ofx_dup,
    build_xlsx_bytes,
    build_xlsx_invalid,
    build_xlsx_oversized_bytes,
)
from transacoes.views import _MAX_OFX_BYTES, _MAX_XLSX_BYTES
from transacoes.xlsx_parse import parse_planilha_padrao_bytes

User = get_user_model()

_XLSX_CT = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
_UPLOAD_SETTINGS = {
    "DATA_UPLOAD_MAX_MEMORY_SIZE": 12 * 1024 * 1024,
    "FILE_UPLOAD_MAX_MEMORY_SIZE": 12 * 1024 * 1024,
}


def _xlsx_upload(raw: bytes, name: str = "test.xlsx") -> SimpleUploadedFile:
    return SimpleUploadedFile(name, raw, content_type=_XLSX_CT)


def _ofx_upload(raw: bytes, name: str = "test.ofx") -> SimpleUploadedFile:
    return SimpleUploadedFile(name, raw, content_type="application/x-ofx")


class ImportAvancadaBase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email="imp-adv@test.local", password="x", nome="Imp Adv"
        )
        cls.conta_a = Conta.objects.create(
            usuario=cls.user, nome="Conta A", tipo="corrente", ativa=True
        )
        cls.conta_b = Conta.objects.create(
            usuario=cls.user, nome="Conta B", tipo="poupanca", ativa=True
        )
        cls.cat_d = Categoria.objects.create(
            usuario=cls.user,
            nome="Desp Imp",
            tipo="despesa",
            cor="#EF4444",
            ativa=True,
        )
        cls.cat_r = Categoria.objects.create(
            usuario=cls.user,
            nome="Rec Imp",
            tipo="receita",
            cor="#10B981",
            ativa=True,
        )

    def setUp(self):
        self.client = Client(enforce_csrf_checks=False)


class UnitImpParseLimitesTests(ImportAvancadaBase):
    def test_unit_imp_01_xlsx_2000_linhas(self):
        raw = build_xlsx_bytes(2000)
        linhas = parse_planilha_padrao_bytes(raw)
        parsed = expectativa_parse(linhas)
        self.assertEqual(parsed["total"], 2000)
        self.client.force_login(self.user)
        r = self.client.post(
            reverse("transacoes:importar_planilha_preview"),
            {"conta_id": self.conta_a.pk, "arquivo": _xlsx_upload(raw)},
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.json()["linhas"]), 2000)

    def test_unit_imp_02_xlsx_2001_linhas(self):
        raw = build_xlsx_bytes(2001)
        self.client.force_login(self.user)
        r = self.client.post(
            reverse("transacoes:importar_planilha_preview"),
            {"conta_id": self.conta_a.pk, "arquivo": _xlsx_upload(raw)},
        )
        self.assertEqual(r.status_code, 400)
        self.assertIn("2000", r.json()["message"])

    @override_settings(**_UPLOAD_SETTINGS)
    def test_unit_imp_03_xlsx_oversized(self):
        raw = build_xlsx_oversized_bytes(_MAX_XLSX_BYTES + 1)
        self.assertGreater(len(raw), _MAX_XLSX_BYTES)
        self.client.force_login(self.user)
        r = self.client.post(
            reverse("transacoes:importar_planilha_preview"),
            {"conta_id": self.conta_a.pk, "arquivo": _xlsx_upload(raw, "big.xlsx")},
        )
        self.assertEqual(r.status_code, 400)
        self.assertIn("grande", r.json()["message"])

    def test_unit_imp_04_ofx_corrupto_vazio(self):
        self._assert_ofx_preview_erro(build_ofx_corrupto("vazio"))

    def test_unit_imp_04_ofx_corrupto_lixo(self):
        self._assert_ofx_preview_erro(build_ofx_corrupto("lixo"))

    def test_unit_imp_04_ofx_corrupto_truncado(self):
        self._assert_ofx_preview_erro(build_ofx_corrupto("truncado"))

    def _assert_ofx_preview_erro(self, raw: bytes):
        self.client.force_login(self.user)
        r = self.client.post(
            reverse("transacoes:importar_ofx_preview"),
            {"conta_id": self.conta_a.pk, "arquivo": _ofx_upload(raw)},
        )
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.json()["status"], "error")

    def test_unit_imp_04_ofx_corrupto_parser_raises(self):
        with self.assertRaises((ValueError, OfxParserException)):
            parse_ofx_bytes(build_ofx_corrupto("lixo"))

    @override_settings(**_UPLOAD_SETTINGS)
    def test_unit_imp_05_ofx_oversized(self):
        raw = b"x" * (_MAX_OFX_BYTES + 1)
        self.client.force_login(self.user)
        r = self.client.post(
            reverse("transacoes:importar_ofx_preview"),
            {"conta_id": self.conta_a.pk, "arquivo": _ofx_upload(raw, "big.ofx")},
        )
        self.assertEqual(r.status_code, 400)
        self.assertIn("grande", r.json()["message"])

    def test_unit_imp_06_ofx_zero_transacoes(self):
        raw = build_ofx_corrupto("sem_stmttrn")
        linhas = parse_ofx_bytes(raw)
        self.assertEqual(expectativa_parse(linhas)["total"], 0)


class UnitImpRegraDupTests(ImportAvancadaBase):
    def _tx(self, conta=None, **kwargs):
        defaults = {
            "usuario": self.user,
            "conta": conta or self.conta_a,
            "categoria": self.cat_d,
            "tipo": "despesa",
            "valor": Decimal("42.50"),
            "data": date(2024, 1, 15),
            "descricao": "PADARIA CENTRAL",
            "ofx_fitid": "dup-seed-fitid",
        }
        defaults.update(kwargs)
        return Transacao.objects.create(**defaults)

    def test_unit_imp_07_regra_dup_01_fitid_mesma_chave(self):
        self._tx()
        raw = build_ofx_dup("fitid_igual")
        linhas = parse_ofx_bytes(raw)
        dups = expectativa_duplicatas(self.user, self.conta_a, linhas)
        self.assertTrue(dups[0].duplicata_por_fitid)
        self.assertTrue(dups[0].duplicata_por_heuristica)

    def test_unit_imp_08_regra_dup_01_fitid_chave_diferente(self):
        self._tx()
        raw = build_ofx_dup("fitid_diff_chave")
        linhas = parse_ofx_bytes(raw)
        dups = expectativa_duplicatas(self.user, self.conta_a, linhas)
        self.assertFalse(dups[0].duplicata_por_fitid)

    def test_unit_imp_09_regra_dup_02_heuristica_normalizada(self):
        self._tx(
            ofx_fitid=None,
            descricao="  MERCADO  SAO   JOSE ",
            data=date(2024, 4, 1),
            valor=Decimal("20.00"),
        )
        linhas = parse_ofx_bytes(build_ofx_dup("heuristica_cruzada"))
        dups = expectativa_duplicatas(self.user, self.conta_a, linhas)
        self.assertFalse(dups[0].duplicata_por_fitid)
        self.assertTrue(dups[0].duplicata_por_heuristica)

    def test_unit_imp_10_lote_fitid_conflito_confirmar_sem_fitid(self):
        self.client.force_login(self.user)
        url = reverse("transacoes:importar_ofx_confirmar")
        payload = {
            "conta_id": self.conta_a.pk,
            "linhas": [
                {
                    "indice": 0,
                    "data": "2024-06-10",
                    "valor": "5.00",
                    "tipo": "despesa",
                    "descricao": "Loja",
                    "categoria_id": self.cat_d.id,
                    "ofx_fitid": "same-twice",
                },
                {
                    "indice": 1,
                    "data": "2024-06-10",
                    "valor": "5.00",
                    "tipo": "despesa",
                    "descricao": "LOJA",
                    "categoria_id": self.cat_d.id,
                    "ofx_fitid": "same-twice",
                },
            ],
        }
        r = self.client.post(url, data=json.dumps(payload), content_type="application/json")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["criadas"], 2)
        fitids = list(
            Transacao.objects.filter(conta=self.conta_a, descricao__icontains="oja")
            .values_list("ofx_fitid", flat=True)
        )
        self.assertEqual(sum(1 for f in fitids if f == "same-twice"), 1)


class UnitImpRollbackTests(ImportAvancadaBase):
    def test_unit_imp_11_confirmar_linha_invalida_rollback_total(self):
        antes = Transacao.objects.filter(conta=self.conta_a).count()
        self.client.force_login(self.user)
        payload = {
            "conta_id": self.conta_a.pk,
            "linhas": [
                {
                    "indice": 0,
                    "data": "2024-01-01",
                    "valor": "10.00",
                    "tipo": "despesa",
                    "descricao": "OK",
                    "categoria_id": self.cat_d.id,
                },
                {
                    "indice": 1,
                    "data": "data-invalida",
                    "valor": "20.00",
                    "tipo": "despesa",
                    "descricao": "Ruim",
                    "categoria_id": self.cat_d.id,
                },
            ],
        }
        r = self.client.post(
            reverse("transacoes:importar_ofx_confirmar"),
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 400)
        self.assertEqual(Transacao.objects.filter(conta=self.conta_a).count(), antes)

    def test_unit_imp_12_integrity_error_rollback_total(self):
        self.client.force_login(self.user)
        payload = {
            "conta_id": self.conta_a.pk,
            "linhas": [
                {
                    "indice": 0,
                    "data": "2024-01-01",
                    "valor": "10.00",
                    "tipo": "despesa",
                    "descricao": "OK",
                    "categoria_id": self.cat_d.id,
                    "ofx_fitid": "fit-x",
                },
            ],
        }
        antes = Transacao.objects.filter(conta=self.conta_a).count()
        with patch(
            "transacoes.views.Transacao.objects.bulk_create",
            side_effect=IntegrityError("dup"),
        ):
            r = self.client.post(
                reverse("transacoes:importar_ofx_confirmar"),
                data=json.dumps(payload),
                content_type="application/json",
            )
        self.assertEqual(r.status_code, 400)
        self.assertEqual(Transacao.objects.filter(conta=self.conta_a).count(), antes)


class UnitImpEncodingTests(ImportAvancadaBase):
    def test_unit_imp_13_fingerprint_normalizacao_interna(self):
        """REGRA-ENC: chave usa normalizar_descricao, não bytes do parser."""
        d = date(2024, 5, 1)
        v = Decimal("12.00")
        k_espacos = chave_fingerprint_linha(d, v, "  Mercado  SAO   JOSE ")
        k_compacto = chave_fingerprint_linha(d, v, "mercado sao jose")
        self.assertEqual(k_espacos[2], k_compacto[2])
        self.assertEqual(k_espacos[2], normalizar_descricao("Mercado Sao Jose"))

    def test_unit_imp_14_normalizar_descricao_case_espacos(self):
        self.assertEqual(
            normalizar_descricao("  PADARIA   Central  "),
            normalizar_descricao("padaria central"),
        )
        linha_a = LinhaOfx(
            date(2024, 5, 2), Decimal("8.00"), "despesa", "  PADARIA   Central  ", None
        )
        linha_b = LinhaOfx(
            date(2024, 5, 2), Decimal("8.00"), "despesa", "padaria central", None
        )
        dups = expectativa_duplicatas(
            self.user,
            self.conta_a,
            [linha_a, linha_b],
        )
        self.assertFalse(dups[0].duplicata_por_heuristica)
        self.assertTrue(dups[1].duplicata_por_heuristica)


class UnitImpContasIncrementalTests(ImportAvancadaBase):
    def test_unit_imp_15_dup_isolada_por_conta(self):
        Transacao.objects.create(
            usuario=self.user,
            conta=self.conta_b,
            categoria=self.cat_d,
            tipo="despesa",
            valor=Decimal("7.00"),
            data=date(2024, 8, 1),
            descricao="Unico",
            ofx_fitid="fit-outra",
        )
        linhas = parse_ofx_bytes(
            build_ofx_bytes(
                [
                    {
                        "fitid": "fit-outra",
                        "trnamt": "-7.00",
                        "name": "Unico",
                        "dtposted": "20240801120000",
                    }
                ]
            )
        )
        dups_a = expectativa_duplicatas(self.user, self.conta_a, linhas)
        dups_b = expectativa_duplicatas(self.user, self.conta_b, linhas)
        self.assertFalse(dups_a[0].duplicata_por_fitid)
        self.assertTrue(dups_b[0].duplicata_por_fitid)

    def test_unit_imp_16_regra_inc_reimport(self):
        linhas = [
            LinhaOfx(date(2024, 9, 1), Decimal("11.00"), "despesa", "Inc A", "inc-1"),
            LinhaOfx(date(2024, 9, 2), Decimal("22.00"), "despesa", "Inc B", "inc-2"),
        ]
        self.client.force_login(self.user)
        payload = {
            "conta_id": self.conta_a.pk,
            "linhas": [
                {
                    "indice": i,
                    "data": ln.data.isoformat(),
                    "valor": str(ln.valor),
                    "tipo": ln.tipo,
                    "descricao": ln.descricao,
                    "categoria_id": self.cat_d.id,
                    "ofx_fitid": ln.ofx_fitid,
                }
                for i, ln in enumerate(linhas)
            ],
        }
        r = self.client.post(
            reverse("transacoes:importar_ofx_confirmar"),
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(r.json()["criadas"], 2)

        dups = expectativa_duplicatas(self.user, self.conta_a, linhas)
        self.assertTrue(all(d.duplicata_por_heuristica for d in dups))
        criadas_novas = expectativa_confirmacao(linhas, dups, indices_selecionados=set())
        self.assertEqual(criadas_novas, 0)
        exp = expectativa_importacao(self.user, self.conta_a, linhas)
        self.assertEqual(exp["criadas_se_confirmar_padrao_ui"], 0)
