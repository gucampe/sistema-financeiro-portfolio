"""
Import Ledger Golden Test — validação de ponta a ponta do pipeline de importação.

Cenário fixo (estado final determinístico):
- 2 transações pré-existentes em conta_a (alvo FITID + heurística)
- OFX com 3 novas + 2 duplicatas contra o seed
- XLSX com 1 nova
- 1 confirmação inválida rejeitada (rollback total)
- re-upload OFX/XLSX (idempotência — 0 novas transações)
- isolamento conta_b (mesmos arquivos, sem seed)

Valida apenas estado do banco (não UI/HTML/JS).
"""

from __future__ import annotations

import json
from datetime import date
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.urls import reverse

from categorias.models import Categoria
from contas.models import Conta
from financial_contracts.saldo_contracts import assert_saldo_conta, calcular_saldo_esperado
from transacoes.models import Transacao
from transacoes.ofx_duplicatas import chave_fingerprint_linha
from transacoes.ofx_parse import parse_ofx_bytes
from transacoes.tests.helpers.import_expectativa import expectativa_importacao
from transacoes.tests.helpers.import_fixtures import (
    build_ofx_bytes,
    build_xlsx_bytes,
    build_xlsx_invalid,
)
from transacoes.xlsx_parse import parse_planilha_padrao_bytes

User = get_user_model()

_XLSX_CT = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

# --- Cenário canônico (fonte única de expectativa) ---

GOLDEN_FITID_SEED = "golden-fit-seed"
GOLDEN_OFX_TXS = [
    {
        "fitid": "golden-new-1",
        "trnamt": "-15.00",
        "name": "Loja Nova 1",
        "dtposted": "20240701120000",
    },
    {
        "fitid": "golden-new-2",
        "trnamt": "-25.00",
        "name": "Loja Nova 2",
        "dtposted": "20240702120000",
    },
    {
        "fitid": "golden-new-3",
        "trnamt": "100.00",
        "name": "Receita Nova",
        "dtposted": "20240703120000",
    },
    {
        "fitid": GOLDEN_FITID_SEED,
        "trnamt": "-42.50",
        "name": "PADARIA CENTRAL",
        "dtposted": "20240115120000",
    },
    {
        "fitid": "golden-heur-file",
        "trnamt": "-20.00",
        "name": "mercado sao jose",
        "dtposted": "20240401120000",
    },
]

GOLDEN_XLSX_DATA = date(2024, 8, 1)
GOLDEN_XLSX_DESC = "Golden XLSX"
GOLDEN_XLSX_VALOR = Decimal("30.00")

EXPECTED_TOTAL_CONTA_A = 6
EXPECTED_TOTAL_CONTA_B = 6
EXPECTED_NOVAS_OFX_PRIMEIRA = 3
EXPECTED_NOVAS_XLSX = 1


def _xlsx_upload(raw: bytes, name: str = "golden.xlsx") -> SimpleUploadedFile:
    return SimpleUploadedFile(name, raw, content_type=_XLSX_CT)


def _ofx_upload(raw: bytes, name: str = "golden.ofx") -> SimpleUploadedFile:
    return SimpleUploadedFile(name, raw, content_type="application/x-ofx")


def _linhas_confirmar_padrao_ui(
    preview: dict,
    *,
    categoria_despesa_id: int,
    categoria_receita_id: int,
) -> list[dict]:
    """REGRA-DUP-03: simula checkbox desmarcado para duplicatas."""
    linhas = []
    for row in preview["linhas"]:
        if row.get("duplicata_por_fitid") or row.get("duplicata_por_heuristica"):
            continue
        tipo = row["tipo"]
        if tipo == "receita":
            cat_id = categoria_receita_id
        elif tipo == "ajuste":
            cat_id = categoria_receita_id
        else:
            cat_id = categoria_despesa_id
        item = {
            "indice": row["indice"],
            "data": row["data"],
            "valor": row["valor"],
            "tipo": tipo,
            "descricao": row["descricao"],
            "categoria_id": cat_id,
        }
        if row.get("ofx_fitid"):
            item["ofx_fitid"] = row["ofx_fitid"]
        linhas.append(item)
    return linhas


