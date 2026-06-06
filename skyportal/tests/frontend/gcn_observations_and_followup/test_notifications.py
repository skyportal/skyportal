import os
import uuid
from datetime import UTC, datetime

import pytest
from playwright.sync_api import expect
from tdtax import __version__, taxonomy

from skyportal.tests import api
from skyportal.tests.frontend.sources_and_observingruns_etc.test_sources import (
    add_comment_and_wait_for_display,
)


def filter_for_value(page, value, last=False):
    input_xpath = "//*[@aria-label='Search']//input"
    if last:
        input_xpath = f"({input_xpath})[last()]"
    page.locator(input_xpath).first.fill(value)


def _enable_switch(page, name):
    """Click a notification preference switch and wait until it's checked."""
    page.locator(f'//*[@name="{name}"]').first.click()
    expect(
        page.locator(
            f'//*[@name="{name}"]/../../span[contains(@class,"Mui-checked")]'
        ).first
    ).to_be_visible()


@pytest.mark.flaky(reruns=2)
def test_mention_generates_notification_then_mark_read_and_delete(
    page, user, public_source
):
    page.goto(f"/become_user/{user.id}")
    page.goto("/profile")

    _enable_switch(page, "mention")

    page.goto(f"/become_user/{user.id}")
    page.goto(f"/source/{public_source.id}")
    expect(page.locator(f'//h6[text()="{public_source.id}"]').first).to_be_visible()

    add_comment_and_wait_for_display(page, f"@{user.username}")

    expect(page.locator("//span[text()='1']").first).to_be_visible()
    page.locator('//*[@data-testid="notificationsButton"]').first.click()
    expect(
        page.locator('//*[text()=" mentioned you in a comment on "]').first
    ).to_be_visible()
    page.locator('//*[contains(@data-testid, "markReadButton")]').first.click()
    expect(page.locator("//button[text()='Mark unread']").first).to_be_visible()
    page.locator(
        '//*[contains(@data-testid, "deleteNotificationButton")]'
    ).first.click()
    expect(
        page.locator('//*[text()=" mentioned you in a comment on "]').first
    ).to_be_hidden()
    expect(page.locator("//*[text()='No notifications']").first).to_be_visible()


@pytest.mark.flaky(reruns=2)
def test_group_admission_requests_notifications(
    page, user, super_admin_user, public_group, public_group2, super_admin_token
):
    status, data = api(
        "POST",
        f"groups/{public_group2.id}/users",
        data={"userID": super_admin_user.id, "admin": True},
        token=super_admin_token,
    )
    assert status == 200

    page.goto(f"/become_user/{user.id}")
    page.goto("/groups")
    expect(page.locator('//h6[text()="My Groups"]').first).to_be_visible()
    filter_for_value(page, public_group2.name)
    page.locator(
        f'//*[@data-testid="requestAdmissionButton{public_group2.id}"]'
    ).first.click()
    expect(
        page.locator(
            f'//*[@data-testid="deleteAdmissionRequestButton{public_group2.id}"]'
        ).first
    ).to_be_visible()
    page.goto(f"/become_user/{super_admin_user.id}")
    page.goto(f"/group/{public_group2.id}")
    page.locator('//*[@data-testid="notificationsButton"]').first.click()
    expect(
        page.locator('//*[text()="New Group Admission Request from "]').first
    ).to_be_visible()
    page.locator('//*[@data-testid="deleteAllNotificationsButton"]').first.click()
    expect(
        page.locator('//*[text()="New Group Admission Request from "]').first
    ).to_be_hidden()

    filter_for_value(page, user.username, last=True)
    expect(page.locator('//div[text()="pending"]').first).to_be_visible()
    page.locator(f'//*[@data-testid="acceptRequestButton{user.id}"]').first.click()
    expect(page.locator('//div[text()="accepted"]').first).to_be_visible()
    expect(page.locator(f'//a[text()="{user.username}"]').first).to_be_visible()

    page.goto(f"/become_user/{user.id}")
    page.goto("/")
    page.locator('//*[@data-testid="notificationsButton"]').first.click()
    expect(page.locator('//em[text()="accepted"]').first).to_be_visible()
    expect(page.locator(f'//em[text()="{public_group2.name}"]').first).to_be_visible()


