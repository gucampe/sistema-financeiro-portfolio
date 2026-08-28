"""Contrato LEAN — Segurança e Permissões (16 unit + 2 skipped)."""

from __future__ import annotations

import json

import pytest
from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from cartoes.models import Fatura
from transacoes.models import Transacao
from usuarios.models import AuditLog
from usuarios.forms import PreferenciasFinanceirasForm
from usuarios.tests.helpers.asserts_seguranca import (
    assert_contagem_inalterada,
    assert_form_invalid,
    assert_http_200,
    assert_http_302_login,
    assert_http_403,
    assert_http_404,
    assert_http_not_403,
    assert_json_404,
    assert_recurso_ausente_para_usuario,
)
from usuarios.tests.helpers.seguranca_fixtures import (
    client_csrf_strict,
    csrf_token,
    disparar_import_cross_tenant,
    par_usuarios,
    seed_cartao_fatura_a,
    seed_recurso_b,
    seed_transacao_a,
)


@pytest.mark.seguranca
class TestSegurancaUnit(TestCase):
    # --- HTTP: AUTH ---

    def test_unit_sec_01_anonimo_configuracoes_redireciona_login(self):
        resp = Client().get(reverse("usuarios:configuracoes"))
        assert_http_302_login(resp)

    def test_unit_sec_02_logado_configuracoes_ok(self):
        par = par_usuarios()
        resp = par.client_a.get(reverse("usuarios:configuracoes"))
        assert_http_200(resp)

    def test_configuracoes_nao_oferece_contribuicao_anonimizada(self):
        par = par_usuarios()
        resp = par.client_a.get(reverse("usuarios:configuracoes"))
        html = resp.content.decode()
        self.assertNotIn("Contribuir com dados anonimizados", html)
        self.assertNotIn("categorizacao_contribuir_globais", html)
        form = PreferenciasFinanceirasForm(instance=par.perfil_a, user=par.user_a)
        self.assertNotIn("categorizacao_contribuir_globais", form.fields)

    def test_unit_sec_02b_usuario_inativo_nao_autentica(self):
        user = get_user_model().objects.create_user(
            email="inativo@test.local", password="x", nome="Inativo"
        )
        user.ativo = False
        user.save(update_fields=["ativo"])
        client = Client(enforce_csrf_checks=False)
        resp = client.post(
            reverse("usuarios:login"),
            {"email": "inativo@test.local", "senha": "x"},
        )
        assert_http_302_login(resp)

    # --- FORM ---

    def test_unit_sec_03_form_rejeita_categoria_de_b(self):
        par = par_usuarios()
        form = PreferenciasFinanceirasForm(
            data={
                "moeda": "BRL",
                "tipo_transacao_padrao": "despesa",
                "conta_padrao": str(par.conta_a.pk),
                "categoria_padrao": str(par.cat_b.pk),
                "ocultar_valores_dashboard": False,
            },
            instance=par.perfil_a,
            user=par.user_a,
        )
        assert_form_invalid(form, "categoria_padrao")

    def test_unit_sec_04_form_rejeita_conta_de_b(self):
        par = par_usuarios()
        form = PreferenciasFinanceirasForm(
            data={
                "moeda": "BRL",
                "tipo_transacao_padrao": "despesa",
                "conta_padrao": str(par.conta_b.pk),
                "categoria_padrao": str(par.cat_a.pk),
                "ocultar_valores_dashboard": False,
            },
            instance=par.perfil_a,
            user=par.user_a,
        )
        assert_form_invalid(form, "conta_padrao")

    # --- HTTP: IDOR ---

    def test_unit_sec_05_idor_get_editar_transacao_b(self):
        par = par_usuarios()
        pk_b = seed_recurso_b(par, "transacao")
        url = reverse("transacoes:editar", kwargs={"pk": pk_b})
        resp = par.client_a.get(f"{url}?ajax=1")
        assert_http_404(resp)

    def test_unit_sec_06_idor_post_excluir_transacao_b(self):
        par = par_usuarios()
        pk_b = seed_recurso_b(par, "transacao")
        url = reverse("transacoes:excluir", kwargs={"pk": pk_b})
        resp = par.client_a.post(url)
        assert_http_404(resp)

    def test_unit_sec_07_idor_post_arquivar_conta_b(self):
        par = par_usuarios()
        id_b = seed_recurso_b(par, "conta")
        url = reverse("contas:arquivar", kwargs={"id": id_b})
        resp = par.client_a.post(url)
        assert_http_404(resp)

    def test_unit_sec_08_idor_post_excluir_cartao_b(self):
        par = par_usuarios()
        id_b = seed_recurso_b(par, "cartao")
        url = reverse("cartoes:excluir", kwargs={"id": id_b})
        resp = par.client_a.post(url)
        assert_http_404(resp)

    def test_unit_sec_09_idor_get_fatura_detalhe_b(self):
        par = par_usuarios()
        fatura_id = seed_recurso_b(par, "fatura")
        fatura = Fatura.objects.get(pk=fatura_id)
        url = reverse(
            "cartoes:fatura_detalhe",
            kwargs={"cartao_id": fatura.cartao_id, "fatura_id": fatura_id},
        )
        resp = par.client_a.get(url)
        assert_http_404(resp)

    def test_unit_sec_10_idor_get_export_job_b(self):
        par = par_usuarios()
        job_id = seed_recurso_b(par, "export_job")
        url = reverse("relatorios:api_export_job_detail", kwargs={"pk": job_id})
        resp = par.client_a.get(url)
        assert_json_404(resp)

    def test_unit_sec_10b_idor_post_toggle_orcamento_b(self):
        from decimal import Decimal

        from relatorios.models import OrcamentoCategoria

        par = par_usuarios()
        orc = OrcamentoCategoria.objects.create(
            usuario=par.user_b,
            categoria=par.cat_b,
            valor_planejado=Decimal("100.00"),
        )
        url = reverse("relatorios:orcamentos_toggle_ativo", kwargs={"pk": orc.pk})
        resp = par.client_a.post(url)
        assert_http_404(resp)

    def test_unit_sec_10c_idor_post_excluir_orcamento_b(self):
        from decimal import Decimal

        from relatorios.models import OrcamentoCategoria

        par = par_usuarios()
        orc = OrcamentoCategoria.objects.create(
            usuario=par.user_b,
            categoria=par.cat_b,
            valor_planejado=Decimal("50.00"),
        )
        url = reverse("relatorios:orcamentos_excluir", kwargs={"pk": orc.pk})
        resp = par.client_a.post(url)
        assert_http_404(resp)

    def test_unit_sec_10d_idor_post_arquivar_categoria_b(self):
        par = par_usuarios()
        url = reverse("categorias:arquivar")
        resp = par.client_a.post(
            url,
            {"categoria_id": par.cat_b.pk},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        assert resp.status_code == 404

    def test_unit_sec_10e_idor_post_excluir_regra_b(self):
        from categorizacao.models import RegraCategorizacao

        par = par_usuarios()
        regra = RegraCategorizacao.objects.create(
            usuario=par.user_b,
            tipo_regra="contains",
            padrao="LOJA B",
            padrao_normalizado="loja b",
            categoria=par.cat_b,
            tipo_transacao="despesa",
        )
        url = reverse("categorizacao:excluir_regra", kwargs={"pk": regra.pk})
        resp = par.client_a.post(url)
        assert_http_404(resp)

    # --- HTTP: API anônima ---

    def test_unit_sec_11_anonimo_api_serie_tendencia(self):
        url = reverse("relatorios:api_serie_tendencia")
        resp = Client().get(f"{url}?preset=este_mes")
        assert_http_302_login(resp)

    def test_unit_sec_12_anonimo_post_api_export_csv(self):
        url = reverse("relatorios:api_export_csv")
        resp = Client().post(url, data={"preset": "este_mes"})
        assert_http_302_login(resp)

    # --- HTTP: import cross-tenant ---

    def test_unit_sec_13_import_conta_b_retorna_404(self):
        par = par_usuarios()
        url = reverse("transacoes:importar_ofx_confirmar")
        payload = {
            "conta_id": par.conta_b.pk,
            "linhas": [
                {
                    "data": "2026-04-01",
                    "valor": "50.00",
                    "tipo": "despesa",
                    "descricao": "Import cross",
                }
            ],
        }
        resp = par.client_a.post(
            url,
            data=json.dumps(payload),
            content_type="application/json",
        )
        assert_http_404(resp)

    # --- ESTADO ---

    def test_unit_sec_14_import_nao_altera_contagem_a(self):
        par = par_usuarios()
        antes, depois = disparar_import_cross_tenant(par)
        assert_contagem_inalterada(antes, depois)

    def test_unit_sec_15_recurso_b_ausente_para_usuario_a(self):
        par = par_usuarios()
        pk_b = seed_recurso_b(par, "transacao")
        assert_recurso_ausente_para_usuario(par.user_a, Transacao, pk_b)

    # --- HTTP: CSRF bloco único ---

    def test_unit_sec_16_csrf_estados_e_endpoints_mutaveis(self):
        par = par_usuarios()
        client = client_csrf_strict(par.user_a)
        token = csrf_token(client)

        tx_pk = seed_transacao_a(par)
        url_excluir = reverse("transacoes:excluir", kwargs={"pk": tx_pk})

        resp_sem = client.post(url_excluir)
        assert_http_403(resp_sem)

        resp_inv = client.post(
            url_excluir,
            HTTP_X_CSRFTOKEN="invalido",
        )
        assert_http_403(resp_inv)

        resp_ok = client.post(
            url_excluir,
            HTTP_X_CSRFTOKEN=token,
        )
        assert_http_not_403(resp_ok)

        cartao_id, fatura_id = seed_cartao_fatura_a(par)
        url_pagar = reverse(
            "cartoes:pagar_fatura",
            kwargs={"cartao_id": cartao_id, "fatura_id": fatura_id},
        )
        resp_pagar = client.post(url_pagar)
        assert_http_403(resp_pagar)

        url_export = reverse("relatorios:api_export_csv")
        resp_export = client.post(url_export, data={"preset": "este_mes"})
        assert_http_403(resp_export)

    def test_unit_sec_17_categoria_icone_malicioso_rejeitado(self):
        par = par_usuarios()
        url = reverse("categorias:adicionar")
        resp = par.client_a.post(
            url,
            {
                "nome": "Teste XSS",
                "icone": "<script>alert(1)</script>",
                "cor": "#4F46E5",
                "tipo": "despesa",
            },
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        assert resp.status_code == 400

    def test_unit_sec_18_exclusao_conta_nao_afeta_outro_usuario(self):
        par = par_usuarios()
        pk_a = par.user_a.pk
        par.client_b.post(
            reverse("usuarios:excluir_conta"),
            {"senha": "x", "confirmo": "on"},
        )
        assert get_user_model().objects.filter(pk=pk_a).exists()
        assert get_user_model().objects.filter(pk=par.user_b.pk).exists() is False

    def test_unit_sec_19_overposting_transacao_ignora_usuario_id(self):
        par = par_usuarios()
        url = reverse("transacoes:adicionar")
        resp = par.client_a.post(
            url,
            {
                "tipo": "despesa",
                "conta": par.conta_a.pk,
                "categoria": par.cat_a.pk,
                "descricao": "Overpost TX",
                "valor": "10.00",
                "data": "2026-07-01",
                "usuario_id": par.user_b.pk,
                "is_staff": "true",
            },
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        tx = Transacao.objects.get(pk=data["id"])
        assert tx.usuario_id == par.user_a.pk
        assert tx.usuario.is_staff is False

    def test_unit_sec_20_overposting_categoria_ignora_padrao_e_usuario(self):
        from categorias.models import Categoria

        par = par_usuarios()
        url = reverse("categorias:adicionar")
        resp = par.client_a.post(
            url,
            {
                "nome": "Cat Overpost",
                "icone": "fa-ellipsis-h",
                "cor": "#4F46E5",
                "tipo": "despesa",
                "padrao": "true",
                "usuario_id": par.user_b.pk,
            },
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        cat = Categoria.objects.get(pk=data["id"])
        assert cat.usuario_id == par.user_a.pk
        assert cat.padrao is False


@pytest.mark.seguranca
@pytest.mark.django_db
def test_sec_rl_01_login_throttle(settings):
    """N falhas no mesmo e-mail → bloqueio Axes (não depende de IP)."""
    from django.test import Client

    User = get_user_model()
    User.objects.create_user(email="rl@test.local", password="good", nome="RL")
    client = Client(enforce_csrf_checks=False)
    url = reverse("usuarios:login")
    limit = getattr(settings, "AXES_FAILURE_LIMIT", 5)
    for _ in range(limit):
        client.post(url, {"email": "rl@test.local", "senha": "wrong"})
    resp = client.post(url, {"email": "rl@test.local", "senha": "wrong"})
    assert resp.status_code in (403, 429)


@pytest.mark.seguranca
@pytest.mark.django_db
def test_sec_rl_02_lockout_nao_bloqueia_outro_email_no_mesmo_cliente(settings):
    """Lockout por e-mail: outra conta no mesmo IP/cliente ainda autentica."""
    from django.test import Client

    User = get_user_model()
    User.objects.create_user(email="rl-a@test.local", password="good-a", nome="RLA")
    User.objects.create_user(email="rl-b@test.local", password="good-b", nome="RLB")
    client = Client(enforce_csrf_checks=False)
    url = reverse("usuarios:login")
    limit = getattr(settings, "AXES_FAILURE_LIMIT", 5)
    for _ in range(limit + 1):
        client.post(url, {"email": "rl-a@test.local", "senha": "wrong"})
    resp = client.post(url, {"email": "rl-b@test.local", "senha": "good-b"})
    assert resp.status_code == 302
    assert "/login/" not in resp["Location"]


@pytest.mark.seguranca
@pytest.mark.django_db
def test_sec_aud_01_export_requested_audit():
    """Criação de export job gera AuditLog export_requested."""
    par = par_usuarios()
    url = reverse("relatorios:api_export_jobs_create")
    resp = par.client_a.post(url, {"dominio": "titular_lgpd", "formato": "zip"})
    assert resp.status_code == 202
    assert AuditLog.objects.filter(
        usuario=par.user_a,
        acao=AuditLog.ACAO_EXPORT_REQUESTED,
    ).exists()
