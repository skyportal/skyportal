import uuid

# import pytest
from selenium.common.exceptions import TimeoutException

# from skyportal.tests import api

# from .test_sources import add_comment_and_wait_for_display


def enter_comment_text(driver, comment_text):
    comment_xpath = (
        "//*[@data-testid=individual-spectra-accordion]//input[@name='text']"
    )
    comment_xpath = "//div[@data-testid='comments-accordion']//input[@name='text']"
    comment_box = driver.wait_for_xpath(comment_xpath)
    driver.click_xpath(comment_xpath)
    comment_box.send_keys(comment_text)


def add_comment(driver, comment_text):
    enter_comment_text(driver, comment_text)
    driver.click_xpath(
        '//div[@data-testid="comments-accordion"]//*[@name="submitCommentButton"]'
    )


def add_comment_and_wait_for_display(driver, comment_text):
    add_comment(driver, comment_text)

    try:
        driver.wait_for_xpath(f'//p[text()="{comment_text}"]', timeout=20)
    except TimeoutException:
        driver.refresh()
        driver.wait_for_xpath(f'//p[text()="{comment_text}"]')


def test_comments(driver, user, public_source):
    driver.get(f"/become_user/{user.id}")
    driver.get(f"/source/{public_source.id}")
    driver.wait_for_xpath(f'//div[text()="{public_source.id}"]')
    comment_text = str(uuid.uuid4())
    add_comment_and_wait_for_display(driver, comment_text)