@pytest.mark.flaky(reruns=3)
def test_comment_on_favorite_source_triggers_notification(
    page, user, user2, public_source
):
    page.goto(f"/become_user/{user.id}")
    page.goto("/profile")

    _enable_switch(page, "favorite_sources")
    _enable_switch(page, "favorite_sources_new_comments")
    _enable_switch(page, "favorite_sources_new_bot_comments")

    page.goto(f"/source/{public_source.id}")
    page.locator(
        f'//*[@data-testid="favorites-exclude_{public_source.id}"]'
    ).first.click()
    expect(
        page.locator(f'//*[@data-testid="favorites-include_{public_source.id}"]').first
    ).to_be_visible()

    page.goto(f"/become_user/{user2.id}")
    page.goto(f"/source/{public_source.id}")
    comment_text = str(uuid.uuid4())
    add_comment_and_wait_for_display(page, comment_text)

    page.goto(f"/become_user/{user.id}")
    page.goto("/")
    expect(page.locator(f"//p[text()='{comment_text}']").first).to_be_visible()
    page.locator('//*[@data-testid="notificationsButton"]').first.click()
    expect(
        page.locator('//*[contains(text(), "New comment on favorite source")]').first
    ).to_be_visible()


@pytest.mark.flaky(reruns=3)
def test_classification_on_favorite_source_triggers_notification(
    page, user, public_source, public_group, taxonomy_token, classification_token
):
    status, data = api(
        "POST",
        "taxonomy",
        data={
            "name": "test taxonomy" + str(uuid.uuid4()),
            "hierarchy": taxonomy,
            "group_ids": [public_group.id],
            "provenance": f"tdtax_{__version__}",
            "version": __version__,
            "isLatest": True,
        },
        token=taxonomy_token,
    )
    assert status == 200
    taxonomy_id = data["data"]["taxonomy_id"]

    page.goto(f"/become_user/{user.id}")
    page.goto("/profile")

    _enable_switch(page, "favorite_sources")
    _enable_switch(page, "favorite_sources_new_classifications")
    _enable_switch(page, "favorite_sources_new_ml_classifications")

    page.goto(f"/source/{public_source.id}")
    page.locator(
        f'//*[@data-testid="favorites-exclude_{public_source.id}"]'
    ).first.click()
    expect(
        page.locator(f'//*[@data-testid="favorites-include_{public_source.id}"]').first
    ).to_be_visible()

    status, data = api(
        "POST",
        "classification",
        data={
            "obj_id": public_source.id,
            "classification": "AGN",
            "taxonomy_id": taxonomy_id,
            "probability": 1.0,
            "group_ids": [public_group.id],
            "ml": True,
        },
        token=classification_token,
    )
    assert status == 200

    page.goto(f"/become_user/{user.id}")
    page.goto("/")
    expect(page.locator("//span[text()='1']").first).to_be_visible()
    page.locator('//*[@data-testid="notificationsButton"]').first.click()
    expect(
        page.locator(
            '//*[contains(text(), "New classification on favorite source")]'
        ).first
    ).to_be_visible()


