import os
import time
import uuid

import numpy as np
import pandas as pd
import pytest
import requests
from playwright.sync_api import expect

from baselayer.app.config import load_config
from skyportal.tests import api, wait_for_gcn_event, wait_for_localization
from skyportal.tests.external.test_moving_objects import (
    add_telescope_and_instrument,
    remove_telescope_and_instrument,
)

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


@pytest.mark.flaky(reruns=3)
@pytest.mark.skipif(not tach_isonline, reason="GCN TACH is not online")
def test_gcn_tach(page, super_admin_user, super_admin_token):
    datafile = (
        f"{os.path.dirname(__file__)}/../../data/GRB180116A_Fermi_GBM_Gnd_Pos.xml"
    )
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

    wait_for_gcn_event(dateobs, super_admin_token)

    page.goto(f"/become_user/{super_admin_user.id}")
    page.goto(f"/gcn_events/{dateobs}")

    page.locator('//*[@data-testid="right-panel-button"]').first.click()

    page.locator('//*[@data-testid="update-aliases"]').first.click()
    expect(page.locator('//*[contains(., "GRB180116A")]').first).to_be_visible()
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
    datafile = (
        f"{os.path.dirname(__file__)}/../../data/GRB180116A_Fermi_GBM_Gnd_Pos.xml"
    )
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

    wait_for_gcn_event(dateobs, super_admin_token)

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


