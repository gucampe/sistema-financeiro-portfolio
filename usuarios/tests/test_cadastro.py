from __future__ import annotations

import threading
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core import mail
from django.core.cache import cache
from django.core.exceptions import ImproperlyConfigured
from django.db import connection, connections
from django.test import Client, TestCase, TransactionTestCase, override_settings
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from usuarios.models import AuditLog, Consentimento, LeadPrimeirosDonos, Usuario
from usuarios.services.cadastro import registrar_primeiro_dono
from usuarios.services.email_acesso import url_absoluta_app
from usuarios.tokens import conta_setup_token_generator
from usuarios.turnstile import verificar_turnstile
from usuarios.utils import normalizar_email, normalizar_whatsapp

User = get_user_model()

SENHA_OK = "Frase-segura-granago-92"


def _post_captura(client, **kwargs):
    data = {
        "nome": kwargs.get("nome", "Maria Silva"),
        "email": kwargs.get("email", "maria@example.com"),
        "whatsapp": kwargs.get("whatsapp", "(11) 98888-7777"),
    }
    return client.post(reverse("usuarios:captura_lead"), data)


class NormalizacaoTests(TestCase):
    def test_email_lowercase_completo(self):
        self.assertEqual(normalizar_email("  Gustavo@Exemplo.COM "), "gustavo@exemplo.com")

    def test_whatsapp_so_digitos(self):
        self.assertEqual(normalizar_whatsapp("(11) 98888-7777"), "11988887777")


class CapturaCadastroTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = Client()

    def test_post_cria_usuario_lead_consentimento_e_email(self):
        with self.captureOnCommitCallbacks(execute=True):
            resp = _post_captura(self.client)
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(resp["Location"].endswith("/obrigado/"))
        self.assertEqual(User.objects.filter(email="maria@example.com").count(), 1)
        user = User.objects.get(email="maria@example.com")
        self.assertFalse(user.has_usable_password())
        self.assertEqual(user.origem, Usuario.ORIGEM_PRIMEIROS_DONOS)
        self.assertEqual(user.whatsapp, "11988887777")
        lead = LeadPrimeirosDonos.objects.get(email="maria@example.com")
        self.assertEqual(lead.usuario_id, user.pk)
        self.assertEqual(lead.whatsapp, "11988887777")
        self.assertEqual(Consentimento.objects.filter(usuario=user).count(), 1)
        self.assertEqual(AuditLog.objects.filter(acao=AuditLog.ACAO_SIGNUP, usuario=user).count(), 1)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Maria, seu acesso ao GranaGo chegou", mail.outbox[0].subject)
        self.assertIn("/conta/configurar/", mail.outbox[0].body)

    def test_email_case_insensitive_nao_duplica(self):
        with self.captureOnCommitCallbacks(execute=True):
            _post_captura(self.client, email="Gustavo@exemplo.com")
            _post_captura(self.client, email="gustavo@exemplo.com", nome="Gustavo 2")
        self.assertEqual(User.objects.filter(email__iexact="gustavo@exemplo.com").count(), 1)
        self.assertEqual(LeadPrimeirosDonos.objects.count(), 1)
        lead = LeadPrimeirosDonos.objects.get()
        self.assertEqual(lead.nome, "Gustavo 2")

    def test_recaptura_preserva_criado_em_e_usuario(self):
        with self.captureOnCommitCallbacks(execute=True):
            _post_captura(self.client, email="a@example.com", nome="Ana", whatsapp="11911111111")
        lead = LeadPrimeirosDonos.objects.get(email="a@example.com")
        criado = lead.criado_em
        user_id = lead.usuario_id
        with self.captureOnCommitCallbacks(execute=True):
            _post_captura(self.client, email="a@example.com", nome="Ana Paula", whatsapp="11922222222")
        lead.refresh_from_db()
        self.assertEqual(lead.criado_em, criado)
        self.assertEqual(lead.usuario_id, user_id)
        self.assertEqual(lead.nome, "Ana Paula")
        self.assertEqual(lead.whatsapp, "11922222222")

    def test_whatsapp_mascarado_vira_digitos(self):
        with self.captureOnCommitCallbacks(execute=True):
            _post_captura(self.client, whatsapp="(21) 99999-0000")
        self.assertEqual(User.objects.get().whatsapp, "21999990000")

    def test_cooldown_nao_envia_segundo_email_e_segue_obrigado(self):
        with self.captureOnCommitCallbacks(execute=True):
            r1 = _post_captura(self.client)
            r2 = _post_captura(self.client, nome="Maria 2")
        self.assertEqual(r1.status_code, 302)
        self.assertEqual(r2.status_code, 302)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(User.objects.count(), 1)

    def test_apos_cooldown_envia_de_novo(self):
        with self.captureOnCommitCallbacks(execute=True):
            _post_captura(self.client)
        cache.delete("setup_email:maria@example.com")
        with self.captureOnCommitCallbacks(execute=True):
            _post_captura(self.client)
        self.assertEqual(len(mail.outbox), 2)

    def test_limite_5_por_hora(self):
        with self.captureOnCommitCallbacks(execute=True):
            _post_captura(self.client)
        cache.delete("setup_email:maria@example.com")
        cache.set("setup_email_hour:maria@example.com", 5, timeout=3600)
        with self.captureOnCommitCallbacks(execute=True):
            resp = _post_captura(self.client)
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(len(mail.outbox), 1)

    def test_ja_configurado_nao_duplica_e_email_diferente(self):
        User.objects.create_user(
            email="maria@example.com",
            password=SENHA_OK,
            nome="Maria",
        )
        with self.captureOnCommitCallbacks(execute=True):
            resp = _post_captura(self.client)
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(User.objects.filter(email="maria@example.com").count(), 1)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("já tem", mail.outbox[0].body.lower())

    def test_flag_desligada_nao_cria(self):
        with override_settings(PRIMEIROS_DONOS_SIGNUP_ENABLED=False):
            resp = _post_captura(self.client)
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(User.objects.count(), 0)

    def test_obrigado_cta_na_session(self):
        with self.captureOnCommitCallbacks(execute=True):
            _post_captura(self.client)
        resp = self.client.get(reverse("usuarios:obrigado"))
        self.assertEqual(resp.status_code, 200)
        self.assertIn("/conta/configurar/", resp.context["conta_setup_url"])

    def test_obrigado_sem_session_cai_no_reset(self):
        resp = self.client.get(reverse("usuarios:obrigado"))
        self.assertEqual(resp.status_code, 200)
        self.assertIn("/senha/redefinir/", resp.context["conta_setup_url"])

    def test_anti_enumeracao_mesmo_redirect(self):
        User.objects.create_user(email="ja@example.com", password=SENHA_OK, nome="Ja")
        with self.captureOnCommitCallbacks(execute=True):
            novo = _post_captura(self.client, email="novo@example.com")
            velho = _post_captura(self.client, email="ja@example.com")
        self.assertEqual(novo.status_code, velho.status_code)
        self.assertTrue(novo["Location"].endswith("/obrigado/"))
        self.assertTrue(velho["Location"].endswith("/obrigado/"))

    def test_falha_email_mantem_usuario(self):
        with patch(
            "usuarios.services.cadastro.enviar_email_setup",
            side_effect=OSError("smtp down"),
        ), patch("sentry_sdk.capture_exception") as capture:
            with self.captureOnCommitCallbacks(execute=True):
                _post_captura(self.client)
            capture.assert_called()
        self.assertEqual(User.objects.filter(email="maria@example.com").count(), 1)


class UrlAppTests(TestCase):
    def test_app_host_quando_nao_debug(self):
        with override_settings(DEBUG=False, APP_HOST="app.granago.com.br"):
            self.assertEqual(
                url_absoluta_app("/conta/configurar/x/y/"),
                "https://app.granago.com.br/conta/configurar/x/y/",
            )


