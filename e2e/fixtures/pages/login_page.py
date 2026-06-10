from __future__ import annotations

from playwright.sync_api import Page, expect

from e2e.fixtures.pages.base_page import BasePage


class LoginPage(BasePage):
    def open(self) -> None:
        self.goto("/login/")

    def login(self, email: str, password: str) -> None:
        self.open()
        self.page.fill("#email", email)
        self.page.fill("#senha", password)
        self.page.click('button[type="submit"]')
        self.page.wait_for_load_state("domcontentloaded")

    def expect_redirect_dashboard(self) -> None:
        self.page.wait_for_url("**/relatorios/**", timeout=15000)
