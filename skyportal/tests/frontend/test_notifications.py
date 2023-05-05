import pytest
import uuid
import os
from tdtax import taxonomy, __version__
from datetime import datetime, timezone
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

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
    driver.get(f'/become_user/{user.id}')
    driver.get("/profile")

    # Enable notifications for mentions
    mention = driver.wait_for_xpath('//*[@name="mention"]')
    driver.scroll_to_element_and_click(mention)

    driver.wait_for_xpath(
        '//*[@name="mention"]/../../span[contains(@class,"Mui-checked")]'
    )

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
    driver.wait_for_xpath('//*[text()="New Group Admission Request from "]')
    driver.click_xpath('//*[@data-testid="deleteAllNotificationsButton"]')
    driver.wait_for_xpath_to_disappear(
        '//*[text()="New Group Admission Request from "]'
    )

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


@pytest.mark.flaky(reruns=3)
def test_comment_on_favorite_source_triggers_notification(
    driver, user, user2, public_source
):
    driver.get(f'/become_user/{user.id}')
    driver.get("/profile")

    # Enable browser notifications for favorite source comments
    favorite_sources = driver.wait_for_xpath('//*[@name="favorite_sources"]')
    driver.scroll_to_element_and_click(favorite_sources)

    driver.wait_for_xpath(
        '//*[@name="favorite_sources"]/../../span[contains(@class,"Mui-checked")]'
    )

    favorite_sources_new_comments = driver.wait_for_xpath(
        '//*[@name="favorite_sources_new_comments"]'
    )
    driver.scroll_to_element_and_click(favorite_sources_new_comments)

    driver.wait_for_xpath(
        '//*[@name="favorite_sources_new_comments"]/../../span[contains(@class,"Mui-checked")]'
    )

    # Make public_source a favorite
    driver.get(f"/source/{public_source.id}")
    driver.click_xpath(
        f'//*[@data-testid="favorites-exclude_{public_source.id}"]', timeout=30
    )
    driver.wait_for_xpath(
        f'//*[@data-testid="favorites-include_{public_source.id}"]', timeout=30
    )

    # Become user2 and submit comment on source
    driver.get(f'/become_user/{user2.id}')
    driver.get(f"/source/{public_source.id}")
    comment_text = str(uuid.uuid4())
    add_comment_and_wait_for_display(driver, comment_text)

    # Check that notification was created
    driver.get(f'/become_user/{user.id}')
    driver.get("/")
    driver.wait_for_xpath(f"//p[text()='{comment_text}']")
    driver.click_xpath('//*[@data-testid="notificationsButton"]')
    driver.wait_for_xpath('//*[contains(text(), "New comment on favorite source")]')


