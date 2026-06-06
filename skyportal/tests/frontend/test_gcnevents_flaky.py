import os
import time
import uuid

import numpy as np
import pytest
from playwright.sync_api import expect

from skyportal.tests import api
from skyportal.tests.frontend.test_reminders import (
    post_and_verify_reminder,
)


@pytest.mark.flaky(reruns=2)
def test_gcn_IPN(super_admin_token):
    skymap = f"{os.path.dirname(__file__)}/../data/GRB220617A_IPN_map_hpx.fits.gz"
    dateobs = "2022-06-17T18:31:12"
    tags = ["IPN", "GRB"]

    data = {"dateobs": dateobs, "skymap": skymap, "tags": tags}

    nretries = 0
    posted = False
    while nretries < 10 and not posted:
        status, data = api("POST", "gcn_event", data=data, token=super_admin_token)
        if status == 200:
            posted = True
        else:
            nretries += 1
            time.sleep(3)

    assert nretries < 10
    assert posted is True
    assert status == 200
    assert data["status"] == "success"

    dateobs = "2022-06-17 18:31:12"
    status, data = api("GET", f"gcn_event/{dateobs}", token=super_admin_token)
    assert status == 200
    data = data["data"]
    assert data["dateobs"] == "2022-06-17T18:31:12"
    assert "IPN" in data["tags"]


@pytest.mark.flaky(reruns=2)
def test_gcnevents_object(
    page, user, super_admin_token, upload_data_token, view_only_token, ztf_camera
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

        # wait for event to load
        time.sleep(15)

    obj_id = str(uuid.uuid4())
    status, data = api(
        "POST",
        "sources",
        data={
            "id": obj_id,
            "ra": 229.9620403,
            "dec": 34.8442757,
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
            "mjd": 58134.025611226854 + 0.5,
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
    catalog_name = str(uuid.uuid4())
    galaxy_name = str(uuid.uuid4())
    data = {
        "catalog_name": catalog_name,
        "catalog_data": {"name": [galaxy_name], "ra": [228.5], "dec": [35.5]},
    }
    status, data = api("POST", "galaxy_catalog", data=data, token=super_admin_token)
    assert status == 200
    assert data["status"] == "success"

    # wait for galaxies to load
    nretries = 0
    galaxies_loaded = False
    while not galaxies_loaded and nretries < 5:
        try:
            status, data = api("GET", "galaxy_catalog", token=view_only_token)
            assert status == 200
            galaxies_loaded = True
        except AssertionError:
            nretries = nretries + 1
            time.sleep(3)

    page.goto(f"/become_user/{user.id}")
    page.goto("/gcn_events/2018-01-16T00:36:53")

    expect(page.locator('//*[text()="180116 00:36:53"]').first).to_be_visible()
    expect(page.locator('//*[text()="Fermi"]').first).to_be_visible()
    expect(page.locator('//*[text()="GRB"]').first).to_be_visible()

    submit_button_xpath = '//button[@type="submit"]'
    page.locator(submit_button_xpath).first.click()

    page.locator('//button[text()="Sources"]').first.click()

    # check for object
    expect(page.locator(f'//*[text()[contains(.,"{obj_id}")]]').first).to_be_visible(
        timeout=15000
    )


def test_reminder_on_gcn(page, super_admin_user, super_admin_token):
    datafile = f"{os.path.dirname(__file__)}/../../../data/GW190814.xml"
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
    for n_times in range(26):
        status, data = api("GET", f"gcn_event/{dateobs}", token=super_admin_token)
        if data["status"] == "success":
            break
        time.sleep(2)
    assert n_times < 25
    gcn_event_id = data["data"]["id"]

    endpoint = f"gcn_event/{gcn_event_id}/reminders"
    post_and_verify_reminder(endpoint, super_admin_token)
    page.goto(f"/become_user/{super_admin_user.id}")
    page.goto(f"/gcn_events/{dateobs}")
    expect(page.locator('//*[contains(.,"190814 21:10:39")]').first).to_be_visible(
        timeout=30000
    )
    page.locator('//*[@data-testid="notificationsButton"]').first.click()
    expect(
        page.locator('//*[@href="/gcn_events/2019-08-14T21:10:39"]').first
    ).to_be_visible()
    page.locator('//*[@data-testid="notificationsButton"]').first.click()


@pytest.mark.flaky(reruns=3)
def test_confirm_reject_source_in_gcn(
    page,
    super_admin_user,
    super_admin_token,
    view_only_token,
    ztf_camera,
    upload_data_token,
):
    datafile = f"{os.path.dirname(__file__)}/../../../data/GW190814.xml"
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
    for n_times in range(26):
        status, data = api("GET", f"gcn_event/{dateobs}", token=super_admin_token)
        if data["status"] == "success":
            break
        time.sleep(2)
    assert n_times < 25

    # wait for the localization to load
    params = {"include2DMap": True}
    for n_times_2 in range(26):
        status, data = api(
            "GET",
            "localization/2019-08-14T21:10:39/name/LALInference.v1.fits.gz",
            token=super_admin_token,
            params=params,
        )

        if data["status"] == "success":
            data = data["data"]
            assert data["dateobs"] == "2019-08-14T21:10:39"
            assert data["localization_name"] == "LALInference.v1.fits.gz"
            assert np.isclose(np.sum(data["flat_2d"]), 1)
            break
        else:
            time.sleep(2)
    assert n_times_2 < 25

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

    status, data = api(
        "POST",
        "photometry",
        data={
            "obj_id": obj_id,
            "mjd": 58709 + 2,
            "instrument_id": ztf_camera.id,
            "flux": 6.24,
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

    page.goto(f"/become_user/{super_admin_user.id}")
    page.goto("/gcn_events/2019-08-14T21:10:39")

    submit_button_xpath = '//button[@type="submit"]'
    page.locator(submit_button_xpath).first.click()

    page.locator('//button[text()="Sources"]').first.click()
    expect(page.locator(f'//*[@name="{obj_id}_gcn_status"]').first).to_be_visible()
    expect(
        page.locator(
            f'//*[@name="{obj_id}_gcn_status"]/*[@data-testid="PriorityHighIcon"]'
        ).first
    ).to_be_visible()

    edit_btn = f'//*[@name="{obj_id}_gcn_status"]/div/*[@type="button"]'
    page.locator(edit_btn).first.click()
    page.locator('//*[@type="button" and contains(., "REJECT")]').first.click()
    expect(
        page.locator(
            f'//*[@name="{obj_id}_gcn_status"]/*[@data-testid="ClearIcon"]'
        ).first
    ).to_be_visible()

    page.locator(edit_btn).first.click()
    page.locator('//*[@type="button" and contains(., "AMBIGUOUS")]').first.click()
    expect(
        page.locator(
            f'//*[@name="{obj_id}_gcn_status"]/*[@data-testid="QuestionMarkIcon"]'
        ).first
    ).to_be_visible()

    page.locator(edit_btn).first.click()
    page.locator('//*[@type="button" and contains(., "HIGHLIGHT")]').first.click()
    expect(
        page.locator(
            f'//*[@name="{obj_id}_gcn_status"]/*[@data-testid="CheckIcon"]'
        ).first
    ).to_be_visible()

    page.goto(f"/source/{obj_id}")

    expect(page.locator('//*[contains(., "GCN Crossmatches:")]').first).to_be_visible()
    expect(
        page.locator('//*[contains(., "2019-08-14T21:10:39")]').first
    ).to_be_visible()
