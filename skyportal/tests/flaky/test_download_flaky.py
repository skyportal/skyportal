import os
import time
import uuid
from os.path import join as pjoin

import numpy as np
import pandas as pd
import pytest
from astropy.table import Table
from numpy import random
from playwright.sync_api import expect
from regions import Regions

from baselayer.app.config import load_config
from skyportal.tests import api
from skyportal.tests.external.test_moving_objects import (
    add_telescope_and_instrument,
    remove_telescope_and_instrument,
)

cfg = load_config()


def enter_comment_text(page, comment_text):
    comment_box = page.locator(
        "//div[@data-testid='comments-accordion']//textarea[@name='text']"
    ).first
    comment_box.click()
    comment_box.fill(comment_text)


def test_download_sources(
    page, user, public_group, upload_data_token, annotation_token
):
    # generate a list of 20 source ids:
    source_ids = [str(uuid.uuid4()) for i in range(20)]
    origin = str(uuid.uuid4())
    # post 20 sources:
    for source_id in source_ids:
        status, data = api(
            "POST",
            "sources",
            data={
                "id": source_id,
                # random ra value
                "ra": random.random() * 360 - 180,
                "dec": random.random() * 180 - 90,
                "redshift": 3,
                "transient": False,
                "ra_dis": 2.3,
                "origin": origin,
                "group_ids": [public_group.id],
            },
            token=upload_data_token,
        )
        assert status == 200

    for source_id in source_ids:
        status, data = api(
            "POST",
            f"sources/{source_id}/annotations",
            data={
                "origin": "kowalski",
                "data": {"offset_from_host_galaxy": 1.5},
                "group_ids": [public_group.id],
            },
            token=annotation_token,
        )
        assert status == 200

    for source_id in source_ids:
        status, data = api(
            "POST",
            f"sources/{source_id}/annotations",
            data={
                "origin": "other_origin",
                "data": {
                    "offset_from_host_galaxy": 1.5,
                    "some_boolean": True,
                },
                "group_ids": [public_group.id],
            },
            token=annotation_token,
        )
        assert status == 200

    page.goto(f"/become_user/{user.id}")
    page.goto("/sources")

    # Filter for origin
    page.locator("//button[@data-testid='Filter Table-iconButton']").first.click()
    origin_input = page.locator("//*[@data-testid='origin-text']//input").first
    origin_input.click()
    origin_input.fill(origin)
    page.locator("//button[text()='Submit']").first.click()
    # wait for the filtered results to load before downloading (otherwise the
    # CSV is generated from the unfiltered table)
    page.wait_for_load_state("networkidle")

    # click the download button and capture the download
    fpath = str(os.path.abspath(pjoin(cfg["paths.downloads_folder"], "sources.csv")))
    with page.expect_download() as download_info:
        page.locator('//button[@aria-label="Download CSV"]').first.click()
    download_info.value.save_as(fpath)
    assert os.path.exists(fpath)

    try:
        with open(fpath) as f:
            lines = f.read()
        assert len(lines.split("\n")) == 21
        assert lines.split("\n")[1].find("kowalski;other_origin") != -1
        assert lines.split("\n")[1].find("offset_from_host_galaxy;some_boolean") != -1
    finally:
        os.remove(fpath)


@pytest.mark.flaky(reruns=2)
def test_upload_download_comment_attachment(page, user, public_source):
    page.goto(f"/become_user/{user.id}")
    page.goto(f"/source/{public_source.id}")
    expect(page.locator(f'//h6[text()="{public_source.id}"]').first).to_be_visible()
    comment_text = str(uuid.uuid4())
    enter_comment_text(page, comment_text)

    page.locator(
        "//div[@data-testid='comments-accordion']//input[@name='attachment']"
    ).first.set_input_files(
        os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "spec.csv")
    )
    page.locator(
        '//div[@data-testid="comments-accordion"]//*[@name="submitCommentButton"]'
    ).first.click()

    comment_p = page.locator(
        f'//div[@data-testid="comments-accordion"]//p[text()="{comment_text}"]'
    ).first
    expect(comment_p).to_be_visible(timeout=20000)

    # hover the comment to reveal the attachment controls, then open the preview
    comment_p.locator("xpath=../..").hover()
    attachment_button = page.locator(
        '//div[@data-testid="comments-accordion"]//button[@data-testid="attachmentButton_spec"]'
    ).first
    attachment_button.hover()
    attachment_button.click()

    # preview dialog -> download
    fpath = str(os.path.abspath(pjoin(cfg["paths.downloads_folder"], "spec.csv")))
    with page.expect_download() as download_info:
        page.locator('//a[@data-testid="attachmentDownloadButton_spec"]').first.click()
    download_info.value.save_as(fpath)
    assert os.path.exists(fpath)

    try:
        with open(fpath) as f:
            lines = f.read()
        assert lines.split("\n")[0] == "wavelengths,fluxes,instrument_id"
    finally:
        os.remove(fpath)


