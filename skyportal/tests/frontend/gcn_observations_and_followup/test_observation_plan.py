import os
import time
import uuid

import pandas as pd
import pytest
from playwright.sync_api import expect

from skyportal.tests import api
from skyportal.tests.external.test_moving_objects import (
    add_telescope_and_instrument,
    remove_telescope_and_instrument,
)


@pytest.mark.flaky(reruns=3)
def test_gcnevents_observations(
    page, user, super_admin_token, upload_data_token, view_only_token, ztf_camera
):
    datafile = f"{os.path.dirname(__file__)}/../../data/GW190425_initial.xml"
    with open(datafile, "rb") as fid:
        payload = fid.read()
    event_data = {"xml": payload}

    dateobs = "2019-04-25T08:18:05"
    status, data = api("GET", f"gcn_event/{dateobs}", token=super_admin_token)
    if status == 404:
        status, data = api(
            "POST", "gcn_event", data=event_data, token=super_admin_token
        )
        assert status == 200
        assert data["status"] == "success"

    telescope_id, instrument_id, telescope_name, instrument_name = (
        add_telescope_and_instrument("ZTF", super_admin_token, list(range(5)))
    )

    datafile = (
        f"{os.path.dirname(__file__)}/../../../../data/sample_observation_data.csv"
    )
    data = {
        "telescopeName": telescope_name,
        "instrumentName": instrument_name,
        "observationData": pd.read_csv(datafile).to_dict(orient="list"),
    }
    status, data = api("POST", "observation", data=data, token=super_admin_token)
    assert status == 200
    assert data["status"] == "success"

    nretries = 0
    observations_loaded = False
    while not observations_loaded and nretries < 5:
        try:
            status, data = api(
                "GET",
                "observation",
                params={
                    "startDate": "2019-04-25T08:18:05",
                    "endDate": "2019-04-27T08:18:05",
                },
                token=super_admin_token,
            )
            assert status == 200
            data = data["data"]
            assert len(data["observations"]) == 10
            observations_loaded = True
        except AssertionError:
            nretries = nretries + 1
            time.sleep(3)

    page.goto(f"/become_user/{user.id}")
    page.goto("/gcn_events/2019-04-25T08:18:05")

    expect(page.locator('//*[text()="190425 08:18:05"]').first).to_be_visible()
    expect(page.locator('//*[text()="LVC"]').first).to_be_visible()
    expect(page.locator('//*[text()="BNS"]').first).to_be_visible()

    # test modify sources form
    page.locator('//*[@id="root_localizationCumprob"]').first.fill("1.00")

    page.locator('//div[@id="root_queryList"]').first.click()
    page.locator('//li[contains(text(), "observations")]').first.click()
    page.keyboard.press("Escape")

    submit_button_xpath = (
        '//div[@data-testid="gcnsource-selection-form"]//button[@type="submit"]'
    )
    page.locator(submit_button_xpath).first.click()

    page.locator('//button[contains(., "Observations")]').first.click()

    remove_telescope_and_instrument(telescope_id, instrument_id, super_admin_token)


