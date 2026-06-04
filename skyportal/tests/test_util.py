import os
import time

import pytest
from selenium import webdriver
from selenium.common.exceptions import (
    ElementClickInterceptedException,
    JavascriptException,
    MoveTargetOutOfBoundsException,
    NoSuchElementException,
    StaleElementReferenceException,
    TimeoutException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.ui import WebDriverWait
from seleniumrequests.request import RequestsSessionMixin

from baselayer.app import models
from baselayer.app.config import load_config

cfg = load_config()


def set_server_url(server_url):
    """Set web driver server URL using value loaded from test config file."""
    MyCustomWebDriver.server_url = server_url


class MyCustomWebDriver(RequestsSessionMixin, webdriver.Firefox):
    @property
    def server_url(self):
        if not hasattr(self, "_server_url"):
            raise NotImplementedError(
                "Please first set the web driver URL using `set_server_url`"
            )
        return self._server_url

    @server_url.setter
    def server_url(self, value):
        self._server_url = value

    def get(self, uri):
        webdriver.Firefox.get(self, self.server_url + uri)
        try:
            self.find_element(By.ID, "websocketStatus")
            self.wait_for_xpath(
                "//*[@id='websocketStatus' and contains(@title,'connected')]"
            )
        except NoSuchElementException:
            pass

    def wait_for_xpath(self, xpath, timeout=10):
        return WebDriverWait(self, timeout).until(
            expected_conditions.presence_of_element_located((By.XPATH, xpath))
        )

    def wait_for_css(self, css, timeout=10):
        return WebDriverWait(self, timeout).until(
            expected_conditions.presence_of_element_located((By.CSS_SELECTOR, css))
        )

    def wait_for_xpath_to_appear(self, xpath, timeout=10):
        return WebDriverWait(self, timeout).until_not(
            expected_conditions.invisibility_of_element((By.XPATH, xpath))
        )

    def wait_for_xpath_to_disappear(self, xpath, timeout=10):
        return WebDriverWait(self, timeout).until(
            expected_conditions.invisibility_of_element((By.XPATH, xpath))
        )

    def wait_for_css_to_disappear(self, css, timeout=10):
        return WebDriverWait(self, timeout).until(
            expected_conditions.invisibility_of_element((By.CSS_SELECTOR, css))
        )

    def wait_for_xpath_to_be_clickable(self, xpath, timeout=10):
        return WebDriverWait(self, timeout).until(
            expected_conditions.element_to_be_clickable((By.XPATH, xpath))
        )

    def wait_for_xpath_to_be_unclickable(self, xpath, timeout=10):
        return WebDriverWait(self, timeout).until_not(
            expected_conditions.element_to_be_clickable((By.XPATH, xpath))
        )

    def wait_for_css_to_be_clickable(self, css, timeout=10):
        return WebDriverWait(self, timeout).until(
            expected_conditions.element_to_be_clickable((By.CSS_SELECTOR, css))
        )

    def wait_for_css_to_be_unclickable(self, css, timeout=10):
        return WebDriverWait(self, timeout).until_not(
            expected_conditions.element_to_be_clickable((By.CSS_SELECTOR, css))
        )

    def scroll_to_element(self, element, scroll_parent=False):
        # scrollIntoView({block: 'center'}) walks ancestor scroll containers
        # (MUI overflow:auto panels in the source/scanning views), where the
        # old window.scrollBy was a silent no-op. `scroll_parent` is kept for
        # back-compat; the behavior is equivalent under the new scroller.
        self.execute_script(
            "arguments[0].scrollIntoView({block: 'center', inline: 'nearest'});",
            element,
        )

    def _try_click(self, element):
        # element.click() first (real DOM click event with focus/blur), JS
        # click as a fallback for elements obstructed by overlays.
        try:
            element.click()
            return True
        except ElementClickInterceptedException:
            pass
        try:
            self.execute_script("arguments[0].click();", element)
            return True
        except JavascriptException:
            return False

    def scroll_to_element_and_click(self, element, timeout=10, scroll_parent=False):
        # Two attempts: a single layout-shift between scroll and click (Aladin
        # init, font swap, async data load) used to throw
        # MoveTargetOutOfBoundsException / StaleElementReferenceException and
        # kill the test even though a re-scroll would have worked.
        for attempt in range(2):
            try:
                self.scroll_to_element(element, scroll_parent=scroll_parent)
                if self._try_click(element):
                    return
            except (
                StaleElementReferenceException,
                MoveTargetOutOfBoundsException,
            ):
                if attempt == 0:
                    time.sleep(0.05)
                    continue
                raise

    def click_xpath(self, xpath, wait_clickable=True, timeout=10, scroll_parent=False):
        # Retry the whole find-scroll-click on stale-element: when the DOM
        # re-renders mid-click the locator must be resolved again, not just
        # the click retried.
        for attempt in range(2):
            try:
                if wait_clickable:
                    element = self.wait_for_xpath_to_be_clickable(
                        xpath, timeout=timeout
                    )
                else:
                    element = WebDriverWait(self, timeout).until(
                        expected_conditions.visibility_of_element_located(
                            (By.XPATH, xpath)
                        )
                    )
                return self.scroll_to_element_and_click(
                    element, scroll_parent=scroll_parent
                )
            except (
                StaleElementReferenceException,
                MoveTargetOutOfBoundsException,
            ):
                if attempt == 0:
                    time.sleep(0.05)
                    continue
                raise

    def click_css(self, css, timeout=10, scroll_parent=False):
        for attempt in range(2):
            try:
                element = self.wait_for_css_to_be_clickable(css, timeout=timeout)
                return self.scroll_to_element_and_click(
                    element, scroll_parent=scroll_parent
                )
            except (
                StaleElementReferenceException,
                MoveTargetOutOfBoundsException,
            ):
                if attempt == 0:
                    time.sleep(0.05)
                    continue
                raise


@pytest.fixture(scope="session")
def driver(request):
    import shutil

    from selenium import webdriver
    from webdriver_manager.firefox import GeckoDriverManager

    options = webdriver.FirefoxOptions()
    if str(os.getenv("FRONTEND_TEST_HEADLESS", "0")).strip().lower() in (
        "1",
        "true",
        "t",
        "yes",
        "y",
    ):
        options.add_argument("-headless")
    options.set_preference("devtools.console.stdout.content", True)
    options.set_preference("browser.download.manager.showWhenStarting", False)
    options.set_preference("browser.download.folderList", 2)
    options.set_preference(
        "browser.download.dir", os.path.abspath(cfg["paths.downloads_folder"])
    )
    options.set_preference(
        "browser.helperApps.neverAsk.saveToDisk",
        (
            "text/csv,text/plain,application/octet-stream,"
            "text/comma-separated-values,text/html"
        ),
    )

    executable_path = shutil.which("geckodriver")
    if executable_path is None:
        executable_path = GeckoDriverManager().install()
    service = webdriver.firefox.service.Service(executable_path=executable_path)

    driver = MyCustomWebDriver(options=options, service=service)
    driver.set_window_size(1920, 1200)
    login(driver)

    yield driver

    driver.close()


def login(driver):
    username_xpath = '//*[contains(string(),"testuser-cesium-ml-org")]'

    driver.get("/")
    try:
        driver.wait_for_xpath(username_xpath, 0.25)
        return  # Already logged in
    except TimeoutException:
        pass

    try:
        element = driver.wait_for_xpath(
            '//a[contains(@href,"/login/google-oauth2")]', 20
        )
        element.click()
    except TimeoutException:
        pass

    try:
        driver.wait_for_xpath(username_xpath, 5)
    except TimeoutException:
        raise TimeoutException("Login failed:\n" + driver.page_source)


@pytest.fixture(scope="function", autouse=True)
def reset_state(request):
    def teardown():
        models.DBSession().rollback()

    request.addfinalizer(teardown)
