import pytest
import uuid
from tdtax import taxonomy, __version__
from selenium.webdriver.common.keys import Keys
from datetime import datetime, timezone

from skyportal.tests import api
from skyportal.tests.frontend.sources_and_followup_etc.test_sources import (
    add_comment_and_wait_for_display,
)


def filter_for_value(driver, value, last=False):
    if last:
        xpath = '(//*[@data-testid="Search-iconButton"])[last()]'
    else:
        xpath = '//*[@data-testid="Search-iconButton"]'
    driver.click_xpath(xpath)
    search_input_xpath = "//input[@aria-label='Search']"
    search_input = driver.wait_for_xpath(search_input_xpath)
    driver.click_xpath(search_input_xpath)
    search_input.send_keys(value)


@pytest.mark.flaky(reruns=2)
def test_mention_generates_notification_then_mark_read_and_delete(
    driver, user, public_source
):
    driver.get(f"/become_user/{user.id}")
    driver.get(f"/source/{public_source.id}")
    driver.wait_for_xpath(f'//div[text()="{public_source.id}"]')

    comment_text = f"@{user.username}"
    add_comment_and_wait_for_display(driver, comment_text)

    driver.wait_for_xpath("//span[text()='1']")
    driver.click_xpath('//*[@data-testid="notificationsButton"]')
    driver.wait_for_xpath('//*[text()=" mentioned you in a comment on "]')
    driver.click_xpath('//*[contains(@data-testid, "markReadButton")]')
    driver.wait_for_xpath("//button[text()='Mark unread']")
    driver.click_xpath('//*[contains(@data-testid, "deleteNotificationButton")]')
    driver.wait_for_xpath_to_disappear('//*[text()=" mentioned you in a comment on "]')
    driver.wait_for_xpath("//*[text()='No notifications']")


@pytest.mark.flaky(reruns=2)
def test_group_admission_requests_notifications(
    driver,
    user,
    super_admin_user,
    public_group,
    public_group2,
    super_admin_token,
):
    # Make super_admin_user an admin member of group2
    status, data = api(
        "POST",
        f"groups/{public_group2.id}/users",
        data={"userID": super_admin_user.id, "admin": True},
        token=super_admin_token,
    )
    assert status == 200

    driver.get(f'/become_user/{user.id}')
    driver.get('/groups')
    driver.wait_for_xpath('//h6[text()="My Groups"]')
    filter_for_value(driver, public_group2.name)
    driver.click_xpath(f'//*[@data-testid="requestAdmissionButton{public_group2.id}"]')
    driver.wait_for_xpath(
        f'//*[@data-testid="deleteAdmissionRequestButton{public_group2.id}"]'
    )
    driver.get(f"/become_user/{super_admin_user.id}")
    driver.get(f"/group/{public_group2.id}")
    driver.click_xpath('//*[@data-testid="notificationsButton"]')
    driver.wait_for_xpath('//*[text()=" has requested to join "]')
    driver.click_xpath('//*[@data-testid="deleteAllNotificationsButton"]')
    driver.wait_for_xpath_to_disappear('//*[text()=" has requested to join "]')

    filter_for_value(driver, user.username, last=True)
    driver.wait_for_xpath('//div[text()="pending"]')
    driver.click_xpath(f'//*[@data-testid="acceptRequestButton{user.id}"]')
    driver.wait_for_xpath('//div[text()="accepted"]')
    driver.wait_for_xpath(f'//a[text()="{user.username}"]')

    driver.get(f'/become_user/{user.id}')
    driver.get("/")
    driver.click_xpath('//*[@data-testid="notificationsButton"]')
    driver.wait_for_xpath('//em[text()="accepted"]')
    driver.wait_for_xpath(f'//em[text()="{public_group2.name}"]')


def test_comment_on_favorite_source_triggers_notification(
    driver, user, user2, public_source
):
    driver.get(f'/become_user/{user.id}')
    driver.get("/profile")

    # Enable browser notifications for favorite source comments
    favorite_sources = driver.wait_for_xpath('//*[@name="favorite_sources"]')
    driver.scroll_to_element_and_click(favorite_sources)

    favorite_sources_new_comments = driver.wait_for_xpath(
        '//*[@name="favorite_sources_new_comments"]'
    )
    driver.scroll_to_element_and_click(favorite_sources_new_comments)

    # Make public_source a favorite
    driver.get(f"/source/{public_source.id}")
    driver.click_xpath(f'//*[@data-testid="favorites-exclude_{public_source.id}"]')
    driver.wait_for_xpath(f'//*[@data-testid="favorites-include_{public_source.id}"]')

    # Become user2 and submit comment on source
    driver.get(f'/become_user/{user2.id}')
    driver.get(f"/source/{public_source.id}")
    add_comment_and_wait_for_display(driver, "comment text")

    # Check that notification was created
    driver.get(f'/become_user/{user.id}')
    driver.get("/")
    driver.wait_for_xpath("//span[text()='1']")
    driver.click_xpath('//*[@data-testid="notificationsButton"]')
    driver.wait_for_xpath('//*[contains(text(), "New comment on favorite source")]')


