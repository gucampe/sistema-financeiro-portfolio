from django.test import TestCase
from django.urls import reverse

from usuarios.models import Perfil
from usuarios.temas import COOKIE_TEMA, TEMA_CLARO, TEMA_ESCURO
from usuarios.tests.helpers.seguranca_fixtures import par_usuarios


class TemaAparenciaTests(TestCase):
    def test_perfil_nasce_no_claro(self):
        par = par_usuarios()
        self.assertEqual(par.perfil_a.tema, TEMA_CLARO)
        resp = par.client_a.get(reverse("usuarios:configuracoes"))
        html = resp.content.decode()
        self.assertNotIn('class="dark"', html)
        self.assertIn('data-tema="claro"', html)
        self.assertIn("Ativar modo escuro", html)
        self.assertIn("css/theme-tokens.css", html)
        self.assertIn("css/theme-dark.css", html)
        self.assertNotIn("prefers-color-scheme", html)

    def test_post_persiste_escuro_e_cookie(self):
        par = par_usuarios()
        resp = par.client_a.post(
            reverse("usuarios:configuracoes_tema"),
            data='{"tema": "escuro"}',
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["tema"], TEMA_ESCURO)
        par.perfil_a.refresh_from_db()
        self.assertEqual(par.perfil_a.tema, TEMA_ESCURO)
        self.assertEqual(resp.cookies[COOKIE_TEMA].value, TEMA_ESCURO)
        pagina = par.client_a.get(reverse("usuarios:configuracoes"))
        html = pagina.content.decode()
        self.assertIn('class="dark"', html)
        self.assertIn('data-tema="escuro"', html)
        self.assertIn("Ativar modo claro", html)

    def test_anonimo_nao_altera_tema(self):
        resp = self.client.post(
            reverse("usuarios:configuracoes_tema"),
            data='{"tema": "escuro"}',
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 302)

    def test_nao_segue_preferencia_do_sistema(self):
        par = par_usuarios()
        resp = par.client_a.get(
            reverse("usuarios:configuracoes"),
            HTTP_SEC_CH_PREFERS_COLOR_SCHEME="dark",
        )
        self.assertNotIn('class="dark"', resp.content.decode())
        self.assertEqual(Perfil.objects.get(pk=par.perfil_a.pk).tema, TEMA_CLARO)

    def test_login_aplica_cookie_do_perfil(self):
        par = par_usuarios()
        par.perfil_a.tema = TEMA_ESCURO
        par.perfil_a.save(update_fields=["tema"])
        resp = self.client.post(
            reverse("usuarios:login"),
            {"email": par.user_a.email, "senha": "x"},
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.cookies[COOKIE_TEMA].value, TEMA_ESCURO)
