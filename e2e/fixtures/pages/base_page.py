from __future__ import annotations

from playwright.sync_api import Locator, Page, expect


class BasePage:
    def __init__(self, page: Page, base_url: str) -> None:
        self.page = page
        self.base_url = base_url.rstrip("/")

    def goto(self, path: str) -> None:
        url = path if path.startswith("http") else f"{self.base_url}{path}"
        self.page.goto(url)

    def expect_url_contains(self, fragment: str) -> None:
        expect(self.page).to_have_url(lambda url: fragment in url)

    def first_visible(self, selector: str) -> Locator:
        """Primeiro elemento visível — evita clicar em blocos mobile/desktop ocultos por CSS."""
        loc = self.page.locator(selector)
        for i in range(loc.count()):
            item = loc.nth(i)
            if item.is_visible():
                return item
        return loc.first

    def click_first_visible(self, selector: str) -> None:
        item = self.first_visible(selector)
        expect(item).to_be_visible()
        item.click()