class TurnstileTests(TestCase):
    def test_bypass_sem_chaves_fora_de_producao(self):
        with override_settings(
            IS_PRODUCTION=False,
            DEBUG=True,
            TURNSTILE_SITE_KEY="",
            TURNSTILE_SECRET_KEY="",
        ):
            self.assertTrue(verificar_turnstile(""))

    def test_producao_sem_chaves_erro(self):
        with override_settings(IS_PRODUCTION=True, TURNSTILE_SITE_KEY="", TURNSTILE_SECRET_KEY=""):
            with self.assertRaises(ImproperlyConfigured):
                verificar_turnstile("token")

    def test_token_invalido_rejeita_captura(self):
        with override_settings(TURNSTILE_SITE_KEY="site", TURNSTILE_SECRET_KEY="secret"):
            with patch("usuarios.views.verificar_turnstile", return_value=False):
                resp = _post_captura(Client())
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(User.objects.count(), 0)


class SetupContaTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = Client()
        self.user = User.objects.create_user(
            email="setup@example.com",
            password=None,
            nome="Setup User",
            origem=Usuario.ORIGEM_PRIMEIROS_DONOS,
        )
        self.uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        self.token = conta_setup_token_generator.make_token(self.user)
        self.url = reverse("usuarios:conta_configurar", args=[self.uid, self.token])

    def test_token_valido_define_senha_e_login(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp["Referrer-Policy"], "same-origin")
        resp = self.client.post(
            self.url,
            {"new_password1": SENHA_OK, "new_password2": SENHA_OK},
        )
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(resp["Location"].endswith("/primeiros-passos/"))
        self.user.refresh_from_db()
        self.assertTrue(self.user.has_usable_password())
        self.assertTrue(self.user.check_password(SENHA_OK))
        log = AuditLog.objects.filter(acao=AuditLog.ACAO_PASSWORD_CHANGE, usuario=self.user).first()
        self.assertIsNotNone(log)
        self.assertEqual(log.metadata.get("origem"), "conta_setup")
        self.assertIn("_auth_user_id", self.client.session)

    def test_segundo_uso_redireciona_login(self):
        self.client.post(self.url, {"new_password1": SENHA_OK, "new_password2": SENHA_OK})
        self.client.logout()
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(resp["Location"].endswith("/login/"))

    def test_token_adulterado_tela_generica(self):
        url = reverse("usuarios:conta_configurar", args=[self.uid, "token-falso"])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertIn("inválido ou vencido", resp.content.decode())
        self.assertIn("/senha/redefinir/", resp.content.decode())

    def test_uid_inexistente_tela_generica(self):
        uid = urlsafe_base64_encode(force_bytes(999999))
        url = reverse("usuarios:conta_configurar", args=[uid, "abc"])
        resp = self.client.get(url)
        html = resp.content.decode()
        self.assertEqual(resp.status_code, 200)
        self.assertIn("inválido ou vencido", html)
        self.assertNotIn("999999", html)

    def test_token_expirado(self):
        with override_settings(CONTA_SETUP_TIMEOUT=-1):
            resp = self.client.get(self.url)
        self.assertIn("inválido ou vencido", resp.content.decode())

    def test_autenticado_nao_usa_token_de_outro(self):
        outro = User.objects.create_user(email="outro@example.com", password=SENHA_OK, nome="Outro")
        self.client.force_login(outro, backend="usuarios.backends.EmailBackend")
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(resp["Location"].endswith("/primeiros-passos/"))
        self.user.refresh_from_db()
        self.assertFalse(self.user.has_usable_password())


class CapturaConcorrenciaTests(TransactionTestCase):
    def test_dois_posts_simultaneos_um_usuario(self):
        if connection.vendor == "sqlite":
            self.skipTest("corrida exige isolamento real (PostgreSQL)")
        cache.clear()
        erros = []

        def worker():
            try:
                registrar_primeiro_dono(
                    nome="Race",
                    email="race@example.com",
                    whatsapp="11988887777",
                )
            except Exception as exc:
                erros.append(exc)
            finally:
                connections.close_all()

        t1 = threading.Thread(target=worker)
        t2 = threading.Thread(target=worker)
        t1.start()
        t2.start()
        t1.join(timeout=15)
        t2.join(timeout=15)
        self.assertFalse(t1.is_alive())
        self.assertFalse(t2.is_alive())
        self.assertEqual(erros, [])
        self.assertEqual(User.objects.filter(email="race@example.com").count(), 1)
        self.assertEqual(LeadPrimeirosDonos.objects.filter(email="race@example.com").count(), 1)
