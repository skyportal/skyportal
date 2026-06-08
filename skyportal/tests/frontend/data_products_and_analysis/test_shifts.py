import os
import time
import uuid
from datetime import date, datetime, timedelta

import numpy as np
import pytest
from playwright.sync_api import expect

from skyportal.tests import api, wait_for_gcn_event, wait_for_localization


def _retype(locator, value):
    """Clear a (possibly pre-filled, controlled) input and type a new value."""
    locator.click()
    locator.press("ControlOrMeta+a")
    locator.press("Delete")
    locator.press_sequentially(value)


@pytest.mark.flaky(reruns=2)
def test_shift(
    public_group,
    super_admin_token,
    super_admin_user,
    user,
    view_only_user,
    shift_admin,
    shift_user,
    page,
):
    name = str(uuid.uuid4())
    start_date = date.today().strftime("%Y-%m-%dT%H:%M:%S")
    end_date = (date.today() + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%S")
    request_data = {
        "name": name,
        "group_id": public_group.id,
        "start_date": start_date,
        "end_date": end_date,
        "description": "the Night Shift",
        "shift_admins": [super_admin_user.id],
    }

    status, data = api("POST", "shifts", data=request_data, token=super_admin_token)
    assert status == 200
    assert data["status"] == "success"

    page.goto(f"/become_user/{super_admin_user.id}")
    page.goto(f"/shifts/{data['data']['id']}")

    expect(page.locator(f'//*/p[contains(.,"{name}")]').first).to_be_visible()

    today_button = '//button[contains(.,"Today")]'
    page.locator(today_button).first.click()

    page.locator('//*/button[@name="add_shift_button"]').first.click()

    form_name = str(uuid.uuid4())
    start_date = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    end_date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%S")

    page.locator('//*[@id="root_name"]').first.fill(form_name)
    page.locator('//*[@id="root_group_id"]').first.click()
    page.locator('//li[contains(text(), "Sitewide Group")]').first.click()
    page.locator('//*[@id="root_required_users_number"]').first.fill("5")
    _retype(page.locator('//*[@id="root_start_date"]').first, start_date)
    _retype(page.locator('//*[@id="root_end_date"]').first, end_date)

    page.locator('//button[@type="submit"]').first.click()

    page.locator(today_button).first.click()

    # check for shift in calendar and click it
    page.locator(
        f'//*[@data-testid="event_shift_name" and contains(text(), "{form_name}")]/..'
    ).first.click()

    # Selecting the shift on the calendar triggers an async fetch that populates
    # the management panel; wait for the panel header to show THIS shift before
    # interacting, otherwise the comment/member actions race the fetch and target
    # a stale shift.
    expect(page.locator(f'//h2[contains(., "{form_name}")]').first).to_be_visible()

    # add a comment to the shift
    page.locator('//*[@id="root_comment"]').first.fill("This is a comment")
    page.locator('//button[@type="submitComment"]').first.click()

    expect(page.locator('//*[contains(text(), "This is a comment")]')).to_have_count(1)

    # delete the comment from the shift
    page.locator('//*[@id="comment"]').first.click()
    page.locator('//*[contains(@name, "deleteCommentButton")]').first.click()

    expect(page.locator('//*[contains(text(), "This is a comment")]')).to_have_count(0)

    remove_members_button_xpath = '//*[@id="remove-members-button"]'
    add_members_button_xpath = '//*[@id="add-members-button"]'

    # add button disabled because no user selected yet
    expect(page.locator(add_members_button_xpath).first).to_be_disabled()

    select_members = '//*[@aria-labelledby="select-members-label"]'
    page.locator(select_members).first.click()
    page.locator(f'//li[@id="select-members"]/*[@id="{user.id}"]').first.click()
    page.keyboard.press("Escape")  # close the multi-select so buttons are clickable

    # remove button disabled because no added user selected yet
    expect(page.locator(remove_members_button_xpath).first).to_be_disabled()

    page.locator(add_members_button_xpath).first.click()
    expect(
        page.locator(f'//*[@data-testid="shift-member-chip-{user.id}"]').first
    ).to_be_visible()

    page.locator(select_members).first.click()
    page.locator(f'//li[@id="select-members"]/*[@id="{user.id}"]').first.click()
    page.locator(
        f'//li[@id="select-members"]/*[@id="{view_only_user.id}"]'
    ).first.click()
    page.keyboard.press("Escape")

    page.locator(add_members_button_xpath).first.click()
    page.locator(remove_members_button_xpath).first.click()

    expect(
        page.locator(f'//*[@data-testid="shift-member-chip-{user.id}"]').first
    ).to_be_hidden()
    expect(
        page.locator(f'//*[@data-testid="shift-member-chip-{view_only_user.id}"]').first
    ).to_be_visible()

    page.locator(select_members).first.click()
    page.locator(
        f'//li[@id="select-members"]/*[@id="{view_only_user.id}"]'
    ).first.click()
    page.keyboard.press("Escape")

    expect(page.locator(add_members_button_xpath).first).to_be_disabled()

    page.locator(remove_members_button_xpath).first.click()

    expect(
        page.locator(f'//*[@data-testid="shift-member-chip-{view_only_user.id}"]').first
    ).to_be_visible()

    leave_button_xpath = '//*[@id="leave_button"]'
    page.locator(leave_button_xpath).first.click()
    expect(page.locator(leave_button_xpath).first).to_be_hidden()

    join_button_xpath = '//*[@id="join_button"]'
    page.locator(join_button_xpath).first.click()
    expect(page.locator(join_button_xpath).first).to_be_hidden()

    page.goto(f"/become_user/{shift_user.id}")
    page.goto("/shifts")

    page.locator(
        '//*[contains(., "Show All Shifts")]/../span[contains(@class, "MuiSwitch-root")]'
    ).first.click()

    shift_on_calendar = (
        f'//*[@data-testid="event_shift_name" and contains(text(), "{name}")]/..'
    )
    page.locator(shift_on_calendar).first.click()

    # Selecting the shift on the calendar triggers an async fetch that populates
    # the management panel; wait for the panel header to show THIS shift before
    # joining. Otherwise the join click races the fetch and is bound to a stale
    # shift, so participating never flips and the join button never hides.
    expect(page.locator(f'//h2[contains(., "{name}")]').first).to_be_visible()

    # joinShift() posts for the redux profile's currentUser.id, which can still
    # be the previous user right after become_user; retry the join (re-selecting
    # the shift to refresh the panel) until shift_user actually lands in the
    # shift, rather than racing a single click against the profile load.
    member_chip = page.locator(
        f'//*[@data-testid="shift-member-chip-{shift_user.id}"]'
    ).first
    for _ in range(10):
        if member_chip.is_visible():
            break
        join_button = page.locator(join_button_xpath).first
        if join_button.is_visible():
            join_button.click()
        else:
            page.locator(shift_on_calendar).first.click()
        page.wait_for_timeout(1500)
    expect(member_chip).to_be_visible()
    expect(page.locator(join_button_xpath).first).to_be_hidden()

    ask_for_replacement_button_xpath = '//*[@id="ask-for-replacement-button"]'
    page.locator(ask_for_replacement_button_xpath).first.click()
    expect(page.locator(ask_for_replacement_button_xpath).first).to_be_hidden()

    # change to another user
    page.goto(f"/become_user/{shift_admin.id}")
    page.goto("/")

    page.locator('//*[@data-testid="notificationsBadge"]').first.click()

    notification_xpath = (
        f'//ul/div/a/p[contains(text(),"needs a replacement for shift: {name}")]'
    )
    page.locator(notification_xpath).first.click()

    page.locator(
        '//*[contains(., "Show All Shifts")]/../span[contains(@class, "MuiSwitch-root")]'
    ).first.click()

    expect(page.locator(shift_on_calendar).first).to_be_visible()
    page.locator(shift_on_calendar).first.click()


def test_shift_summary(
    public_group,
    super_admin_token,
    super_admin_user,
    upload_data_token,
    view_only_token,
    ztf_camera,
    page,
):
    shift_name_1 = str(uuid.uuid4())
    request_data = {
        "name": shift_name_1,
        "group_id": public_group.id,
        "start_date": "2018-01-15T12:00:00",
        "end_date": "2018-01-17T12:00:00",
        "description": "Shift during GCN",
        "shift_admins": [super_admin_user.id],
    }

    status, data = api("POST", "shifts", data=request_data, token=super_admin_token)
    assert status == 200
    assert data["status"] == "success"
    shift_id = data["data"]["id"]

    status, data = api(
        "GET", f"shifts/{shift_id}", data=request_data, token=super_admin_token
    )
    assert status == 200
    assert data["status"] == "success"

    status, data = api(
        "GET", f"shifts?group_id={public_group.id}", token=super_admin_token
    )
    assert status == 200
    assert data["status"] == "success"

    status, data = api("GET", "gcn_event/2018-01-16T00:36:53", token=super_admin_token)
    if status == 404:
        datafile = (
            f"{os.path.dirname(__file__)}/../../data/GRB180116A_Fermi_GBM_Gnd_Pos.xml"
        )
        with open(datafile, "rb") as fid:
            payload = fid.read()
        data = {"xml": payload}

        status, data = api("POST", "gcn_event", data=data, token=super_admin_token)
        assert status == 200
        assert data["status"] == "success"

        wait_for_gcn_event("2018-01-16T00:36:53", super_admin_token)
    else:
        assert status == 200
        assert data["status"] == "success"

    skymap = "214.74000_28.14000_11.19000"
    localization = wait_for_localization(
        "2018-01-16T00:36:53", skymap, super_admin_token
    )
    assert np.isclose(np.sum(localization["flat_2d"]), 1)

    obj_id = str(uuid.uuid4())
    status, data = api(
        "POST",
        "sources",
        data={"id": obj_id, "ra": 229.9620403, "dec": 34.8442757, "redshift": 3},
        token=upload_data_token,
    )
    assert status == 200

    status, data = api("GET", f"sources/{obj_id}", token=view_only_token)
    assert status == 200

    status, data = api(
        "POST",
        "photometry",
        data={
            "obj_id": obj_id,
            "mjd": 58134.025611226854 + 1,
            "instrument_id": ztf_camera.id,
            "flux": 12.24,
            "fluxerr": 0.031,
            "zp": 25.0,
            "magsys": "ab",
            "filter": "ztfg",
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data["status"] == "success"

    status, data = api("GET", f"sources/{obj_id}", token=view_only_token)
    assert status == 200

    page.goto(f"/become_user/{super_admin_user.id}")
    page.goto(f"/shifts/{shift_id}")

    expect(
        page.locator(
            '//*[@id="gcn_2018-01-16T00:36:53"][contains(.,"2018-01-16T00:36:53")]'
        ).first
    ).to_be_visible()

    page.locator('//*[@id="gcn_list_item_2018-01-16T00:36:53"]').first.click()

    expect(
        page.locator(f"//a[contains(@href, '/source/{obj_id}')]").first
    ).to_be_visible()
