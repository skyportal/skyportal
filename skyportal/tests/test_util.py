import os

import pytest
from selenium import webdriver
from selenium.common.exceptions import (
    ElementClickInterceptedException,
    JavascriptException,
    NoSuchElementException,
    StaleElementReferenceException,
    TimeoutException,
)
from selenium.webdriver.common.action_chains import ActionChains
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
        scroll_script = (
            """
                arguments[0].scrollIntoView();
            """
            if scroll_parent
            else """
            const viewPortHeight = Math.max(document.documentElement.clientHeight, window.innerHeight || 0);
            const elementTop = arguments[0].getBoundingClientRect().top;
            window.scrollBy(0, elementTop - (viewPortHeight / 2));
            """
        )
        self.execute_script(scroll_script, element)

    def scroll_to_element_and_click(self, element, timeout=10, scroll_parent=False):
        self.scroll_to_element(element, scroll_parent=scroll_parent)
        ActionChains(self).move_to_element(element).perform()

        try:
            return element.click()
        except ElementClickInterceptedException:
            pass
        except StaleElementReferenceException:
            pass

        try:
            return self.execute_script("arguments[0].click();", element)
        except JavascriptException:
            pass
        except StaleElementReferenceException:
            pass

        # Tried to click something that's not a button, try sending
        # a mouse click to that coordinate
        ActionChains(self).click().perform()

    def click_xpath(self, xpath, wait_clickable=True, timeout=10, scroll_parent=False):
        if wait_clickable:
            element = self.wait_for_xpath_to_be_clickable(xpath, timeout=timeout)
        else:
            element = self.wait_for_xpath(xpath)
        return self.scroll_to_element_and_click(element, scroll_parent=scroll_parent)

    def click_css(self, css, timeout=10, scroll_parent=False):
        element = self.wait_for_css_to_be_clickable(css, timeout=timeout)
        return self.scroll_to_element_and_click(element, scroll_parent=scroll_parent)


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
