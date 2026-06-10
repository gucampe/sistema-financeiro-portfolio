"""Fixtures pytest-playwright + Django live_server."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

pytest_plugins = ["pytest_playwright"]

from e2e.factories.personas import (
    E2E_PASSWORD,
    seed_persona_basic,
    seed_persona_card_user,
    seed_persona_cartao_b,
    seed_persona_ecossistema,
    seed_persona_orcamentos,
    seed_persona_relatorios,
)
from e2e.helpers.observability import (
    attach_console_listener,
    har_path_for,
    is_e2e_item,
    on_test_failed,
    start_tracing,
    stop_tracing,
)

# Timezone determinístico (TZ-*)
os.environ.setdefault("TZ", "America/Sao_Paulo")
# Playwright pytest pode rodar em contexto async; Django ORM exige sync.
os.environ.setdefault("DJANGO_ALLOW_ASYNC_UNSAFE", "true")


@pytest.fixture(scope="session")
def browser_type_launch_args(browser_type_launch_args):
    return {
        **browser_type_launch_args,
        "args": ["--disable-dev-shm-usage"],
    }


@pytest.fixture
def browser_context_args(browser_context_args, request):
    artifacts = ROOT / "artifacts"
    artifacts.mkdir(parents=True, exist_ok=True)
    args = {
        **browser_context_args,
        "timezone_id": "America/Sao_Paulo",
        "locale": "pt-BR",
        "record_video_dir": str(artifacts / "videos"),
    }
    nodeid = request.node.nodeid
    if is_e2e_item(nodeid) and "chromium" in nodeid:
        har = har_path_for(nodeid)
        args["record_har_path"] = str(har)
        args["record_har_mode"] = "minimal"
    return args


@pytest.fixture
def app_base_url(live_server):
    return live_server.url


@pytest.fixture
def persona_basic(db):
    return seed_persona_basic(f"basic-{os.getpid()}@e2e.granago.test")


@pytest.fixture
def persona_card(db):
    return seed_persona_card_user(f"card-{os.getpid()}@e2e.granago.test")


@pytest.fixture
def persona_cartao_b(db):
    return seed_persona_cartao_b(f"cartao-b-{os.getpid()}@e2e.granago.test")


@pytest.fixture
def persona_relatorios(db):
    """Persona idempotente; KPIs via kpi_home() com TZ America/Sao_Paulo."""
    return seed_persona_relatorios(f"rel-{os.getpid()}@e2e.granago.test")


@pytest.fixture
def dashboard_tz():
    """Garante timezone determinístico para testes Dashboard/KPIs."""
    os.environ["TZ"] = "America/Sao_Paulo"
    return "America/Sao_Paulo"


@pytest.fixture
def persona_ecossistema(db):
    return seed_persona_ecossistema(f"eco-{os.getpid()}@e2e.granago.test")


@pytest.fixture
def logged_in_ecossistema_page(page, app_base_url, persona_ecossistema):
    from e2e.fixtures.pages.login_page import LoginPage

    login = LoginPage(page, app_base_url)
    login.login(persona_ecossistema["user"].email, E2E_PASSWORD)
    login.expect_redirect_dashboard()
    return page, persona_ecossistema


@pytest.fixture
def persona_orcamentos(db):
    return seed_persona_orcamentos(f"orc-{os.getpid()}@e2e.granago.test")


@pytest.fixture
def logged_in_page(page, app_base_url, persona_basic):
    from e2e.fixtures.pages.login_page import LoginPage

    login = LoginPage(page, app_base_url)
    login.login(persona_basic["user"].email, E2E_PASSWORD)
    login.expect_redirect_dashboard()
    return page


@pytest.fixture
def logged_in_card_page(page, app_base_url, persona_card):
    from e2e.fixtures.pages.login_page import LoginPage

    login = LoginPage(page, app_base_url)
    login.login(persona_card["user"].email, E2E_PASSWORD)
    login.expect_redirect_dashboard()
    return page


@pytest.fixture
def logged_in_cartao_b_page(page, app_base_url, persona_cartao_b):
    from e2e.fixtures.pages.login_page import LoginPage

    login = LoginPage(page, app_base_url)
    login.login(persona_cartao_b["user"].email, E2E_PASSWORD)
    login.expect_redirect_dashboard()
    return page


@pytest.fixture
def logged_in_relatorios_page(page, app_base_url, persona_relatorios):
    from e2e.fixtures.pages.login_page import LoginPage

    login = LoginPage(page, app_base_url)
    login.login(persona_relatorios["user"].email, E2E_PASSWORD)
    login.expect_redirect_dashboard()
    return page


@pytest.fixture
def logged_in_orcamentos_page(page, app_base_url, persona_orcamentos):
    from e2e.fixtures.pages.login_page import LoginPage

    login = LoginPage(page, app_base_url)
    login.login(persona_orcamentos["user"].email, E2E_PASSWORD)
    login.expect_redirect_dashboard()
    return page


@pytest.fixture
def page(page, context, request):
    """Envolve page do pytest-playwright com trace, console e artefatos em falha."""
    nodeid = request.node.nodeid
    if not is_e2e_item(nodeid):
        yield page
        return

    console_logs = attach_console_listener(page)
    request.node._e2e_console_logs = console_logs
    start_tracing(context)
    yield page

    failed = (
        hasattr(request.node, "rep_call")
        and request.node.rep_call is not None
        and request.node.rep_call.failed
    )
    if failed:
        on_test_failed(
            page,
            nodeid,
            context=context,
            console_logs=console_logs,
        )
    else:
        stop_tracing(context, nodeid, failed=False)


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    rep = outcome.get_result()
    setattr(item, "rep_" + rep.when, rep)


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "django_db: django database access",
    )
