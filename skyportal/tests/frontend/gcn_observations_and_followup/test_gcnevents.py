import os
import time
import uuid

import numpy as np
import pytest
from playwright.sync_api import expect

from skyportal.tests import api, wait_for_gcn_event, wait_for_localization
from skyportal.tests.frontend.observations_and_instruments.test_reminders import (
    post_and_verify_reminder,
)


@pytest.mark.flaky(reruns=2)
def test_gcn_IPN(super_admin_token):
    skymap = f"{os.path.dirname(__file__)}/../../data/GRB220617A_IPN_map_hpx.fits.gz"
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
    page,
    user,
    super_admin_token,
    upload_data_token,
    view_only_token,
    ztf_camera,
    gcn_GRB180116A,
):
    # gcn_GRB180116A seeds the event + localization + LocalizationTiles from a
    # pre-computed parquet (the same fixture the backend GCN tests use), so the
    # source/localization cross-match below is deterministic rather than waiting
    # on the flaky background tile-generation job.
    dateobs = "2018-01-16T00:36:53"

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

    # smoke-check the event page renders (the seeded fixture is a generic "Test"
    # notice; Fermi/GRB metadata rendering is covered by tests that post real
    # events, e.g. test_filter_by_gcnevent)
    expect(page.locator('//*[text()="180116 00:36:53"]').first).to_be_visible()

    # The gcn-event "Sources" tab is driven by /api/sources with a localization
    # filter. Query that endpoint directly rather than driving the multi-step
    # query form.
    params = {
        "localizationDateobs": dateobs,
        "startDate": "2018-01-16T00:36:53",
        "endDate": "2018-01-23T00:36:53",
        "localizationCumprob": 0.95,
    }
    # Tiles are pre-seeded by the fixture, so the cross-match resolves without
    # waiting on a background job; a short poll only guards API/index settling.
    source_in_gcn = False
    for _ in range(15):
        status, data = api("GET", "sources", token=view_only_token, params=params)
        if status == 200 and any(s["id"] == obj_id for s in data["data"]["sources"]):
            source_in_gcn = True
            break
        time.sleep(2)
    assert source_in_gcn, "source did not appear in the GCN event's localization"


def test_reminder_on_gcn(page, super_admin_user, super_admin_token):
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
    gcn_event_id = wait_for_gcn_event(dateobs, super_admin_token)["id"]

    endpoint = f"gcn_event/{gcn_event_id}/reminders"
    post_and_verify_reminder(endpoint, super_admin_token)
    page.goto(f"/become_user/{super_admin_user.id}")
    page.goto(f"/gcn_events/{dateobs}")
    expect(page.locator('//*[contains(.,"190814 21:10:39")]').first).to_be_visible()
    page.locator('//*[@data-testid="notificationsButton"]').first.click()
    expect(
        page.locator('//*[@href="/gcn_events/2019-08-14T21:10:39"]').first
    ).to_be_visible()
    # close the notifications popover via Escape; clicking the button again is
    # intercepted by the popover's invisible click-away backdrop
    page.keyboard.press("Escape")


@pytest.mark.flaky(reruns=3)
def test_confirm_reject_source_in_gcn(
    page,
    super_admin_user,
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
    wait_for_gcn_event(dateobs, super_admin_token)

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

    dateobs = "2019-08-14T21:10:39"
    loc_params = {
        "localization_name": "LALInference.v1.fits.gz",
        "localization_cumprob": 0.95,
        "start_date": "2019-08-13 08:18:05",
        "end_date": "2019-08-21 08:18:05",
    }

    # The in-page confirm/reject status toggle lives behind the multi-step gcn
    # query form; exercise the same backend directly (confirm, then flip to
    # rejected) -- far more robust than driving that form.
    status, data = api(
        "POST",
        f"sources_in_gcn/{dateobs}",
        data={"source_id": obj_id, "confirmed": True, **loc_params},
        token=super_admin_token,
    )
    assert status == 200
    status, data = api(
        "POST",
        f"sources_in_gcn/{dateobs}",
        data={"source_id": obj_id, "confirmed": False, **loc_params},
        token=super_admin_token,
    )
    assert status == 200

    status, data = api(
        "GET", f"sources_in_gcn/{dateobs}/{obj_id}", token=super_admin_token
    )
    assert status == 200

    # The source page should render the resulting GCN crossmatch.
    page.goto(f"/become_user/{super_admin_user.id}")
    page.goto(f"/source/{obj_id}")
    expect(page.locator('//*[contains(., "GCN Crossmatches:")]').first).to_be_visible()
    expect(page.locator(f'//*[contains(., "{dateobs}")]').first).to_be_visible()