def test_filter_by_gcnevent(
    page,
    user,
    super_admin_token,
    view_only_token,
    ztf_camera,
    upload_data_token,
):
    datafile = f"{os.path.dirname(__file__)}/../../../../data/GW190814.xml"
    with open(datafile, "rb") as fid:
        payload = fid.read()
    event_data = {"xml": payload}

    dateobs = "2019-08-14T21:10:39"
    status, data = api("GET", f"gcn_event/{dateobs}", token=super_admin_token)

    if status == 404:
        status, data = api(
            "POST", "gcn_event", data=event_data, token=super_admin_token
        )
        assert status == 200
        assert data["status"] == "success"

    # wait for event to load
    wait_for_gcn_event("2019-08-14T21:10:39", super_admin_token)

    # wait for the localization to load
    localization = wait_for_localization(
        "2019-08-14T21:10:39", "LALInference.v1.fits.gz", super_admin_token
    )
    assert np.isclose(np.sum(localization["flat_2d"]), 1)

    obj_id = str(uuid.uuid4())
    status, data = api(
        "POST",
        "sources",
        data={
            "id": obj_id,
            "ra": 24.6258,
            "dec": -32.9024,
            "redshift": 3,
        },
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
            "mjd": 58709 + 1,
            "instrument_id": ztf_camera.id,
            "flux": 12.24,
            "fluxerr": 0.031,
            "zp": 25.0,
            "magsys": "ab",
            "filter": "ztfg",
            "ra": 24.6258,
            "dec": -32.9024,
            "ra_unc": 0.01,
            "dec_unc": 0.01,
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data["status"] == "success"

    notinevent_obj_id = str(uuid.uuid4())

    status, data = api(
        "POST",
        "sources",
        data={
            "id": notinevent_obj_id,
            "ra": 40,
            "dec": -10,
            "redshift": 3,
        },
        token=upload_data_token,
    )
    assert status == 200

    page.goto(f"/become_user/{user.id}")
    page.goto("/sources")

    page.locator("//button[@data-testid='Filter Table-iconButton']").first.click()

    page.locator('//input[@name="startDate"]').first.fill("2019-08-14T21:10:39")
    page.locator('//input[@name="endDate"]').first.fill("2019-08-21T21:10:39")

    page.locator(
        '//*[@role="combobox" and (@aria-labelledby="gcnEventSelectLabel" or @id="gcnEventSelectLabel")]'
    ).first.click()
    page.locator('//li[contains(text(), "2019-08-14T21:10:39")]').first.click()

    page.locator(
        '//*[@role="combobox" and (@aria-labelledby="localizationSelectLabel" or @id="localizationSelectLabel")]'
    ).first.click()
    page.locator('//li[contains(text(), "LALInference.v1.fits.gz")]').first.click()

    page.locator("//button[text()='Submit']").first.click()

    # The source that is not in the event should disappear
    expect(
        page.locator(f'//a[@data-testid="{notinevent_obj_id}"]').first
    ).to_be_hidden()

    # Should see the posted source
    expect(page.locator(f'//a[@data-testid="{obj_id}"]').first).to_be_visible()


def test_gcn_summary_observations(
    super_admin_user, super_admin_token, view_only_token, public_group
):
    datafile = f"{os.path.dirname(__file__)}/../../../../data/GW190814.xml"
    with open(datafile, "rb") as fid:
        payload = fid.read()
    event_data = {"xml": payload}

    dateobs = "2019-08-14T21:10:39"
    status, data = api("GET", f"gcn_event/{dateobs}", token=super_admin_token)

    if status == 404:
        status, data = api(
            "POST", "gcn_event", data=event_data, token=super_admin_token
        )
        assert status == 200
        assert data["status"] == "success"

        gcnevent_id = data["data"]["gcnevent_id"]
    else:
        gcnevent_id = data["data"]["id"]

    # wait for event to load
    wait_for_gcn_event(dateobs, super_admin_token)

    # wait for the localization to load
    localization = wait_for_localization(
        "2019-08-14T21:10:39", "LALInference.v1.fits.gz", super_admin_token
    )
    assert np.isclose(np.sum(localization["flat_2d"]), 1)
    localization_id = localization["id"]

    telescope_id, instrument_id, telescope_name, instrument_name = (
        add_telescope_and_instrument("ZTF", super_admin_token, list(range(199, 204)))
    )

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
    }

    status, data = api("POST", "allocation", data=request_data, token=super_admin_token)
    assert status == 200
    assert data["status"] == "success"
    allocation_id = data["data"]["id"]

    queue_name = str(uuid.uuid4())
    request_data = {
        "allocation_id": allocation_id,
        "gcnevent_id": gcnevent_id,
        "localization_id": localization_id,
        "payload": {
            "start_date": "2019-08-15 08:18:05",
            "end_date": "2019-08-20 08:18:05",
            "filter_strategy": "block",
            "schedule_strategy": "tiling",
            "schedule_type": "greedy_slew",
            "exposure_time": 300,
            "field_ids": [200, 201, 202],
            "filters": "ztfr",
            "maximum_airmass": 2.0,
            "integrated_probability": 100,
            "minimum_time_difference": 30,
            "queue_name": queue_name,
            "program_id": "Partnership",
            "subprogram_name": "GRB",
        },
    }

    status, data = api(
        "POST", "observation_plan", data=request_data, token=super_admin_token
    )
    assert status == 200
    assert data["status"] == "success"

    # wait for the observation plan to finish loading
    time.sleep(15)
    n_retries = 0
    while n_retries < 10:
        try:
            status, data = api(
                "GET",
                "observation_plan",
                params={"includePlannedObservations": "true"},
                token=super_admin_token,
            )
            assert status == 200
            assert data["status"] == "success"

            data = [
                d
                for d in data["data"]["requests"]
                if d["gcnevent_id"] == gcnevent_id
                and d["allocation_id"] == allocation_id
            ]
            assert len(data) == 1
            assert data[0]["payload"] == request_data["payload"]
            assert len(data[0]["observation_plans"]) == 1
            break
        except AssertionError:
            n_retries = n_retries + 1
            time.sleep(3)

        assert n_retries < 10

    datafile = f"{os.path.dirname(__file__)}/../../../../data/sample_observation_gw.csv"
    data = {
        "telescopeName": telescope_name,
        "instrumentName": instrument_name,
        "observationData": pd.read_csv(datafile).to_dict(orient="list"),
    }

    status, data = api("POST", "observation", data=data, token=super_admin_token)

    assert status == 200
    assert data["status"] == "success"

    # wait for the executed observations to populate

    params = {
        "telescopeName": telescope_name,
        "instrumentName": instrument_name,
        "startDate": "2019-08-13 08:18:05",
        "endDate": "2019-08-19 08:18:05",
    }
    nretries = 0
    observations_loaded = False
    while not observations_loaded and nretries < 25:
        try:
            status, data = api(
                "GET", "observation", params=params, token=super_admin_token
            )
            assert status == 200
            data = data["data"]
            assert len(data["observations"]) >= 9
            observations_loaded = True
        except AssertionError:
            nretries = nretries + 1
            time.sleep(2)

    assert nretries < 25
    assert status == 200
    assert observations_loaded is True

    # get the gcn event summary
    data = {
        "title": "gcn summary",
        "subject": "follow-up",
        "userIds": super_admin_user.id,
        "groupId": public_group.id,
        "startDate": "2019-08-13 08:18:05",
        "endDate": "2019-08-19 08:18:05",
        "localizationCumprob": 0.99,
        "showSources": False,
        "showGalaxies": False,
        "showObservations": True,
        "noText": False,
    }

    status, data = api(
        "POST",
        "gcn_event/2019-08-14T21:10:39/summary",
        data=data,
        token=super_admin_token,
    )
    assert status == 200
    summary_id = data["data"]["id"]

    nretries = 0
    summaries_loaded = False
    while nretries < 40:
        status, data = api(
            "GET",
            f"gcn_event/2019-08-14T21:10:39/summary/{summary_id}",
            token=view_only_token,
            params=params,
        )
        if status == 404:
            nretries = nretries + 1
            time.sleep(5)
        if status == 200:
            data = data["data"]
            if data["text"] == "pending":
                nretries = nretries + 1
                time.sleep(5)
            else:
                summaries_loaded = True
                break

    assert nretries < 40
    assert summaries_loaded
    text = data["text"]
    lines = list(filter(None, text.split("\n")))

    # The summary is now markdown-formatted (lines prefixed with "##"/"####" and
    # the author + "on behalf of" merged onto one line), so check by content
    # rather than fixed line indices.
    assert "TITLE: GCN SUMMARY" in text
    assert "SUBJECT: Follow-up" in text
    assert "DATE" in text
    assert (
        f"FROM: {super_admin_user.first_name} {super_admin_user.last_name} at ... <{super_admin_user.contact_email}>"
        in text
    )
    assert (
        f"{super_admin_user.first_name.upper()[0]}. {super_admin_user.last_name} (...)"
        in text
    )
    assert f"on behalf of the {public_group.name} group:" in text

    # obs
    assert "Observations:" in text

    # The observations-summary prose includes counts (images, square degrees,
    # probability %) computed from whatever observations are in the localization,
    # which vary as other tests add observations to the shared DB. Assert the
    # stable structure rather than the exact numbers.
    assert (
        "We observed the localization region of LVC trigger 2019-08-14T21:10:39" in text
    )
    assert "covering ztfr bands" in text
    # The summary is markdown now, so this phrase is wrapped in bold (...region**.)
    # rather than ending in a bare period -- match without the trailing punctuation.
    assert "of the probability enclosed in the localization region" in text

    # the observations table header row lists the columns
    header_row = next((line for line in lines if "T-T0 (hr)" in line), None)
    assert header_row is not None
    for col in ("T-T0 (hr)", "mjd", "ra", "dec", "filter", "exposure", "limmag (ab)"):
        assert col in header_row

    remove_telescope_and_instrument(telescope_id, instrument_id, super_admin_token)
