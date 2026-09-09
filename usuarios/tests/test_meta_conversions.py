from __future__ import annotations

import hashlib
import json
from unittest.mock import MagicMock, patch

from django.core.cache import cache
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from usuarios.services.meta_conversions import (
    enviar_complete_registration,
    hash_email,
    hash_external_id,
    hash_primeiro_nome,
    hash_sobrenome,
    hash_telefone,
    telefone_para_capi,
)
from usuarios.tests.test_cadastro import _post_captura


def _sha(valor: str) -> str:
    return hashlib.sha256(valor.encode("utf-8")).hexdigest()


class MetaHashTests(TestCase):
    def test_email_normalizado_antes_do_hash(self):
        self.assertEqual(hash_email("  Maria@Example.COM "), _sha("maria@example.com"))

    def test_telefone_recebe_ddi_55(self):
        self.assertEqual(telefone_para_capi("(11) 98888-7777"), "5511988887777")
        self.assertEqual(hash_telefone("(11) 98888-7777"), _sha("5511988887777"))

    def test_telefone_ja_com_ddi_nao_duplica(self):
        self.assertEqual(telefone_para_capi("5511988887777"), "5511988887777")

    def test_primeiro_nome_lowercase(self):
        self.assertEqual(hash_primeiro_nome("Maria Silva"), _sha("maria"))

    def test_sobrenome_junta_partes_depois_do_primeiro(self):
        self.assertEqual(hash_sobrenome("Maria Silva"), _sha("silva"))
        self.assertEqual(hash_sobrenome("Maria Silva Santos"), _sha("silvasantos"))
        self.assertEqual(hash_sobrenome("Maria"), "")

    def test_external_id_hasheia_pk(self):
        self.assertEqual(hash_external_id(42), _sha("42"))
        self.assertEqual(hash_external_id(None), "")


class MetaCapiEnvioTests(TestCase):
    def test_sem_credenciais_nao_chama_rede(self):
        with override_settings(META_PIXEL_ID="", META_CAPI_ACCESS_TOKEN=""):
            with patch("usuarios.services.meta_conversions.urllib.request.urlopen") as urlopen:
                ok = enviar_complete_registration(
                    event_id="evt-1",
                    email="maria@example.com",
                    nome="Maria",
                    whatsapp="11988887777",
                )
        self.assertFalse(ok)
        urlopen.assert_not_called()

    def test_payload_hasheado_com_test_event_code(self):
        cm = MagicMock()
        cm.status = 200
        cm.read.return_value = b'{"events_received":1}'
        with override_settings(
            META_PIXEL_ID="123456",
            META_CAPI_ACCESS_TOKEN="fake-token",
            META_CAPI_TEST_EVENT_CODE="TESTXXXX",
            META_CAPI_API_VERSION="v22.0",
            SITE_URL="https://granago.com.br",
        ):
            with patch(
                "usuarios.services.meta_conversions.urllib.request.urlopen"
            ) as urlopen:
                urlopen.return_value.__enter__.return_value = cm
                ok = enviar_complete_registration(
                    event_id="evt-abc",
                    email="maria@example.com",
                    nome="Maria Silva",
                    whatsapp="(11) 98888-7777",
                    usuario_id=42,
                )
        self.assertTrue(ok)
        req = urlopen.call_args[0][0]
        self.assertIn("/v22.0/123456/events", req.get_full_url())
        body = json.loads(req.data.decode())
        evento = body["data"][0]
        self.assertEqual(evento["event_name"], "CompleteRegistration")
        self.assertEqual(evento["event_id"], "evt-abc")
        self.assertEqual(evento["action_source"], "website")
        self.assertEqual(evento["event_source_url"], "https://granago.com.br/comece/")
        self.assertEqual(evento["user_data"]["em"], [_sha("maria@example.com")])
        self.assertEqual(evento["user_data"]["ph"], [_sha("5511988887777")])
        self.assertEqual(evento["user_data"]["fn"], [_sha("maria")])
        self.assertEqual(evento["user_data"]["ln"], [_sha("silva")])
        self.assertEqual(evento["user_data"]["external_id"], [_sha("42")])
        self.assertEqual(evento["user_data"]["country"], [_sha("br")])
        self.assertEqual(body["test_event_code"], "TESTXXXX")
        self.assertEqual(body["access_token"], "fake-token")
        raw = req.data.decode()
        self.assertNotIn("maria@example.com", raw)
        self.assertNotIn("98888", raw)


class MetaCapiCadastroTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = Client()

    def test_cadastro_novo_envia_capi_e_event_id_no_obrigado(self):
        cm = MagicMock()
        cm.status = 200
        cm.read.return_value = b"{}"
        with override_settings(
            META_PIXEL_ID="999888777",
            META_CAPI_ACCESS_TOKEN="fake-token",
            META_CAPI_TEST_EVENT_CODE="",
        ):
            with patch(
                "usuarios.services.meta_conversions.urllib.request.urlopen"
            ) as urlopen:
                urlopen.return_value.__enter__.return_value = cm
                with self.captureOnCommitCallbacks(execute=True):
                    resp = _post_captura(self.client)
                urlopen.assert_called_once()
                event_id = json.loads(urlopen.call_args[0][0].data.decode())["data"][0][
                    "event_id"
                ]
            self.assertEqual(resp.status_code, 302)
            obrigado = self.client.get(reverse("usuarios:obrigado"))
        html = obrigado.content.decode()
        self.assertIn(event_id.replace("-", r"\u002D"), html)
        self.assertIn("999888777", html)
        self.assertIn("completeRegistrationEventId", html)
        self.assertIn(_sha("maria@example.com"), html)
        self.assertIn(_sha("silva"), html)
        self.assertIn('"country": "br"', html)
        self.assertNotIn("maria@example.com", html)
        self.assertNotIn("fake-token", html)
        self.assertNotIn("access_token", html)

    def test_recaptura_nao_dispara_capi_de_novo(self):
        cm = MagicMock()
        cm.status = 200
        cm.read.return_value = b"{}"
        with override_settings(
            META_PIXEL_ID="999888777",
            META_CAPI_ACCESS_TOKEN="fake-token",
        ):
            with patch(
                "usuarios.services.meta_conversions.urllib.request.urlopen"
            ) as urlopen:
                urlopen.return_value.__enter__.return_value = cm
                with self.captureOnCommitCallbacks(execute=True):
                    _post_captura(self.client)
                    urlopen.reset_mock()
                    _post_captura(self.client, nome="Maria 2")
                urlopen.assert_not_called()

    def test_falha_capi_nao_quebra_cadastro(self):
        with override_settings(
            META_PIXEL_ID="999888777",
            META_CAPI_ACCESS_TOKEN="fake-token",
        ):
            with patch(
                "usuarios.services.meta_conversions.urllib.request.urlopen",
                side_effect=TimeoutError(),
            ):
                with self.captureOnCommitCallbacks(execute=True):
                    resp = _post_captura(self.client)
        self.assertEqual(resp.status_code, 302)
        from django.contrib.auth import get_user_model

        self.assertEqual(get_user_model().objects.filter(email="maria@example.com").count(), 1)

    def test_landing_sem_pixel_nao_injeta_meta(self):
        with override_settings(META_PIXEL_ID=""):
            html = self.client.get(reverse("usuarios:landing")).content.decode()
        self.assertNotIn("GRANAGO_META", html)
        self.assertNotIn("meta_pixel.js", html)
        self.assertNotIn("data-marketing-choice", html)

    def test_landing_com_pixel_informa_cookies_no_cadastro(self):
        with override_settings(META_PIXEL_ID="1750083062777982"):
            html = self.client.get(reverse("usuarios:landing")).content.decode()
        self.assertIn("1750083062777982", html)
        self.assertIn("meta_pixel.js", html)
        self.assertIn("incluindo cookies", html)
        self.assertNotIn("data-marketing-choice", html)
        self.assertNotIn("Aceitar cookies de anúncios", html)
        self.assertNotIn("cookie-consent-banner", html)
        self.assertNotIn("EAA", html)

    def test_fbclid_da_landing_vira_fbc_na_capi(self):
        cm = MagicMock()
        cm.status = 200
        cm.read.return_value = b"{}"
        with override_settings(
            META_PIXEL_ID="999888777",
            META_CAPI_ACCESS_TOKEN="fake-token",
        ):
            self.client.get(reverse("usuarios:landing") + "?fbclid=ClickIdABC")
            with patch(
                "usuarios.services.meta_conversions.urllib.request.urlopen"
            ) as urlopen:
                urlopen.return_value.__enter__.return_value = cm
                with self.captureOnCommitCallbacks(execute=True):
                    _post_captura(self.client)
                fbc = json.loads(urlopen.call_args[0][0].data.decode())["data"][0][
                    "user_data"
                ]["fbc"]
        self.assertTrue(fbc.startswith("fb.1."))
        self.assertTrue(fbc.endswith(".ClickIdABC"))

    def test_cookie_fbc_prevalece_sobre_fbclid_da_sessao(self):
        cm = MagicMock()
        cm.status = 200
        cm.read.return_value = b"{}"
        self.client.cookies["_fbc"] = "fb.1.1.FromCookie"
        with override_settings(
            META_PIXEL_ID="999888777",
            META_CAPI_ACCESS_TOKEN="fake-token",
        ):
            self.client.get(reverse("usuarios:landing") + "?fbclid=FromQuery")
            with patch(
                "usuarios.services.meta_conversions.urllib.request.urlopen"
            ) as urlopen:
                urlopen.return_value.__enter__.return_value = cm
                with self.captureOnCommitCallbacks(execute=True):
                    _post_captura(self.client)
                fbc = json.loads(urlopen.call_args[0][0].data.decode())["data"][0][
                    "user_data"
                ]["fbc"]
        self.assertEqual(fbc, "fb.1.1.FromCookie")

    def test_primeiro_fbclid_da_sessao_nao_e_sobrescrito(self):
        self.client.get(reverse("usuarios:landing") + "?fbclid=Primeiro")
        self.client.get(reverse("usuarios:landing") + "?fbclid=Segundo")
        self.assertEqual(self.client.session["meta_fbclid"], "Primeiro")