def test_gcn_summary_observations(
    page,
    super_admin_user,
    super_admin_token,
    public_group,
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

        gcnevent_id = data["data"]["gcnevent_id"]
    else:
        gcnevent_id = data["data"]["id"]

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
    localization_id = data["id"]

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
            "galactic_latitude": 10,
        },
    }

    status, data = api(
        "POST", "observation_plan", data=request_data, token=super_admin_token
    )
    assert status == 200
    assert data["status"] == "success"

    id = data["data"]["ids"][0]

    # wait for the observation plan to finish loading
    time.sleep(15)

    status, data = api(
        "GET",
        f"observation_plan/{id}",
        params={"includePlannedObservations": "true"},
        token=super_admin_token,
    )
    assert status == 200
    assert data["status"] == "success"

    assert data["data"]["gcnevent_id"] == gcnevent_id
    assert data["data"]["allocation_id"] == allocation_id
    assert data["data"]["payload"] == request_data["payload"]

    assert len(data["data"]["observation_plans"]) == 1

    datafile = f"{os.path.dirname(__file__)}/../../../data/sample_observation_gw.csv"
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
    params = {
        "title": "gcn summary",
        "subject": "follow-up",
        "userIds": super_admin_user.id,
        "groupId": public_group.id,
        "startDate": "2019-08-13 08:18:05",
        "endDate": "2019-08-19 08:18:05",
        "localizationCumprob": 0.99,
        "showSources": True,
        "showGalaxies": False,
        "showObservations": False,
        "noText": False,
    }

    get_summary(page, super_admin_user, public_group, False, False, True)

    fpath = str(
        os.path.abspath(
            pjoin(cfg["paths.downloads_folder"], "Gcn Summary_2019-08-14T21 10 39.txt")
        )
    )
    try_count = 1
    while not os.path.exists(fpath) and try_count <= 5:
        try_count += 1
        time.sleep(1)
    assert os.path.exists(fpath)

    try:
        with open(fpath) as f:
            lines = f.read()
        data = list(filter(None, lines.split("\n")))
        assert "TITLE: GCN SUMMARY" in data[0]
        assert "SUBJECT: Follow-up" in data[1]
        assert "DATE" in data[2]
        assert (
            f"FROM:  {super_admin_user.first_name} {super_admin_user.last_name} at ... <{super_admin_user.contact_email}>"
            in data[3]
        )
        assert f"on behalf of the {public_group.name}, report:" in data[4]

        assert any("Observations:" in line for line in data)
        assert any(
            "We observed the localization region of LVC trigger 2019-08-14T21:10:39.000 UTC"
            in line
            for line in data
        )
        assert any(
            "T-T0 (hr)" in line
            and "mjd" in line
            and "ra" in line
            and "dec" in line
            and "filter" in line
            and "exposure" in line
            and "limmag (ab)" in line
            for line in data
        )

    finally:
        os.remove(fpath)

    remove_telescope_and_instrument(telescope_id, instrument_id, super_admin_token)


def test_gcn_summary_galaxies(
    page,
    super_admin_user,
    super_admin_token,
    view_only_token,
    public_group,
):
    catalog_name = "test_galaxy_catalog"
    # in case the catalog already exists, delete it.
    status, data = api(
        "DELETE", f"galaxy_catalog/{catalog_name}", token=super_admin_token
    )

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

    datafile = f"{os.path.dirname(__file__)}/../../../data/CLU_mini.hdf5"
    data = {
        "catalog_name": catalog_name,
        "catalog_data": Table.read(datafile)
        .to_pandas()
        .replace({np.nan: None})
        .to_dict(orient="list"),
    }

    status, data = api("POST", "galaxy_catalog", data=data, token=super_admin_token)
    assert status == 200
    assert data["status"] == "success"

    params = {"catalog_name": catalog_name}

    nretries = 0
    galaxies_loaded = False
    while nretries < 40:
        status, data = api(
            "GET", "galaxy_catalog", token=view_only_token, params=params
        )
        assert status == 200
        data = data["data"]["galaxies"]
        if len(data) == 92 and any(
            d["name"] == "6dFgs gJ0001313-055904" and d["mstar"] == 336.60756522868667
            for d in data
        ):
            galaxies_loaded = True
            break
        nretries = nretries + 1
        time.sleep(2)

    assert nretries < 40
    assert galaxies_loaded

    # get the gcn event summary
    params = {
        "title": "gcn summary",
        "subject": "follow-up",
        "userIds": super_admin_user.id,
        "groupId": public_group.id,
        "startDate": "2019-08-13 08:18:05",
        "endDate": "2019-08-19 08:18:05",
        "localizationCumprob": 0.99,
        "showSources": True,
        "showGalaxies": False,
        "showObservations": False,
        "noText": False,
    }

    get_summary(page, super_admin_user, public_group, False, True, False)

    fpath = str(
        os.path.abspath(
            pjoin(cfg["paths.downloads_folder"], "Gcn Summary_2019-08-14T21 10 39.txt")
        )
    )
    try_count = 1
    while not os.path.exists(fpath) and try_count <= 5:
        try_count += 1
        time.sleep(1)
    assert os.path.exists(fpath)

    try:
        with open(fpath) as f:
            lines = f.read()
        data = list(filter(None, lines.split("\n")))
        assert "TITLE: GCN SUMMARY" in data[0]
        assert "SUBJECT: Follow-up" in data[1]
        assert "DATE" in data[2]
        assert (
            f"FROM:  {super_admin_user.first_name} {super_admin_user.last_name} at ... <{super_admin_user.contact_email}>"
            in data[3]
        )
        assert f"on behalf of the {public_group.name}, report:" in data[4]

        assert any(
            "Found 54 galaxies in the event's localization:" in line for line in data
        )

        assert any(
            "Galaxy" in line
            and "RA" in line
            and "Dec" in line
            and "Distance" in line
            and "m_Ks" in line
            and "m_NUV" in line
            and "m_W1" in line
            and "dP_dV" in line
            for line in data
        )

    finally:
        os.remove(fpath)

    status, data = api(
        "DELETE", f"galaxy_catalog/{catalog_name}", token=super_admin_token
    )


