import os
import time
import uuid

import pytest
import requests
from playwright.sync_api import expect

from baselayer.app.config import load_config
from skyportal.tests import api

cfg = load_config()

tach_isonline = False
try:
    response = requests.get(
        "https://heasarc.gsfc.nasa.gov/wsgi-scripts/tach/gcn_v2/tach.wsgi/", timeout=5
    )
    response.raise_for_status()
except Exception:
    pass
else:
    tach_isonline = True


def get_summary(page, user, group, showSources, showGalaxies, showObservations):
    page.goto(f"/become_user/{user.id}")
    page.goto("/gcn_events/2019-08-14T21:10:39")

    page.locator('//button[@name="gcn_summary"]').first.click()

    page.locator('//*[@aria-labelledby="group-select"]').first.click()
    page.locator(f'//li[contains(., "{group.name}")]').first.click()

    if showSources is True:
        page.locator('//*[@label="Show Sources"]').first.click()
    if showGalaxies is True:
        page.locator('//*[@label="Show Galaxies"]').first.click()
    if showObservations is True:
        page.locator('//*[@label="Show Observations"]').first.click()

    page.locator('//button[contains(.,"Get Summary")]').first.click()

    expect(page.locator('//textarea[@id="text"]').first).to_be_visible(timeout=60000)
    expect(
        page.locator('//textarea[contains(.,"TITLE: GCN SUMMARY")]').first
    ).to_be_visible(timeout=60000)

    with page.expect_download():
        page.locator('//button[contains(.,"Download")]').first.click()


@pytest.mark.flaky(reruns=3)
@pytest.mark.skipif(not tach_isonline, reason="GCN TACH is not online")
def test_gcn_tach(page, super_admin_user, super_admin_token):
    datafile = f"{os.path.dirname(__file__)}/../data/GRB180116A_Fermi_GBM_Gnd_Pos.xml"
    with open(datafile, "rb") as fid:
        payload = fid.read()
    event_data = {"xml": payload}

    dateobs = "2018-01-16T00:36:53"
    status, data = api("GET", f"gcn_event/{dateobs}", token=super_admin_token)
    if status == 404:
        status, data = api(
            "POST", "gcn_event", data=event_data, token=super_admin_token
        )
        assert status == 200
        assert data["status"] == "success"

    for n_times in range(26):
        status, data = api("GET", f"gcn_event/{dateobs}", token=super_admin_token)
        if data["status"] == "success":
            break
        time.sleep(2)
    assert n_times < 25

    page.goto(f"/become_user/{super_admin_user.id}")
    page.goto(f"/gcn_events/{dateobs}")

    page.locator('//*[@data-testid="right-panel-button"]').first.click()

    page.locator('//*[@data-testid="update-aliases"]').first.click()
    expect(page.locator('//*[contains(., "GRB180116A")]').first).to_be_visible(
        timeout=60000
    )
    expect(page.locator('//*[@name="gcn_triggers-aliases"]/*')).to_have_count(4)

    expect(
        page.locator('//a[contains(text(), "GRB 180116A: Fermi GBM Detection")]').first
    ).to_be_visible()


def test_gcn_allocation_triggers(
    page,
    public_group,
    super_admin_user,
    super_admin_token,
    view_only_user,
):
    datafile = f"{os.path.dirname(__file__)}/../data/GRB180116A_Fermi_GBM_Gnd_Pos.xml"
    with open(datafile, "rb") as fid:
        payload = fid.read()
    event_data = {"xml": payload}

    dateobs = "2018-01-16T00:36:53"
    status, data = api("GET", f"gcn_event/{dateobs}", token=super_admin_token)
    if status == 404:
        status, data = api(
            "POST", "gcn_event", data=event_data, token=super_admin_token
        )
        assert status == 200
        assert data["status"] == "success"

    for n_times in range(26):
        status, data = api("GET", f"gcn_event/{dateobs}", token=super_admin_token)
        if data["status"] == "success":
            break
        time.sleep(2)
    assert n_times < 25

    name = str(uuid.uuid4())
    status, data = api(
        "POST",
        "telescope",
        data={
            "name": name,
            "nickname": name,
            "lat": 0.0,
            "lon": 0.0,
            "elevation": 0.0,
            "diameter": 10.0,
        },
        token=super_admin_token,
    )
    assert status == 200
    assert data["status"] == "success"
    telescope_id = data["data"]["id"]

    instrument_name = str(uuid.uuid4())
    status, data = api(
        "POST",
        "instrument",
        data={
            "name": instrument_name,
            "type": "imager",
            "band": "Optical",
            "filters": ["ztfr"],
            "telescope_id": telescope_id,
            "api_classname": "ZTFAPI",
            "api_classname_obsplan": "ZTFMMAAPI",
            "field_fov_type": "circle",
            "field_fov_attributes": 3.0,
            "sensitivity_data": {
                "ztfr": {
                    "limiting_magnitude": 20.3,
                    "magsys": "ab",
                    "exposure_time": 30,
                    "zeropoint": 26.3,
                }
            },
        },
        token=super_admin_token,
    )
    assert status == 200
    assert data["status"] == "success"
    instrument_id = data["data"]["id"]

    request_data = {
        "group_id": public_group.id,
        "instrument_id": instrument_id,
        "pi": "Shri Kulkarni",
        "hours_allocated": 200,
        "validity_ranges": [
            {
                "start_date": "2021-02-27T00:00:00.000Z",
                "end_date": "3021-07-20T00:00:00.000Z",
            }
        ],
        "proposal_id": "COO-2020A-P01",
        "default_share_group_ids": [public_group.id],
    }

    status, data = api("POST", "allocation", data=request_data, token=super_admin_token)
    assert status == 200
    assert data["status"] == "success"
    allocation_id = data["data"]["id"]

    status, data = api("GET", f"allocation/{allocation_id}", token=super_admin_token)
    assert status == 200
    assert data["status"] == "success"

    # go to the page of the event
    page.goto(f"/become_user/{super_admin_user.id}")
    page.goto(f"/gcn_events/{dateobs}")

    # find the trigger for the allocation
    chip_not_set = f'//div[@id="{instrument_name}_not_set"]'
    expect(page.locator(chip_not_set)).to_have_count(1)
    page.locator(chip_not_set).first.click()

    # check that the allocation trigger is not set
    expect(
        page.locator(
            f'//div[@id="{allocation_id}_current"]/span[contains(., "Not set")]'
        ).first
    ).to_be_visible()

    trigger_state = (
        f'//div[@id="{allocation_id}_triggered"]/span[contains(., "Triggered")]'
    )
    page.locator(trigger_state).first.click()

    # check that the allocation trigger is triggered
    chip_triggered = f'//div[@id="{instrument_name}_triggered"]'
    page.locator(chip_triggered).first.click()

    expect(
        page.locator(
            f'//div[@id="{allocation_id}_current"]/span[contains(., "Triggered")]'
        ).first
    ).to_be_visible()

    # now switch to view only user
    page.goto(f"/become_user/{view_only_user.id}")
    page.goto(f"/gcn_events/{dateobs}")

    expect(page.locator(chip_triggered)).to_have_count(1)
    page.locator(chip_triggered).first.click()

    # we should see an error message
    expect(
        page.locator(
            '//*[text()="You do not have permission to edit this GCN event allocation triggers"]'
        ).first
    ).to_be_visible()