def test_observationplan_request(
    page, super_admin_user, super_admin_token, public_group
):
    datafile = f"{os.path.dirname(__file__)}/../../data/GW190425_initial.xml"
    with open(datafile, "rb") as fid:
        payload = fid.read()
    event_data = {"xml": payload}

    dateobs = "2019-04-25T08:18:05"
    status, data = api("GET", f"gcn_event/{dateobs}", token=super_admin_token)
    if status == 404:
        status, data = api(
            "POST", "gcn_event", data=event_data, token=super_admin_token
        )
        assert status == 200
        assert data["status"] == "success"

    telescope_id, instrument_id, _, instrument_name = add_telescope_and_instrument(
        "ZTF", super_admin_token, list(range(5))
    )

    status, data = api(
        "POST",
        "allocation",
        data={
            "group_id": public_group.id,
            "instrument_id": instrument_id,
            "hours_allocated": 100,
            "validity_ranges": [
                {
                    "start_date": "2021-02-27T00:00:00.000Z",
                    "end_date": "3021-07-20T00:00:00.000Z",
                }
            ],
            "pi": "Ed Hubble",
            "types": ["triggered", "forced_photometry", "observation_plan"],
            "_altdata": '{"access_token": "testtoken"}',
        },
        token=super_admin_token,
    )
    assert status == 200
    assert data["status"] == "success"
    catalog_name = str(uuid.uuid4())
    galaxy_name = str(uuid.uuid4())
    data = {
        "catalog_name": catalog_name,
        "catalog_data": {"name": [galaxy_name], "ra": [228.5], "dec": [35.5]},
    }
    status, data = api("POST", "galaxy_catalog", data=data, token=super_admin_token)
    assert status == 200
    assert data["status"] == "success"

    page.goto(f"/become_user/{super_admin_user.id}")
    page.goto("/gcn_events/2019-04-25T08:18:05")

    nretries = 0
    while nretries < 5:
        try:
            expect(page.locator('//*[text()="190425 08:18:05"]').first).to_be_visible()
            break
        except AssertionError:
            page.reload()
            nretries = nretries + 1

    expect(page.locator('//*[text()="LVC"]').first).to_be_visible()
    expect(page.locator('//*[text()="BNS"]').first).to_be_visible()

    page.locator("//*[@id='observationplan-header']").first.click()

    page.locator(
        '//*[contains(@aria-labelledby, "allocationSelectLabel")]'
    ).first.click()
    page.locator(
        f'//li[contains(text(), "{instrument_name}")][contains(text(), "{public_group.name}")]'
    ).first.click()
    page.keyboard.press("Escape")

    # The observation-plan form's default "filters" is ztfg,ztfr,ztfg, but the
    # test instrument only has the ztfr filter, so the form's subset validation
    # fails and Add to Queue won't submit. Replace it with a valid subset.
    page.locator(
        '//div[@data-testid="observationplan-request-form"]//*[@id="root_filters"]'
    ).first.fill("ztfr")

    page.locator('//button[contains(., "Add to Queue")]').first.click()
    page.locator('//button[contains(., "Generate Observation Plans")]').first.click()

    time.sleep(30)

    expect(
        page.locator(f"//*[@data-testid='{instrument_name}-requests-header']").first
    ).to_be_visible(timeout=30000)
    page.locator(f"//*[@data-testid='{instrument_name}-requests-header']").first.click()
    expect(
        page.locator(
            f'//div[contains(@data-testid, "{instrument_name}_observationplanRequestsTable")]//div[contains(., "ztfr")]'
        ).first
    ).to_be_visible(timeout=15000)
    expect(
        page.locator(
            f'//div[contains(@data-testid, "{instrument_name}_observationplanRequestsTable")]//div[contains(., "complete")]'
        ).first
    ).to_be_visible(timeout=15000)

    status, data = api("GET", "observation_plan", token=super_admin_token)
    assert status == 200

    observation_plan_request_id = data["data"]["requests"][-1]["observation_plans"][0][
        "observation_plan_request_id"
    ]
    page.locator(
        f'//a[contains(@data-testid, "gcnRequest_{observation_plan_request_id}")]'
    ).first.click()
    page.locator(
        f'//button[contains(@data-testid, "treasuremapRequest_{observation_plan_request_id}")]'
    ).first.click()
    # Downloading a plan is now a "Download" button that opens a ZTF/Rubin menu.
    page.locator('//button[normalize-space(.)="Download"]').first.click()
    page.locator('//li[contains(., "ZTF compatible")]').first.click()
    page.locator(
        f'//button[contains(@data-testid, "addObservingRunButton_{observation_plan_request_id}")]'
    ).first.click()
    page.locator(
        f'//button[contains(@data-testid, "observingRunRequest_{observation_plan_request_id}")]'
    ).first.click()
    page.locator(
        f'//button[contains(@data-testid, "deleteRequest_{observation_plan_request_id}")]'
    ).first.click()

    expect(
        page.locator(f"//*[@data-testid='{instrument_name}-requests-header']").first
    ).to_be_hidden()

    remove_telescope_and_instrument(telescope_id, instrument_id, super_admin_token)


@pytest.mark.flaky(reruns=2)
def test_gcn_request(page, user, super_admin_token, public_group):
    datafile = f"{os.path.dirname(__file__)}/../../data/GW190425_initial.xml"
    with open(datafile, "rb") as fid:
        payload = fid.read()
    event_data = {"xml": payload}

    dateobs = "2019-04-25T08:18:05"
    status, data = api("GET", f"gcn_event/{dateobs}", token=super_admin_token)
    if status == 404:
        status, data = api(
            "POST", "gcn_event", data=event_data, token=super_admin_token
        )
        assert status == 200
        assert data["status"] == "success"

    telescope_id, instrument_id, telescope_name, instrument_name = (
        add_telescope_and_instrument("ZTF", super_admin_token, list(range(5)))
    )

    datafile = (
        f"{os.path.dirname(__file__)}/../../../../data/sample_observation_data.csv"
    )
    data = {
        "telescopeName": telescope_name,
        "instrumentName": instrument_name,
        "observationData": pd.read_csv(datafile).to_dict(orient="list"),
    }
    status, data = api("POST", "observation", data=data, token=super_admin_token)
    assert status == 200
    assert data["status"] == "success"

    params = {
        "telescopeName": telescope_name,
        "instrumentName": instrument_name,
        "startDate": "2019-04-25 08:18:05",
        "endDate": "2019-04-28 08:18:05",
        "localizationDateobs": "2019-04-25T08:18:05",
        "localizationName": "bayestar.fits.gz",
        "localizationCumprob": 1.01,
        "returnStatistics": True,
    }

    nretries = 0
    observations_loaded = False
    while not observations_loaded and nretries < 5:
        try:
            status, data = api(
                "GET", "observation", params=params, token=super_admin_token
            )
            assert status == 200
            data = data["data"]
            assert len(data["observations"]) == 10
            observations_loaded = True
        except AssertionError:
            nretries = nretries + 1
            time.sleep(3)

    page.goto(f"/become_user/{user.id}")
    page.goto("/gcn_events/2019-04-25T08:18:05")
    nretries = 0
    while nretries < 5:
        try:
            expect(page.locator('//*[text()="190425 08:18:05"]').first).to_be_visible(
                timeout=20000
            )
            break
        except AssertionError:
            page.reload()
            nretries = nretries + 1
    expect(page.locator('//*[text()="LVC"]').first).to_be_visible()
    expect(page.locator('//*[text()="BNS"]').first).to_be_visible()

    page.locator('//*[@aria-labelledby="localizationSelectLabel"]').first.click()
    page.locator('//li[contains(text(), "bayestar.fits.gz")]').first.click()
    page.locator('//*[@id="root_localizationCumprob"]').first.fill("1.00")

    page.locator('//button[@type="submit"]').first.click()

    page.locator('//*[@aria-labelledby="instrumentSelectLabel"]').first.click()
    page.locator(f'//li[contains(text(), "{instrument_name}")]').first.click()

    remove_telescope_and_instrument(telescope_id, instrument_id, super_admin_token)