@pytest.mark.flaky(reruns=3)
def test_spectra_on_favorite_source_triggers_notification(
    page, user, public_source, lris, upload_data_token, public_group
):
    page.goto(f"/become_user/{user.id}")
    page.goto("/profile")

    _enable_switch(page, "favorite_sources")
    _enable_switch(page, "favorite_sources_new_spectra")

    page.goto(f"/source/{public_source.id}")
    page.locator(
        f'//*[@data-testid="favorites-exclude_{public_source.id}"]'
    ).first.click()
    expect(
        page.locator(f'//*[@data-testid="favorites-include_{public_source.id}"]').first
    ).to_be_visible()

    status, data = api(
        "POST",
        "spectrum",
        data={
            "obj_id": public_source.id,
            "observed_at": str(datetime.now(UTC)),
            "instrument_id": lris.id,
            "wavelengths": [664, 665, 666],
            "fluxes": [234.2, 232.1, 235.3],
            "group_ids": [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data["status"] == "success"

    page.goto(f"/become_user/{user.id}")
    page.goto("/")
    expect(page.locator("//span[text()='1']").first).to_be_visible()
    page.locator('//*[@data-testid="notificationsButton"]').first.click()
    expect(
        page.locator('//*[contains(text(), "New spectrum on favorite source")]').first
    ).to_be_visible()


def test_new_classification_on_source_triggers_notification(
    page, user, public_source, public_group, taxonomy_token, classification_token
):
    status, data = api(
        "POST",
        "taxonomy",
        data={
            "name": "test taxonomy" + str(uuid.uuid4()),
            "hierarchy": taxonomy,
            "group_ids": [public_group.id],
            "provenance": f"tdtax_{__version__}",
            "version": __version__,
            "isLatest": True,
        },
        token=taxonomy_token,
    )
    assert status == 200
    taxonomy_id = data["data"]["taxonomy_id"]

    page.goto(f"/become_user/{user.id}")
    page.goto("/profile")

    _enable_switch(page, "sources")

    page.locator("//*[@id='classifications-select']").first.click()
    page.locator('//li[@data-value="AGN"]').first.click()
    page.keyboard.press("Escape")

    page.locator(
        '//*[@data-testid="addShortcutButton" and contains(., "Update")]'
    ).first.click()
    expect(
        page.locator('//*[contains(text(), "Sources classifications updated")]').first
    ).to_be_visible()

    status, data = api(
        "POST",
        "classification",
        data={
            "obj_id": public_source.id,
            "classification": "AGN",
            "taxonomy_id": taxonomy_id,
            "probability": 1.0,
            "group_ids": [public_group.id],
        },
        token=classification_token,
    )
    assert status == 200

    page.goto(f"/become_user/{user.id}")
    page.goto("/")
    expect(page.locator("//span[text()='1']").first).to_be_visible()
    page.locator('//*[@data-testid="notificationsButton"]').first.click()
    expect(
        page.locator('//*[contains(text(), "New classification")]').first
    ).to_be_visible()


@pytest.mark.flaky(reruns=3)
def test_new_spectra_on_source_triggers_notification(
    page, user, public_source, lris, upload_data_token, public_group
):
    page.goto(f"/become_user/{user.id}")
    page.goto("/profile")

    _enable_switch(page, "sources")
    _enable_switch(page, "sources_new_spectra")

    page.locator("//*[@id='groups-select']").first.click()
    page.locator(f'//li[contains(text(), "{public_group.name}")]').first.click()
    page.keyboard.press("Escape")

    page.locator(
        '//*[@data-testid="addShortcutButton" and contains(., "Update")]'
    ).first.click()

    status, data = api(
        "POST",
        "spectrum",
        data={
            "obj_id": public_source.id,
            "observed_at": str(datetime.now(UTC)),
            "instrument_id": lris.id,
            "wavelengths": [664, 665, 666],
            "fluxes": [234.2, 232.1, 235.3],
            "group_ids": [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data["status"] == "success"

    page.goto(f"/become_user/{user.id}")
    page.goto("/")
    expect(page.locator("//span[text()='1']").first).to_be_visible()
    page.locator('//*[@data-testid="notificationsButton"]').first.click()
    expect(
        page.locator('//*[contains(text(), "New spectrum for source")]').first
    ).to_be_visible()


@pytest.mark.flaky(reruns=2)
def test_new_gcn_event_triggers_notification(page, user, super_admin_token):
    page.goto(f"/become_user/{user.id}")
    page.goto("/profile")

    _enable_switch(page, "gcn_events")

    page.locator('//*[@id="new-gcn-notification-profile"]').first.click()

    page.locator('//*[@id="GcnNotificationNameInput"]').first.fill("test")

    page.locator('//*[@aria-labelledby="selectGcns"]').first.click()
    page.locator('//li[@data-value="FERMI_GBM_GND_POS"]').first.click()
    page.keyboard.press("Escape")

    page.locator(
        '//*[@data-testid="addShortcutButton" and contains(., "Create")]'
    ).first.click()
    expect(
        page.locator('//*[contains(text(), "Gcn notice preferences updated")]').first
    ).to_be_visible()

    datafile = (
        f"{os.path.dirname(__file__)}/../../data/GRB180116A_Fermi_GBM_Gnd_Pos.xml"
    )
    with open(datafile, "rb") as fid:
        payload = fid.read()
    data = {"xml": payload}

    status, data = api("POST", "gcn_event", data=data, token=super_admin_token)
    assert status == 200
    assert data["status"] == "success"

    page.goto(f"/become_user/{user.id}")
    page.goto("/")
    expect(page.locator("//span[text()='1']").first).to_be_visible()
    page.locator('//*[@data-testid="notificationsButton"]').first.click()
    expect(page.locator('//*[contains(text(), "New GCN Event")]').first).to_be_visible()


def test_notification_setting_select(page, user):
    page.goto(f"/become_user/{user.id}")
    page.goto("/profile")

    _enable_switch(page, "mention")

    page.locator('//*[@name="notification_settings_button_mention"]').first.click()

    def _enable_setting(name):
        page.locator(
            f'//*[@name="{name}" and contains(@class, "MuiSwitch-input")]'
        ).first.click()
        expect(
            page.locator(
                f'//*[@name="{name}" and contains(@class, "MuiSwitch-input")]/../../span[contains(@class,"Mui-checked")]'
            ).first
        ).to_be_visible()

    _enable_setting("email")
    _enable_setting("slack")
    # sms toggle reveals further sms options
    page.locator('//*[@name="sms"]').first.click()
    expect(
        page.locator(
            '//*[@name="sms" and contains(@class, "MuiSwitch-input")]/../../span[contains(@class,"Mui-checked")]'
        ).first
    ).to_be_visible()
    _enable_setting("on_shift_sms")
    _enable_setting("time_slot_sms")

    expect(
        page.locator('//*[@aria-label="time_slot_slider" and @value="8"]').first
    ).to_be_visible()
    expect(
        page.locator('//*[@aria-label="time_slot_slider" and @value="20"]').first
    ).to_be_visible()

    # Move the start slider 8H -> 3H. Range inputs respond reliably to arrow
    # keys (drag-and-drop on a slider thumb is flaky), so focus and step down.
    slider = page.locator(
        '//*[@aria-label="time_slot_slider" and @data-index="0"]'
    ).first
    slider.focus()
    for _ in range(5):
        slider.press("ArrowLeft")

    expect(
        page.locator('//*[@aria-label="time_slot_slider" and @value="3"]').first
    ).to_be_visible()

    # test inverting the timeslot
    page.locator(
        '//*[@label="Invert" and contains(@class, "MuiCheckbox-root")]'
    ).first.click()
    expect(
        page.locator('//*[@label="Invert" and contains(@class,"Mui-checked")]').first
    ).to_be_visible()
    expect(
        page.locator(
            '//*[contains(@class, "MuiSlider-root") and contains(@class, "MuiSlider-trackInverted")]'
        ).first
    ).to_be_visible()

    # reload profile to see if the settings were saved
    page.goto(f"/become_user/{user.id}")
    page.goto("/profile")

    expect(
        page.locator(
            '//*[@name="mention"]/../../span[contains(@class,"Mui-checked")]'
        ).first
    ).to_be_visible()

    page.locator('//*[@name="notification_settings_button_mention"]').first.click()

    for name in ("email", "slack", "sms", "on_shift_sms", "time_slot_sms"):
        expect(
            page.locator(
                f'//*[@name="{name}" and contains(@class, "MuiSwitch-input")]/../../span[contains(@class,"Mui-checked")]'
            ).first
        ).to_be_visible()

    expect(
        page.locator('//*[@aria-label="time_slot_slider" and @value="3"]').first
    ).to_be_visible()
    expect(
        page.locator('//*[@aria-label="time_slot_slider" and @value="20"]').first
    ).to_be_visible()
    expect(
        page.locator(
            '//*[contains(@class, "MuiSlider-root") and contains(@class, "MuiSlider-trackInverted")]'
        ).first
    ).to_be_visible()
