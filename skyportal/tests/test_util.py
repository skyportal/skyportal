import os

import pytest
from playwright.sync_api import (
    TimeoutError as PlaywrightTimeoutError,
)
from playwright.sync_api import (
    expect,
    sync_playwright,
)

from baselayer.app import models
from baselayer.app.config import load_config

cfg = load_config()

# ---------------------------------------------------------------------------
# Playwright frontend testing
#
# Tests take a ``page`` (a Playwright Page) and drive the UI with locators +
# ``expect`` (which auto-wait, eliminating the explicit WebDriverWait/xpath
# polling Selenium needed -- and the flakiness that came with it). The page is
# session-scoped and logged in once.
# ---------------------------------------------------------------------------

PLAYWRIGHT_BASE_URL = f"http://localhost:{cfg['ports.app']}"
TESTUSER_XPATH = '//*[contains(string(),"testuser-cesium-ml-org")]'
# Generous default: Playwright only waits the full timeout on failure (it
# resolves as soon as the condition is met), and several pages (maps, GCN
# events, observation plans) render slowly. The legacy Selenium tests used
# explicit 20-30s waits on these; a 30s default covers them centrally.
# Overridable via env so CI (where the 2-vCPU runner makes page rendering slower
# under load) can grant more headroom without affecting local runs.
PLAYWRIGHT_DEFAULT_TIMEOUT_MS = int(
    os.environ.get("PLAYWRIGHT_DEFAULT_TIMEOUT_MS", 30_000)
)


def _frontend_test_headless():
    return str(os.getenv("FRONTEND_TEST_HEADLESS", "0")).strip().lower() in (
        "1",
        "true",
        "t",
        "yes",
        "y",
    )


def playwright_login(page):
    """Log in the shared page as testuser-cesium-ml-org (via the fake-OAuth
    ``debug_login`` flow enabled in the test config)."""
    page.goto("/")
    # Already logged in?
    if page.locator(TESTUSER_XPATH).first.is_visible():
        return
    login_link = page.locator('//a[contains(@href,"/login/google-oauth2")]').first
    try:
        login_link.wait_for(state="visible", timeout=20_000)
        login_link.click()
    except PlaywrightTimeoutError:
        pass  # no login link -> assume already authenticated
    expect(page.locator(TESTUSER_XPATH).first).to_be_visible(timeout=20_000)


@pytest.fixture(scope="session")
def page():
    """Session-scoped, authenticated Playwright page bound to the test server.

    ``base_url`` is set so tests navigate with relative paths (``page.goto("/")``,
    ``page.goto(f"/source/{id}")``).
    """
    try:
        expect.set_options(timeout=PLAYWRIGHT_DEFAULT_TIMEOUT_MS)
    except Exception:
        pass

    with sync_playwright() as p:
        browser = p.firefox.launch(
            headless=_frontend_test_headless(),
            firefox_user_prefs={
                "ui.primaryPointerCapabilities": 6,
                "ui.allPointerCapabilities": 6,
                # Aladin Lite (localization sky views) is WebGL2-only; allow the
                # software renderer so those plots work on GPU-less CI runners.
                "webgl.disabled": False,
                "webgl.force-enabled": True,
                "webgl.forbid-software": False,
                "webgl.out-of-process": False,
                "gfx.webrender.software": True,
            },
        )
        context = browser.new_context(
            base_url=PLAYWRIGHT_BASE_URL,
            viewport={"width": 1920, "height": 1200},
            accept_downloads=True,
        )
        context.set_default_timeout(PLAYWRIGHT_DEFAULT_TIMEOUT_MS)
        page = context.new_page()
        playwright_login(page)
        try:
            yield page
        finally:
            context.close()
            browser.close()


@pytest.fixture(scope="function", autouse=True)
def reset_state(request):
    # Roll back at setup as well as teardown: if a previous test's fixture
    # teardown left the shared DBSession in a failed-flush (PendingRollbackError)
    # state, recover here so a single isolation glitch can't cascade into every
    # subsequent test. A rollback only discards uncommitted state -- fixtures
    # commit their own data -- so this is safe.
    models.DBSession().rollback()

    def teardown():
        models.DBSession().rollback()

    request.addfinalizer(teardown)
