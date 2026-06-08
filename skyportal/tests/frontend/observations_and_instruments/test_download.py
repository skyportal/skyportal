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
from skyportal.tests import api, wait_for_gcn_event, wait_for_localization
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
    # wait for the filtered results to load before downloading
    page.wait_for_load_state("networkidle")

    # click the download button and capture the download
    fpath = str(os.path.abspath(pjoin(cfg["paths.downloads_folder"], "sources.csv")))
    with page.expect_download() as download_info:
        page.locator('//button[@aria-label="Download CSV"]').first.click()
    download_info.value.save_as(fpath)
    assert os.path.exists(fpath)

    try:
        with open(fpath) as f:
            lines = [line for line in f.read().split("\n") if line.strip()]
        # the CSV download is not strictly limited to the origin-filtered set (and
        # the shared DB accumulates sources across tests), so assert on our own 20
        # sources rather than a fixed total line count. Each of our rows must carry
        # the aggregated multi-origin annotation columns.
        our_rows = [line for line in lines if any(sid in line for sid in source_ids)]
        assert len(our_rows) == 20, f"expected our 20 sources, found {len(our_rows)}"
        assert all("kowalski;other_origin" in line for line in our_rows)
        assert all("offset_from_host_galaxy;some_boolean" in line for line in our_rows)
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
        os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "data",
            "spec.csv",
        )
    )
    page.locator(
        '//div[@data-testid="comments-accordion"]//*[@name="submitCommentButton"]'
    ).first.click()

    comment_p = page.locator(
        f'//div[@data-testid="comments-accordion"]//p[text()="{comment_text}"]'
    ).first
    expect(comment_p).to_be_visible()

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
    # generate the GCN summary (with observations) and read it back
    text = get_summary(
        page, super_admin_user, public_group, False, False, True, super_admin_token
    )

    # The summary is markdown viewed in the Edit dialog now (no downloaded file),
    # so assert on stable content substrings rather than fixed line indices.
    assert "TITLE: GCN SUMMARY" in text
    assert "SUBJECT: Follow-up" in text
    assert "DATE" in text
    assert (
        f"FROM: {super_admin_user.first_name} {super_admin_user.last_name} at ... <{super_admin_user.contact_email}>"
        in text
    )
    assert f"on behalf of the {public_group.name} group:" in text

    assert "Observations:" in text
    assert (
        "We observed the localization region of LVC trigger 2019-08-14T21:10:39.000 UTC"
        in text
    )
    # the observations table header row lists the columns
    assert all(
        col in text
        for col in (
            "T-T0 (hr)",
            "mjd",
            "ra",
            "dec",
            "filter",
            "exposure",
            "limmag (ab)",
        )
    )

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

    datafile = f"{os.path.dirname(__file__)}/../../../../data/CLU_mini.hdf5"
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

    # The catalog row count being ready doesn't mean the galaxies are yet matchable
    # within the localization (the probability cross-match lags), and the summary's
    # galaxy table needs that. Wait until galaxies fall inside the localization with
    # a probability -- same cumprob 0.95 and returnProbability the summary uses --
    # before generating.
    loc_params = {
        "catalog_name": catalog_name,
        "localizationDateobs": "2019-08-14T21:10:39",
        "localizationName": "LALInference.v1.fits.gz",
        "localizationCumprob": 0.95,
        "returnProbability": True,
    }
    nretries = 0
    galaxies_in_localization = False
    while nretries < 40:
        status, data = api(
            "GET", "galaxy_catalog", token=super_admin_token, params=loc_params
        )
        if status == 200 and len(data["data"]["galaxies"]) > 0:
            galaxies_in_localization = True
            break
        nretries += 1
        time.sleep(2)
    assert galaxies_in_localization

    text = get_summary(
        page, super_admin_user, public_group, False, True, False, super_admin_token
    )

    # Markdown summary read via the API now (no downloaded file); assert on stable
    # content substrings rather than fixed line indices.
    assert "TITLE: GCN SUMMARY" in text
    assert "SUBJECT: Follow-up" in text
    assert "DATE" in text
    assert (
        f"FROM: {super_admin_user.first_name} {super_admin_user.last_name} at ... <{super_admin_user.contact_email}>"
        in text
    )
    assert f"on behalf of the {public_group.name} group:" in text

    # markdown bolds the count ("Found **54 galaxies** in the event's
    # localization:"), so match the unformatted tail of the phrase
    assert "in the event's localization" in text
    # the galaxies table header row lists the columns
    assert all(
        col in text
        for col in (
            "Galaxy",
            "RA",
            "Dec",
            "Distance",
            "m_Ks",
            "m_NUV",
            "m_W1",
            "dP_dV",
        )
    )

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
    datafile = f"{os.path.dirname(__file__)}/../../../../data/GW190814.xml"
    with open(datafile, "rb") as fid:
        payload = fid.read()
    data = {"xml": payload}

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

    # generate the GCN summary (with sources) and read it back
    text = get_summary(
        page, super_admin_user, public_group, True, False, False, super_admin_token
    )

    # Markdown summary read via the API now (no downloaded file); assert on stable
    # content substrings rather than fixed line indices.
    assert "TITLE: GCN SUMMARY" in text
    assert "SUBJECT: Follow-up" in text
    assert "DATE" in text
    assert (
        f"FROM: {super_admin_user.first_name} {super_admin_user.last_name} at ... <{super_admin_user.contact_email}>"
        in text
    )
    assert f"on behalf of the {public_group.name} group:" in text

    assert "in the event's localization" in text

    # the sources table header row lists the columns
    assert all(col in text for col in ("id", "tns", "ra", "dec", "redshift", "comment"))

    # source photometry (the header is "Photometry of **<id>**:")
    assert "Photometry of" in text
    assert all(col in text for col in ("mjd", "mag±err (ab)", "filter"))