def test_gcn_summary_sources(
    page,
    super_admin_user,
    super_admin_token,
    view_only_token,
    public_group,
    ztf_camera,
    upload_data_token,
):
    datafile = f"{os.path.dirname(__file__)}/../../../data/GW190814.xml"
    with open(datafile, "rb") as fid:
        payload = fid.read()
    data = {"xml": payload}

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
            "mjd": 58709 + 1.5,
            "instrument_id": ztf_camera.id,
            "flux": 13.24,
            "fluxerr": 0.131,
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

    # get the gcn event summary
    params = {
        "title": "gcn summary",
        "subject": "follow-up",
        "userIds": super_admin_user.id,
        "groupId": public_group.id,
        "startDate": "2019-08-13 08:18:05",
        "endDate": "2019-08-19 08:18:05",
        "localizationCumprob": 1.00,
        "numberDetections": 1,
        "showSources": True,
        "showGalaxies": False,
        "showObservations": False,
        "noText": False,
    }

    get_summary(page, super_admin_user, public_group, True, False, False)

    fpath = str(
        os.path.abspath(
            pjoin(cfg["paths.downloads_folder"], "Gcn Summary_2019-08-14T21 10 39.txt")
        )
    )
    try_count = 1
    while not os.path.exists(fpath) and try_count <= 5:
        try_count += 1
        time.sleep(1)
    assert os.path.exists(fpath)

    try:
        with open(fpath) as f:
            lines = f.read()
        data = list(filter(None, lines.split("\n")))
        assert "TITLE: GCN SUMMARY" in data[0]
        assert "SUBJECT: Follow-up" in data[1]
        assert "DATE" in data[2]
        assert (
            f"FROM:  {super_admin_user.first_name} {super_admin_user.last_name} at ... <{super_admin_user.contact_email}>"
            in data[3]
        )
        assert f"on behalf of the {public_group.name}, report:" in data[4]

        assert any(
            "Found" in line and "in the event's localization" in line for line in data
        )

        assert any(
            "id" in line
            and "tns" in line
            and "ra" in line
            and "dec" in line
            and "redshift" in line
            and "comment" in line
            for line in data
        )

        # source phot
        assert any("Photometry for source" in line for line in data)
        assert any(
            "mjd" in line and "mag±err (ab)" in line and "filter" in line
            for line in data
        )
    finally:
        os.remove(fpath)


def get_summary(page, user, group, showSources, showGalaxies, showObservations):
    page.goto(f"/become_user/{user.id}")
    page.goto("/gcn_events/2019-08-14T21:10:39")

    page.locator('//button[@name="gcn_summary"]').first.click()

    page.locator('//*[@aria-labelledby="group-select"]').first.click()
    page.locator(f'//li[contains(., "{group.name}")]').first.click()
    # (the single-select closes on option click; no Escape, which would close
    # the whole summary dialog)

    if showSources is True:
        page.locator('//*[@label="Show Sources"]').first.click()
    if showGalaxies is True:
        page.locator('//*[@label="Show Galaxies"]').first.click()
    if showObservations is True:
        page.locator('//*[@label="Show Observations"]').first.click()

    page.locator('//button[contains(.,"Generate")]').first.click()
    page.locator('//button[contains(.,"Retrieve")]').first.click()

    expect(page.locator('//textarea[@id="text"]').first).to_be_visible(timeout=60000)
    expect(
        page.locator('//textarea[contains(.,"TITLE: GCN SUMMARY")]').first
    ).to_be_visible(timeout=60000)

    with page.expect_download() as download_info:
        page.locator('//button[contains(.,"Download")]').first.click()
    download = download_info.value
    download.save_as(pjoin(cfg["paths.downloads_folder"], download.suggested_filename))


def test_download_localization(super_admin_token):
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

    skymap = "LALInference.v1.fits.gz"
    assert data["data"]["dateobs"] == dateobs
    assert any(
        loc["localization_name"] == skymap for loc in data["data"]["localizations"]
    )

    status, data = api(
        "GET",
        f"localization/{dateobs}/name/{skymap}/download",
        token=super_admin_token,
    )
    assert status == 200