def test_classification_on_favorite_source_triggers_notification(
    driver, user, user2, public_source, public_group, taxonomy_token
):
    status, data = api(
        'POST',
        'taxonomy',
        data={
            'name': "test taxonomy" + str(uuid.uuid4()),
            'hierarchy': taxonomy,
            'group_ids': [public_group.id],
            'provenance': f"tdtax_{__version__}",
            'version': __version__,
            'isLatest': True,
        },
        token=taxonomy_token,
    )
    assert status == 200

    driver.get(f'/become_user/{user.id}')
    driver.get("/profile")

    # Enable browser notifications for favorite source comments
    favorite_sources = driver.wait_for_xpath('//*[@name="favorite_sources"]')
    driver.scroll_to_element_and_click(favorite_sources)

    favorite_sources_new_classifications = driver.wait_for_xpath(
        '//*[@name="favorite_sources_new_classifications"]'
    )
    driver.scroll_to_element_and_click(favorite_sources_new_classifications)

    # Make public_source a favorite
    driver.get(f"/source/{public_source.id}")
    driver.click_xpath(f'//*[@data-testid="favorites-exclude_{public_source.id}"]')
    driver.wait_for_xpath(f'//*[@data-testid="favorites-include_{public_source.id}"]')

    # Become user2 and submit comment on source
    driver.get(f'/become_user/{user2.id}')
    driver.get(f"/source/{public_source.id}")

    # add a classification
    groupSelect = driver.wait_for_xpath('//*[@id="groupSelect"]')
    driver.scroll_to_element_and_click(groupSelect)

    driver.click_xpath(
        f'//li[contains(text(), "{public_group.name}")]',
        scroll_parent=True,
    )

    root_taxonomy = driver.wait_for_xpath('//*[@id="root_taxonomy"]')
    driver.scroll_to_element_and_click(root_taxonomy)

    driver.click_xpath(
        '//li[contains(text(), "test taxonomy")]',
        scroll_parent=True,
    )

    classification = driver.wait_for_xpath('//*[@id="classification"]')
    driver.scroll_to_element_and_click(classification)
    driver.click_xpath(
        '//li[@data-value="DM annihilation <> Nonstellar"]',
        scroll_parent=True,
    )

    probability = driver.wait_for_xpath('//*[@id="probability"]')
    driver.scroll_to_element_and_click(probability)
    probability.send_keys("0.5")
    probability.send_keys(Keys.ENTER)

    # Check that notification was created
    driver.get(f'/become_user/{user.id}')
    driver.get("/")
    driver.wait_for_xpath("//span[text()='1']")
    driver.click_xpath('//*[@data-testid="notificationsButton"]')
    driver.wait_for_xpath(
        '//*[contains(text(), "New classification on favorite source")]'
    )


def test_spectra_on_favorite_source_triggers_notification(
    driver, user, public_source, lris, upload_data_token, public_group
):
    driver.get(f'/become_user/{user.id}')
    driver.get("/profile")

    # Enable browser notifications for favorite source comments
    favorite_sources = driver.wait_for_xpath('//*[@name="favorite_sources"]')
    driver.scroll_to_element_and_click(favorite_sources)

    favorite_sources_new_comments = driver.wait_for_xpath(
        '//*[@name="favorite_sources_new_spectra"]'
    )
    driver.scroll_to_element_and_click(favorite_sources_new_comments)

    # Make public_source a favorite
    driver.get(f"/source/{public_source.id}")
    driver.click_xpath(f'//*[@data-testid="favorites-exclude_{public_source.id}"]')
    driver.wait_for_xpath(f'//*[@data-testid="favorites-include_{public_source.id}"]')

    # Add spectrum to public_source
    status, data = api(
        'POST',
        'spectrum',
        data={
            'obj_id': public_source.id,
            'observed_at': str(datetime.now(timezone.utc)),
            'instrument_id': lris.id,
            'wavelengths': [664, 665, 666],
            'fluxes': [234.2, 232.1, 235.3],
            'group_ids': [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data['status'] == 'success'

    # Check that notification was created
    driver.get(f'/become_user/{user.id}')
    driver.get("/")
    driver.wait_for_xpath("//span[text()='1']")
    driver.click_xpath('//*[@data-testid="notificationsButton"]')
    driver.wait_for_xpath('//*[contains(text(), "New spectrum on favorite source")]')
