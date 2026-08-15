from django.test import Client, TestCase
from django.urls import reverse

from django.contrib.auth import get_user_model


class InstitucionalSiteTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_home_e_institucional_nao_landing(self):
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode()
        self.assertIn("GranaGo", html)
        self.assertIn("pra onde foi cada real", html)
        self.assertNotIn("Veja 3 meses de gastos", html)
        self.assertIn("/primeiros-donos/", html)
        self.assertIn("Garantir minha vaga no GranaGo", html)

    def test_landing_permanece_em_primeiros_donos(self):
        resp = self.client.get("/primeiros-donos/")
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode()
        self.assertIn("Veja 3 meses de gastos", html)
        self.assertIn("Primeiros Donos", html)

    def test_paginas_institucionais(self):
        paginas = [
            ("usuarios:nossa_historia", "Nossa História", "desenvolvedor"),
            ("usuarios:como_funciona", "Como funciona", "Registre sua primeira transação"),
            ("usuarios:faq", "Dúvidas frequentes", "Precisa conectar minha conta bancária?"),
        ]
        for name, title, trecho in paginas:
            with self.subTest(name=name):
                resp = self.client.get(reverse(name))
                self.assertEqual(resp.status_code, 200)
                html = resp.content.decode()
                self.assertIn(title, html)
                self.assertIn(trecho, html)
                self.assertIn("/primeiros-donos/", html)

    def test_legais_novas_urls_e_redirects(self):
        priv = self.client.get("/politica-de-privacidade/")
        self.assertEqual(priv.status_code, 200)
        self.assertIn("Política de Privacidade", priv.content.decode())

        termos = self.client.get("/termos-de-uso/")
        self.assertEqual(termos.status_code, 200)
        self.assertIn("Termos de Uso", termos.content.decode())

        legacy_p = self.client.get("/privacidade/")
        self.assertEqual(legacy_p.status_code, 301)
        self.assertTrue(legacy_p["Location"].endswith("/politica-de-privacidade/"))

        legacy_t = self.client.get("/termos/")
        self.assertEqual(legacy_t.status_code, 301)
        self.assertTrue(legacy_t["Location"].endswith("/termos-de-uso/"))

    def test_robots_e_sitemap(self):
        robots = self.client.get("/robots.txt")
        self.assertEqual(robots.status_code, 200)
        self.assertIn("Sitemap:", robots.content.decode())

        sitemap = self.client.get("/sitemap.xml")
        self.assertEqual(sitemap.status_code, 200)
        xml = sitemap.content.decode()
        for path in (
            "/",
            "/nossa-historia/",
            "/como-funciona/",
            "/faq/",
            "/politica-de-privacidade/",
            "/termos-de-uso/",
            "/primeiros-donos/",
        ):
            self.assertIn(path, xml)

    def test_home_nao_redireciona_usuario_autenticado(self):
        User = get_user_model()
        user = User.objects.create_user(
            email="inst@test.local",
            password="SenhaForte123!",
            nome="Inst",
        )
        self.client.force_login(user)
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("pra onde foi cada real", resp.content.decode())

    def test_home_aceita_head(self):
        resp = self.client.head("/")
        self.assertEqual(resp.status_code, 200)

    def test_home_seo_basico(self):
        resp = self.client.get("/")
        html = resp.content.decode()
        self.assertIn("<title>", html)
        self.assertIn('name="description"', html)
        self.assertIn('property="og:title"', html)
        self.assertIn('rel="canonical"', html)
