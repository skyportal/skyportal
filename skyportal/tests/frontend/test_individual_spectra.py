import uuid
import pytest
from selenium.common.exceptions import TimeoutException


def enter_comment_text(driver, comment_text):
    comment_xpath = (
        "//div[contains(@data-testid, 'individual-spectrum-id_')]//input[@name='text']"
    )
    comment_box = driver.wait_for_xpath(comment_xpath)
    driver.click_xpath(comment_xpath)
    comment_box.send_keys(comment_text)


def add_comment(driver, comment_text):
    enter_comment_text(driver, comment_text)
    driver.click_xpath(
        "//div[contains(@data-testid, 'individual-spectrum-id_')]//*[@name='submitCommentButton']"
    )


def add_comment_and_wait_for_display(driver, comment_text):
    add_comment(driver, comment_text)

    try:
        driver.wait_for_xpath(f'//p[text()="{comment_text}"]', timeout=20)
    except TimeoutException:
        driver.refresh()
        driver.wait_for_xpath(f'//p[text()="{comment_text}"]')


@pytest.mark.flaky(reruns=2)
def test_comments(driver, user, public_source):

    driver.get(f"/become_user/{user.id}")

    # Test the individual spectra comments on the Source page
    driver.get(f"/source/{public_source.id}")

    driver.wait_for_xpath(f'//div[text()="{public_source.id}"]')

    # open the accordion with all the individual spectra
    driver.click_xpath("//div[@data-testid='individual-spectra-accordion']")

    comment_text = str(uuid.uuid4())
    add_comment_and_wait_for_display(driver, comment_text)

    # now test the Manage Data page
    # driver.get(f"/manage_data/{public_source.id}")

    # driver.click_xpath('//tr[@id="MUIDataTableBodyRow-0"]//*[@id="expandable-button"]')
    # add_comment_and_wait_for_display(driver, comment_text)