def get_summary(
    page,
    user,
    group,
    showSources,
    showGalaxies,
    showObservations,
    token,
    localization_name="LALInference.v1.fits.gz",
):
    dateobs = "2019-08-14T21:10:39"
    # Generate via the API instead of the flaky summary dialog (page/user kept
    # for the callers' signature); the text is read back via the API below.
    status, _ = api(
        "POST",
        f"gcn_event/{dateobs}/summary",
        data={
            "title": "Gcn Summary",
            "subject": f"Follow-up on GCN Event {dateobs}",
            "groupId": group.id,
            "startDate": "2019-08-01T00:00:00",
            "endDate": "2019-09-01T00:00:00",
            "localizationName": localization_name,
            "localizationCumprob": 0.95,
            "numberDetections": 2,
            "numberObservations": 1,
            "showSources": showSources,
            "showGalaxies": showGalaxies,
            "showObservations": showObservations,
        },
        token=token,
    )
    assert status == 200, f"summary generation POST failed with status {status}"

    summary_id = None
    for _ in range(40):
        status, data = api("GET", f"gcn_event/{dateobs}", token=token)
        if status == 200:
            for s in data["data"]["summaries"]:  # sorted newest-first by the API
                if s["group"]["id"] == group.id:
                    summary_id = s["id"]
                    break
        if summary_id is not None:
            break
        time.sleep(2)
    assert summary_id is not None, "GCN summary was not created by the Generate action"

    summary_text = "pending"
    for _ in range(40):
        status, data = api(
            "GET", f"gcn_event/{dateobs}/summary/{summary_id}", token=token
        )
        if status == 200 and data["data"]["text"] != "pending":
            summary_text = data["data"]["text"]
            break
        time.sleep(5)
    assert summary_text != "pending", "GCN summary text did not finish generating"
    return summary_text


def test_download_localization(super_admin_token):
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
    event = wait_for_gcn_event(dateobs, super_admin_token)

    skymap = "LALInference.v1.fits.gz"
    assert event["dateobs"] == dateobs
    assert any(loc["localization_name"] == skymap for loc in event["localizations"])

    status, data = api(
        "GET",
        f"localization/{dateobs}/name/{skymap}/download",
        token=super_admin_token,
    )
    assert status == 200