def _ledger_snapshot(conta: Conta) -> list[dict]:
    return list(
        Transacao.objects.filter(conta=conta)
        .order_by("data", "pk")
        .values("data", "valor", "tipo", "descricao", "ofx_fitid")
    )


def _assert_sem_duplicatas_logicas(conta: Conta, usuario) -> None:
    txs = Transacao.objects.filter(conta=conta, usuario=usuario)
    fitids = [
        f
        for f in txs.exclude(ofx_fitid__isnull=True)
        .exclude(ofx_fitid="")
        .values_list("ofx_fitid", flat=True)
    ]
    assert len(fitids) == len(set(fitids)), "FITID duplicado na mesma conta"

    chaves: set[tuple] = set()
    for t in txs:
        chave = chave_fingerprint_linha(t.data, t.valor, t.descricao)
        assert chave not in chaves, f"Fingerprint heurístico duplicado: {chave}"
        chaves.add(chave)


@pytest.mark.importacao_avancada
class ImportLedgerGoldenTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email="ledger-golden@test.local", password="x", nome="Ledger Golden"
        )
        cls.conta_a = Conta.objects.create(
            usuario=cls.user, nome="Conta Golden A", tipo="corrente", ativa=True
        )
        cls.conta_b = Conta.objects.create(
            usuario=cls.user, nome="Conta Golden B", tipo="poupanca", ativa=True
        )
        cls.cat_d = Categoria.objects.create(
            usuario=cls.user,
            nome="Desp Golden",
            tipo="despesa",
            cor="#EF4444",
            ativa=True,
        )
        cls.cat_r = Categoria.objects.create(
            usuario=cls.user,
            nome="Rec Golden",
            tipo="receita",
            cor="#10B981",
            ativa=True,
        )

    def setUp(self):
        self.client = Client(enforce_csrf_checks=False)
        self.url_ofx_preview = reverse("transacoes:importar_ofx_preview")
        self.url_xlsx_preview = reverse("transacoes:importar_planilha_preview")
        self.url_confirmar = reverse("transacoes:importar_ofx_confirmar")
        self.raw_ofx = build_ofx_bytes(GOLDEN_OFX_TXS)
        self.raw_xlsx = build_xlsx_bytes(
            1,
            data_inicio=GOLDEN_XLSX_DATA,
            descricao=GOLDEN_XLSX_DESC,
            valor=float(GOLDEN_XLSX_VALOR),
            valor_por_linha=False,
        )

    def _seed_conta_a(self) -> None:
        Transacao.objects.create(
            usuario=self.user,
            conta=self.conta_a,
            categoria=self.cat_d,
            tipo="despesa",
            valor=Decimal("42.50"),
            data=date(2024, 1, 15),
            descricao="PADARIA CENTRAL",
            ofx_fitid=GOLDEN_FITID_SEED,
        )
        Transacao.objects.create(
            usuario=self.user,
            conta=self.conta_a,
            categoria=self.cat_d,
            tipo="despesa",
            valor=Decimal("20.00"),
            data=date(2024, 4, 1),
            descricao="mercado sao jose",
            ofx_fitid=None,
        )

    def _preview_ofx(self, conta: Conta, raw: bytes | None = None) -> dict:
        r = self.client.post(
            self.url_ofx_preview,
            {"conta_id": conta.pk, "arquivo": _ofx_upload(raw or self.raw_ofx)},
        )
        self.assertEqual(r.status_code, 200, r.content)
        data = r.json()
        self.assertEqual(data["status"], "ok")
        return data

    def _preview_xlsx(self, conta: Conta, raw: bytes | None = None) -> dict:
        r = self.client.post(
            self.url_xlsx_preview,
            {"conta_id": conta.pk, "arquivo": _xlsx_upload(raw or self.raw_xlsx)},
        )
        self.assertEqual(r.status_code, 200, r.content)
        data = r.json()
        self.assertEqual(data["status"], "ok")
        return data

    def _confirmar(self, conta: Conta, linhas: list[dict]) -> dict:
        r = self.client.post(
            self.url_confirmar,
            data=json.dumps({"conta_id": conta.pk, "linhas": linhas}),
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 200, r.content)
        return r.json()

    def _confirmar_rejeita(self, conta: Conta, linhas: list[dict]) -> None:
        antes = Transacao.objects.filter(conta=conta).count()
        r = self.client.post(
            self.url_confirmar,
            data=json.dumps({"conta_id": conta.pk, "linhas": linhas}),
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 400, r.content)
        self.assertEqual(Transacao.objects.filter(conta=conta).count(), antes)

    def test_import_ledger_golden(self):
        """
        Pipeline completo: parse → duplicatas → preview → confirmação → saldo → re-upload.
        """
        self.client.force_login(self.user)
        self._seed_conta_a()

        linhas_ofx = parse_ofx_bytes(self.raw_ofx)
        linhas_xlsx = parse_planilha_padrao_bytes(self.raw_xlsx)

        # --- Oracle modular (antes da confirmação) ---
        exp_ofx = expectativa_importacao(self.user, self.conta_a, linhas_ofx)
        self.assertEqual(exp_ofx["total"], 5)
        self.assertEqual(
            exp_ofx["criadas_se_confirmar_padrao_ui"], EXPECTED_NOVAS_OFX_PRIMEIRA
        )

        exp_xlsx = expectativa_importacao(self.user, self.conta_a, linhas_xlsx)
        self.assertEqual(exp_xlsx["criadas_se_confirmar_padrao_ui"], EXPECTED_NOVAS_XLSX)

        # --- 1ª importação OFX (preview → confirmar) ---
        preview_ofx = self._preview_ofx(self.conta_a)
        linhas_confirmar = _linhas_confirmar_padrao_ui(
            preview_ofx,
            categoria_despesa_id=self.cat_d.id,
            categoria_receita_id=self.cat_r.id,
        )
        self.assertEqual(len(linhas_confirmar), EXPECTED_NOVAS_OFX_PRIMEIRA)
        resp_ofx = self._confirmar(self.conta_a, linhas_confirmar)
        self.assertEqual(resp_ofx["criadas"], EXPECTED_NOVAS_OFX_PRIMEIRA)

        # --- 1ª importação XLSX ---
        preview_xlsx = self._preview_xlsx(self.conta_a)
        linhas_xlsx_confirmar = _linhas_confirmar_padrao_ui(
            preview_xlsx,
            categoria_despesa_id=self.cat_d.id,
            categoria_receita_id=self.cat_r.id,
        )
        self.assertEqual(len(linhas_xlsx_confirmar), EXPECTED_NOVAS_XLSX)
        resp_xlsx = self._confirmar(self.conta_a, linhas_xlsx_confirmar)
        self.assertEqual(resp_xlsx["criadas"], EXPECTED_NOVAS_XLSX)

        self.conta_a.refresh_from_db()
        self.assertEqual(
            Transacao.objects.filter(conta=self.conta_a).count(),
            EXPECTED_TOTAL_CONTA_A,
        )
        _assert_sem_duplicatas_logicas(self.conta_a, self.user)
        saldo_a = calcular_saldo_esperado(self.conta_a)
        assert_saldo_conta(self.conta_a, saldo_a, "GOLDEN-SALDO-A")
        snapshot_a = _ledger_snapshot(self.conta_a)

        # --- Transação inválida: rejeitada sem alterar ledger ---
        self._confirmar_rejeita(
            self.conta_a,
            [
                {
                    "indice": 0,
                    "data": "data-invalida",
                    "valor": "99.00",
                    "tipo": "despesa",
                    "descricao": "Linha inválida",
                    "categoria_id": self.cat_d.id,
                }
            ],
        )
        self.assertEqual(_ledger_snapshot(self.conta_a), snapshot_a)

        # --- Planilha inválida: preview rejeita (não persiste) ---
        r_inv = self.client.post(
            self.url_xlsx_preview,
            {
                "conta_id": self.conta_a.pk,
                "arquivo": _xlsx_upload(build_xlsx_invalid("linha_data_invalida")),
            },
        )
        self.assertEqual(r_inv.status_code, 400)
        self.assertEqual(_ledger_snapshot(self.conta_a), snapshot_a)

        # --- Re-upload incremental (idempotência) ---
        exp_re_ofx = expectativa_importacao(self.user, self.conta_a, linhas_ofx)
        self.assertEqual(exp_re_ofx["criadas_se_confirmar_padrao_ui"], 0)

        preview_re_ofx = self._preview_ofx(self.conta_a)
        re_ofx = _linhas_confirmar_padrao_ui(
            preview_re_ofx,
            categoria_despesa_id=self.cat_d.id,
            categoria_receita_id=self.cat_r.id,
        )
        self.assertEqual(re_ofx, [])
        resp_re_ofx = self._confirmar(self.conta_a, re_ofx)
        self.assertEqual(resp_re_ofx["criadas"], 0)

        exp_re_xlsx = expectativa_importacao(self.user, self.conta_a, linhas_xlsx)
        self.assertEqual(exp_re_xlsx["criadas_se_confirmar_padrao_ui"], 0)

        preview_re_xlsx = self._preview_xlsx(self.conta_a)
        re_xlsx = _linhas_confirmar_padrao_ui(
            preview_re_xlsx,
            categoria_despesa_id=self.cat_d.id,
            categoria_receita_id=self.cat_r.id,
        )
        self.assertEqual(re_xlsx, [])
        resp_re_xlsx = self._confirmar(self.conta_a, re_xlsx)
        self.assertEqual(resp_re_xlsx["criadas"], 0)

        self.conta_a.refresh_from_db()
        self.assertEqual(_ledger_snapshot(self.conta_a), snapshot_a)
        assert_saldo_conta(self.conta_a, saldo_a, "GOLDEN-IDEMP-A")

        # --- Isolamento conta_b (sem seed; mesmos arquivos) ---
        exp_b_ofx = expectativa_importacao(self.user, self.conta_b, linhas_ofx)
        self.assertEqual(exp_b_ofx["criadas_se_confirmar_padrao_ui"], 5)

        preview_b_ofx = self._preview_ofx(self.conta_b)
        b_ofx = _linhas_confirmar_padrao_ui(
            preview_b_ofx,
            categoria_despesa_id=self.cat_d.id,
            categoria_receita_id=self.cat_r.id,
        )
        self.assertEqual(len(b_ofx), 5)
        self._confirmar(self.conta_b, b_ofx)

        preview_b_xlsx = self._preview_xlsx(self.conta_b)
        b_xlsx = _linhas_confirmar_padrao_ui(
            preview_b_xlsx,
            categoria_despesa_id=self.cat_d.id,
            categoria_receita_id=self.cat_r.id,
        )
        self._confirmar(self.conta_b, b_xlsx)

        self.assertEqual(
            Transacao.objects.filter(conta=self.conta_b).count(),
            EXPECTED_TOTAL_CONTA_B,
        )
        _assert_sem_duplicatas_logicas(self.conta_b, self.user)

        saldo_b = calcular_saldo_esperado(self.conta_b)
        assert_saldo_conta(self.conta_b, saldo_b, "GOLDEN-SALDO-B")
        assert_saldo_conta(self.conta_b, saldo_a, "GOLDEN-SALDO-AB-IGUAL")

        self.assertEqual(Transacao.objects.filter(conta=self.conta_a).count(), 6)
        self.assertEqual(Transacao.objects.filter(conta=self.conta_b).count(), 6)
        self.assertNotEqual(_ledger_snapshot(self.conta_a), _ledger_snapshot(self.conta_b))