@pytest.mark.flaky(reruns=3)
def test_classification_on_favorite_source_triggers_notification(
    driver, user, public_source, public_group, taxonomy_token, classification_token
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
    taxonomy_id = data['data']['taxonomy_id']

    driver.get(f'/become_user/{user.id}')
    driver.get("/profile")

    # Enable browser notifications for favorite source comments
    favorite_sources = driver.wait_for_xpath('//*[@name="favorite_sources"]')
    driver.scroll_to_element_and_click(favorite_sources)

    driver.wait_for_xpath(
        '//*[@name="favorite_sources"]/../../span[contains(@class,"Mui-checked")]'
    )

    favorite_sources_new_classifications = driver.wait_for_xpath(
        '//*[@name="favorite_sources_new_classifications"]'
    )
    driver.scroll_to_element_and_click(favorite_sources_new_classifications)

    driver.wait_for_xpath(
        '//*[@name="favorite_sources_new_classifications"]/../../span[contains(@class,"Mui-checked")]'
    )

    # Make public_source a favorite
    driver.get(f"/source/{public_source.id}")
    driver.click_xpath(f'//*[@data-testid="favorites-exclude_{public_source.id}"]')
    driver.wait_for_xpath(f'//*[@data-testid="favorites-include_{public_source.id}"]')

    status, data = api(
        'POST',
        'classification',
        data={
            'obj_id': public_source.id,
            'classification': 'AGN',
            'taxonomy_id': taxonomy_id,
            'probability': 1.0,
            'group_ids': [public_group.id],
        },
        token=classification_token,
    )
    assert status == 200

    # Check that notification was created
    driver.get(f'/become_user/{user.id}')
    driver.get("/")
    driver.wait_for_xpath("//span[text()='1']")
    driver.click_xpath('//*[@data-testid="notificationsButton"]')
    driver.wait_for_xpath(
        '//*[contains(text(), "New classification on favorite source")]'
    )


@pytest.mark.flaky(reruns=3)
def test_spectra_on_favorite_source_triggers_notification(
    driver, user, public_source, lris, upload_data_token, public_group
):
    driver.get(f'/become_user/{user.id}')
    driver.get("/profile")

    # Enable browser notifications for favorite source comments
    favorite_sources = driver.wait_for_xpath('//*[@name="favorite_sources"]')
    driver.scroll_to_element_and_click(favorite_sources)

    driver.wait_for_xpath(
        '//*[@name="favorite_sources"]/../../span[contains(@class,"Mui-checked")]'
    )

    favorite_sources_new_comments = driver.wait_for_xpath(
        '//*[@name="favorite_sources_new_spectra"]'
    )
    driver.scroll_to_element_and_click(favorite_sources_new_comments)

    driver.wait_for_xpath(
        '//*[@name="favorite_sources_new_spectra"]/../../span[contains(@class,"Mui-checked")]'
    )

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


def test_new_classification_on_source_triggers_notification(
    driver, user, public_source, public_group, taxonomy_token, classification_token
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
    taxonomy_id = data['data']['taxonomy_id']

    driver.get(f'/become_user/{user.id}')
    driver.get("/profile")

    # Enable notifications for sources when a specific classification is added
    sources = driver.wait_for_xpath('//*[@name="sources"]')
    driver.scroll_to_element_and_click(sources)

    driver.wait_for_xpath(
        '//*[@name="sources"]/../../span[contains(@class,"Mui-checked")]'
    )

    sources_new_classification = driver.wait_for_xpath(
        "//*[@id='classifications-select']"
    )
    driver.scroll_to_element_and_click(sources_new_classification)
    driver.click_xpath(
        '//li[@data-value="AGN"]',
        scroll_parent=True,
    )

    driver.click_xpath(
        '//*[@data-testid="addShortcutButton" and contains(., "Update")]'
    )

    driver.wait_for_xpath('//*[contains(text(), "Sources classifications updated")]')

    status, data = api(
        'POST',
        'classification',
        data={
            'obj_id': public_source.id,
            'classification': 'AGN',
            'taxonomy_id': taxonomy_id,
            'probability': 1.0,
            'group_ids': [public_group.id],
        },
        token=classification_token,
    )
    assert status == 200

    # Check that notification was created
    driver.get(f'/become_user/{user.id}')
    driver.get("/")
    driver.wait_for_xpath("//span[text()='1']")
    driver.click_xpath('//*[@data-testid="notificationsButton"]')
    driver.wait_for_xpath('//*[contains(text(), "New classification")]')


def test_new_gcn_event_triggers_notification(driver, user, super_admin_token):

    driver.get(f'/become_user/{user.id}')
    driver.get("/profile")

    # Enable notifications for sources when a specific classification is added
    gcn_events = driver.wait_for_xpath('//*[@name="gcn_events"]')
    driver.scroll_to_element_and_click(gcn_events)

    driver.wait_for_xpath(
        '//*[@name="gcn_events"]/../../span[contains(@class,"Mui-checked")]'
    )

    new_notif_profile = '//*[@id="new-gcn-notification-profile"]'
    driver.wait_for_xpath(new_notif_profile)
    driver.click_xpath(new_notif_profile)

    gcn_events_name = driver.wait_for_xpath('//*[@id="GcnNotificationNameInput"]')
    gcn_events_name.send_keys('test')

    gcn_events_notice_types = driver.wait_for_xpath(
        '//*[@aria-labelledby="selectGcns"]'
    )
    driver.scroll_to_element_and_click(gcn_events_notice_types)

    driver.click_xpath(
        '//li[@data-value="FERMI_GBM_GND_POS"]',
    )

    # we close the dropdown list
    element = driver.switch_to.active_element
    element.send_keys(Keys.ESCAPE)

    create = '//*[@data-testid="addShortcutButton" and contains(., "Create")]'
    driver.execute_script(
        "arguments[0].scrollIntoView(true);", driver.wait_for_xpath(create)
    )
    driver.click_xpath(create)

    driver.wait_for_xpath('//*[contains(text(), "Gcn notice preferences updated")]')

    datafile = f'{os.path.dirname(__file__)}/../data/GRB180116A_Fermi_GBM_Gnd_Pos.xml'
    with open(datafile, 'rb') as fid:
        payload = fid.read()
    data = {'xml': payload}

    status, data = api('POST', 'gcn_event', data=data, token=super_admin_token)
    assert status == 200
    assert data['status'] == 'success'

    # Check that notification was created
    driver.get(f'/become_user/{user.id}')
    driver.get("/")
    driver.wait_for_xpath("//span[text()='1']")
    driver.click_xpath('//*[@data-testid="notificationsButton"]')
    driver.wait_for_xpath('//*[contains(text(), "New GCN Event")]')


def test_notification_setting_select(driver, user):
    driver.get(f'/become_user/{user.id}')
    driver.get("/profile")

    # Enable notifications for new mentions
    mention = driver.wait_for_xpath('//*[@name="mention"]')
    driver.scroll_to_element_and_click(mention)

    driver.wait_for_xpath(
        '//*[@name="mention"]/../../span[contains(@class,"Mui-checked")]'
    )

    mention_settings = driver.wait_for_xpath(
        '//*[@name="notification_settings_button_mention"]'
    )
    driver.scroll_to_element_and_click(mention_settings)

    email_setting = driver.wait_for_xpath(
        '//*[@name="email" and contains(@class, "MuiSwitch-input")]'
    )
    driver.scroll_to_element_and_click(email_setting)

    driver.wait_for_xpath(
        '//*[@name="email" and contains(@class, "MuiSwitch-input")]/../../span[contains(@class,"Mui-checked")]'
    )

    # same for slack
    slack_setting = driver.wait_for_xpath(
        '//*[@name="slack" and contains(@class, "MuiSwitch-input")]'
    )
    driver.scroll_to_element_and_click(slack_setting)
    driver.wait_for_xpath(
        '//*[@name="slack" and contains(@class, "MuiSwitch-input")]/../../span[contains(@class,"Mui-checked")]'
    )

    # same for sms
    sms_setting = driver.wait_for_xpath('//*[@name="sms"]')
    driver.scroll_to_element_and_click(sms_setting)
    driver.wait_for_xpath(
        '//*[@name="sms" and contains(@class, "MuiSwitch-input")]/../../span[contains(@class,"Mui-checked")]'
    )

    # sms settings appeared, so we can test them
    sms_on_shift_setting = driver.wait_for_xpath(
        '//*[@name="on_shift_sms" and contains(@class, "MuiSwitch-input")]'
    )
    driver.scroll_to_element_and_click(sms_on_shift_setting)
    driver.wait_for_xpath(
        '//*[@name="on_shift_sms" and contains(@class, "MuiSwitch-input")]/../../span[contains(@class,"Mui-checked")]'
    )

    sms_time_slot_setting = driver.wait_for_xpath(
        '//*[@name="time_slot_sms" and contains(@class, "MuiSwitch-input")]'
    )
    driver.scroll_to_element_and_click(sms_time_slot_setting)
    driver.wait_for_xpath(
        '//*[@name="time_slot_sms" and contains(@class, "MuiSwitch-input")]/../../span[contains(@class,"Mui-checked")]'
    )

    driver.wait_for_xpath('//*[@aria-label="time_slot_slider" and @value="8"]')
    driver.wait_for_xpath('//*[@aria-label="time_slot_slider" and @value="20"]')
    start_time_slot = driver.find_elements(
        By.XPATH, '//*[@aria-label="time_slot_slider" and @value="8"]'
    )
    start_time_slot_move_to = driver.find_elements(By.XPATH, '//*[@data-index="3"]')

    # drag the start of the slider from 8 to 3
    print('start_time_slot', start_time_slot)
    print('start_time_slot_move_to', start_time_slot_move_to)
    ActionChains(driver).drag_and_drop(
        start_time_slot[0], start_time_slot_move_to[0]
    ).perform()

    driver.wait_for_xpath('//*[@aria-label="time_slot_slider" and @value="3"]')

    # test inverting the timeslot
    time_slot_invert = driver.wait_for_xpath(
        '//*[@label="Invert" and contains(@class, "MuiCheckbox-root")]'
    )
    driver.scroll_to_element_and_click(time_slot_invert)

    driver.wait_for_xpath('//*[@label="Invert" and contains(@class,"Mui-checked")]')

    driver.wait_for_xpath(
        '//*[contains(@class, "MuiSlider-root") and contains(@class, "MuiSlider-trackInverted")]'
    )

    # reload profile to see if the settings were saved
    driver.get(f'/become_user/{user.id}')
    driver.get("/profile")

    driver.wait_for_xpath(
        '//*[@name="mention"]/../../span[contains(@class,"Mui-checked")]'
    )

    mention_settings = driver.wait_for_xpath(
        '//*[@name="notification_settings_button_mention"]'
    )
    driver.scroll_to_element_and_click(mention_settings)

    driver.wait_for_xpath(
        '//*[@name="email" and contains(@class, "MuiSwitch-input")]/../../span[contains(@class,"Mui-checked")]'
    )
    driver.wait_for_xpath(
        '//*[@name="slack" and contains(@class, "MuiSwitch-input")]/../../span[contains(@class,"Mui-checked")]'
    )
    driver.wait_for_xpath(
        '//*[@name="sms" and contains(@class, "MuiSwitch-input")]/../../span[contains(@class,"Mui-checked")]'
    )
    driver.wait_for_xpath(
        '//*[@name="on_shift_sms" and contains(@class, "MuiSwitch-input")]/../../span[contains(@class,"Mui-checked")]'
    )
    driver.wait_for_xpath(
        '//*[@name="time_slot_sms" and contains(@class, "MuiSwitch-input")]/../../span[contains(@class,"Mui-checked")]'
    )

    driver.wait_for_xpath('//*[@aria-label="time_slot_slider" and @value="3"]')
    driver.wait_for_xpath('//*[@aria-label="time_slot_slider" and @value="20"]')

    driver.wait_for_xpath(
        '//*[contains(@class, "MuiSlider-root") and contains(@class, "MuiSlider-trackInverted")]'
    )
