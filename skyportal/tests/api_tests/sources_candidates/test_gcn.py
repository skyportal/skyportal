import os
import time
import uuid

import numpy as np
import pytest
import requests
from astropy.table import Table

from skyportal.tests import api
from skyportal.tests.external.test_moving_objects import (
    add_telescope_and_instrument,
    remove_telescope_and_instrument,
)
from skyportal.utils.gcn import from_url

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


@pytest.mark.flaky(reruns=2)
def test_gcn_GW(super_admin_token, view_only_token):
    datafile = f"{os.path.dirname(__file__)}/../../data/GW190425_initial.xml"
    with open(datafile, "rb") as fid:
        payload = fid.read()
    event_data = {"xml": payload}

    dateobs = "2019-04-25 08:18:05"
    status, data = api("GET", f"gcn_event/{dateobs}", token=super_admin_token)
    if status == 404:
        status, data = api(
            "POST", "gcn_event", data=event_data, token=super_admin_token
        )
        assert status == 200
        assert data["status"] == "success"

    dateobs = "2019-04-25 08:18:05"
    status, data = api("GET", f"gcn_event/{dateobs}", token=super_admin_token)
    assert status == 200
    data = data["data"]
    assert data["dateobs"] == "2019-04-25T08:18:05"
    assert "GW" in data["tags"]
    property_dict = {
        "BBH": 0.0,
        "BNS": 0.999402567114,
        "FAR": 4.53764787126e-13,
        "NSBH": 0.0,
        "HasNS": 1.0,
        "MassGap": 0.0,
        "HasRemnant": 1.0,
        "Terrestrial": 0.00059743288626,
        "num_instruments": 2,
    }
    assert data["properties"][0]["data"] == property_dict

    params = {
        "startDate": "2019-04-25T00:00:00",
        "endDate": "2019-04-26T00:00:00",
        "gcnTagKeep": "GW",
    }

    status, data = api("GET", "gcn_event", token=super_admin_token, params=params)
    assert status == 200
    data = data["data"]
    assert len(data["events"]) > 0
    data = data["events"][0]
    assert data["dateobs"] == "2019-04-25T08:18:05"
    assert "GW" in data["tags"]

    params = {
        "startDate": "2019-04-25T00:00:00",
        "endDate": "2019-04-26T00:00:00",
        "gcnTagKeep": "Fermi",
    }

    status, data = api("GET", "gcn_event", token=super_admin_token, params=params)
    assert status == 200
    data = data["data"]
    assert len(data["events"]) == 0

    params = {"include2DMap": True}
    skymap = "bayestar.fits.gz"
    status, data = api(
        "GET",
        f"localization/{dateobs}/name/{skymap}",
        token=super_admin_token,
        params=params,
    )

    data = data["data"]
    assert data["dateobs"] == "2019-04-25T08:18:05"
    assert data["localization_name"] == "bayestar.fits.gz"
    assert np.isclose(np.sum(data["flat_2d"]), 1)

    status, data = api(
        "DELETE",
        f"localization/{dateobs}/name/{skymap}",
        token=view_only_token,
    )
    assert status == 404

    status, data = api(
        "DELETE",
        f"localization/{dateobs}/name/{skymap}",
        token=super_admin_token,
    )
    assert status == 200

    # delete the event
    status, data = api(
        "DELETE", "gcn_event/2019-04-25T08:18:05", token=super_admin_token
    )


def test_gcn_Fermi(super_admin_token, view_only_token):
    datafile = (
        f"{os.path.dirname(__file__)}/../../data/GRB180116A_Fermi_GBM_Gnd_Pos.xml"
    )
    with open(datafile, "rb") as fid:
        payload = fid.read()
    event_data = {"xml": payload}

    dateobs = "2018-01-16 00:36:53"
    status, data = api("GET", f"gcn_event/{dateobs}", token=super_admin_token)

    if status == 404:
        status, data = api(
            "POST", "gcn_event", data=event_data, token=super_admin_token
        )
        assert status == 200
        assert data["status"] == "success"

    params = {"include2DMap": True}
    status, data = api("GET", f"gcn_event/{dateobs}", token=super_admin_token)
    if status != 200:
        print(data)
    assert status == 200
    data = data["data"]
    assert data["dateobs"] == "2018-01-16T00:36:53"
    assert "GRB" in data["tags"]

    skymap = "214.74000_28.14000_11.19000"
    status, data = api(
        "GET",
        f"localization/{dateobs}/name/{skymap}",
        token=super_admin_token,
        params=params,
    )

    data = data["data"]
    assert data["dateobs"] == "2018-01-16T00:36:53"
    assert data["localization_name"] == "214.74000_28.14000_11.19000"
    assert np.isclose(np.sum(data["flat_2d"]), 1)

    status, data = api(
        "DELETE",
        f"localization/{dateobs}/name/{skymap}",
        token=view_only_token,
    )
    assert status == 404

    status, data = api(
        "DELETE",
        f"localization/{dateobs}/name/{skymap}",
        token=super_admin_token,
    )
    assert status == 200


def test_gcn_from_moc(super_admin_token):
    name = str(uuid.uuid4())
    post_data = {
        "name": name,
        "nickname": name,
        "type": "gravitational-wave",
        "fixed_location": True,
        "lat": 0.0,
        "lon": 0.0,
    }

    status, data = api("POST", "mmadetector", data=post_data, token=super_admin_token)
    assert status == 200
    assert data["status"] == "success"
    mmadetector_id = data["data"]["id"]

    skymap = f"{os.path.dirname(__file__)}/../../data/GRB220617A_IPN_map_hpx.fits.gz"
    dateobs = "2022-06-18T18:31:12"
    tags = ["IPN", "GRB", name]
    skymap, _, _ = from_url(skymap)
    properties = {"BNS": 0.9, "NSBH": 0.1}

    event_data = {
        "dateobs": dateobs,
        "skymap": skymap,
        "tags": tags,
        "properties": properties,
    }

    dateobs = "2022-06-18 18:31:12"
    status, data = api("GET", f"gcn_event/{dateobs}", token=super_admin_token)
    if status == 404:
        status, data = api(
            "POST", "gcn_event", data=event_data, token=super_admin_token
        )
        assert status == 200
        assert data["status"] == "success"

    status, data = api("GET", f"gcn_event/{dateobs}", token=super_admin_token)
    assert status == 200
    data = data["data"]
    assert data["dateobs"] == "2022-06-18T18:31:12"
    assert "IPN" in data["tags"]
    assert name in [detector["name"] for detector in data["detectors"]]
    properties_dict = data["properties"][0]
    assert properties_dict["data"] == properties

    status, data = api("GET", f"mmadetector/{mmadetector_id}", token=super_admin_token)
    assert status == 200
    assert data["status"] == "success"
    data = data["data"]
    assert "2022-06-18T18:31:12" in [event["dateobs"] for event in data["events"]]

    params = {"gcnPropertiesFilter": "BNS: 0.5: gt, NSBH: 0.5: lt"}
    status, data = api("GET", "gcn_event", token=super_admin_token, params=params)
    assert status == 200
    data = data["data"]
    assert "2022-06-18T18:31:12" in [event["dateobs"] for event in data["events"]]

    params = {"gcnPropertiesFilter": "BNS: 0.5: lt, NSBH: 0.5: lt"}
    status, data = api("GET", "gcn_event", token=super_admin_token, params=params)
    assert status == 200
    data = data["data"]
    assert "2022-06-18T18:31:12" not in [event["dateobs"] for event in data["events"]]


def test_gcn_from_json(super_admin_token):
    datafile = f"{os.path.dirname(__file__)}/../../data/EP240508.json"
    with open(datafile, "rb") as fid:
        payload = fid.read()
    event_data = {"json": payload}

    dateobs = "2024-05-08T07:38:01"
    status, data = api("GET", f"gcn_event/{dateobs}", token=super_admin_token)
    if status == 404:
        status, data = api(
            "POST", "gcn_event", data=event_data, token=super_admin_token
        )
        assert status == 200
        assert data["status"] == "success"

    dateobs = "2024-05-08T07:38:01"
    status, data = api("GET", f"gcn_event/{dateobs}", token=super_admin_token)
    assert status == 200
    data = data["data"]
    assert data["dateobs"] == "2024-05-08T07:38:01"
    assert "Einstein Probe" in data["tags"]

    params = {"include2DMap": True}
    skymap = "229.83800_-29.74700_0.05090"
    n_retries = 0
    while True:
        try:
            status, data = api(
                "GET",
                f"localization/{dateobs}/name/{skymap}",
                token=super_admin_token,
                params=params,
            )

            data = data["data"]
            assert data.get("dateobs") == "2024-05-08T07:38:01"
            assert data.get("localization_name") == skymap
            assert np.isclose(np.sum(data.get("flat_2d", [])), 1)
            break
        except AssertionError as e:
            if n_retries == 5:
                raise e
            n_retries += 1
            time.sleep(2)

    status, data = api(
        "DELETE",
        f"localization/{dateobs}/name/{skymap}",
        token=super_admin_token,
    )
    assert status == 200

    # delete the event
    status, data = api(
        "DELETE", "gcn_event/2024-05-08T07:38:01", token=super_admin_token
    )


def test_gcn_from_igwn_json(super_admin_token):
    # LVK IGWN gwalert JSON (replaces the retired GCN Classic LVC VOEvents). The
    # skymap is embedded in the alert as base64 and ingested directly.
    datafile = f"{os.path.dirname(__file__)}/../../data/igwn_gwalert_preliminary.json"
    with open(datafile, "rb") as fid:
        payload = fid.read()

    dateobs = "2026-06-05T11:57:26"
    status, data = api("GET", f"gcn_event/{dateobs}", token=super_admin_token)
    if status == 404:
        status, data = api(
            "POST", "gcn_event", data={"json": payload}, token=super_admin_token
        )
        assert status == 200, data
        assert data["status"] == "success"

    status, data = api("GET", f"gcn_event/{dateobs}", token=super_admin_token)
    assert status == 200
    data = data["data"]
    assert data["dateobs"] == dateobs
    for tag in ("GW", "BNS", "Significant"):
        assert tag in data["tags"]
    assert "LVC#MS260605l" in data["aliases"]

    skymap = "MS260605l-PRELIMINARY.multiorder.fits"
    params = {"include2DMap": True}
    n_retries = 0
    while True:
        try:
            status, data = api(
                "GET",
                f"localization/{dateobs}/name/{skymap}",
                token=super_admin_token,
                params=params,
            )
            data = data["data"]
            assert data.get("localization_name") == skymap
            assert np.isclose(np.sum(data.get("flat_2d", [])), 1)
            break
        except AssertionError as e:
            if n_retries == 10:
                raise e
            n_retries += 1
            time.sleep(2)

    # a retraction of the same superevent adds the "retracted" tag
    datafile = f"{os.path.dirname(__file__)}/../../data/igwn_gwalert_retraction.json"
    with open(datafile, "rb") as fid:
        retraction = fid.read()
    status, data = api(
        "POST", "gcn_event", data={"json": retraction}, token=super_admin_token
    )
    assert status == 200, data

    n_retries = 0
    while True:
        status, data = api("GET", f"gcn_event/{dateobs}", token=super_admin_token)
        assert status == 200
        if "retracted" in data["data"]["tags"] or n_retries == 5:
            break
        n_retries += 1
        time.sleep(2)
    assert "retracted" in data["data"]["tags"]

    api("DELETE", f"localization/{dateobs}/name/{skymap}", token=super_admin_token)
    api("DELETE", f"gcn_event/{dateobs}", token=super_admin_token)


def test_gcn_from_polygon(super_admin_token):
    localization_name = str(uuid.uuid4())
    dateobs = "2022-09-03T14:44:12"
    polygon = [(30.0, 60.0), (40.0, 60.0), (40.0, 70.0), (30.0, 70.0)]
    tags = ["IPN", "GRB"]
    skymap = {"polygon": polygon, "localization_name": localization_name}

    event_data = {"dateobs": dateobs, "skymap": skymap, "tags": tags}

    status, data = api("POST", "gcn_event", data=event_data, token=super_admin_token)
    assert status == 200
    assert data["status"] == "success"

    dateobs = "2022-09-03 14:44:12"
    status, data = api("GET", f"gcn_event/{dateobs}", token=super_admin_token)
    assert status == 200
    data = data["data"]
    assert data["dateobs"] == "2022-09-03T14:44:12"
    assert "IPN" in data["tags"]


def test_gcn_Swift(super_admin_token):
    datafile = f"{os.path.dirname(__file__)}/../../data/SWIFT_1125809-092.xml"
    with open(datafile, "rb") as fid:
        payload = fid.read()
    event_data_1 = {"xml": payload}

    datafile = f"{os.path.dirname(__file__)}/../../data/SWIFT_1125809-104.xml"
    with open(datafile, "rb") as fid:
        payload = fid.read()
    event_data_2 = {"xml": payload}

    dateobs = "2022-09-30 11:11:52"
    status, data = api("GET", f"gcn_event/{dateobs}", token=super_admin_token)

    if status == 404:
        status, data = api(
            "POST", "gcn_event", data=event_data_1, token=super_admin_token
        )
        assert status == 200
        assert data["status"] == "success"

        status, data = api(
            "POST", "gcn_event", data=event_data_2, token=super_admin_token
        )
        assert status == 200
        assert data["status"] == "success"

    status, data = api("GET", f"gcn_event/{dateobs}", token=super_admin_token)
    assert status == 200
    data = data["data"]
    assert data["dateobs"] == "2022-09-30T11:11:52"
    assert any(
        loc["localization_name"] == "64.71490_13.35000_0.00130"
        for loc in data["localizations"]
    )
    assert any(
        loc["localization_name"] == "64.73730_13.35170_0.05000"
        for loc in data["localizations"]
    )

    # wait for the async tasks to finish before finishing the tests, which will delete the user
    # from the db, causing failures in the session.commit() in the async tasks (because the user is not in the db anymore)
    time.sleep(5)


def test_gcn_summary_sources(
    super_admin_user,
    super_admin_token,
    view_only_token,
    public_group,
    ztf_camera,
    upload_data_token,
    gcn_GW190814,
):
    dateobs = gcn_GW190814.dateobs.strftime("%Y-%m-%dT%H:%M:%S")

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

    # get the gcn event summary
    data = {
        "title": "gcn summary",
        "subject": "follow-up",
        "userIds": super_admin_user.id,
        "groupId": public_group.id,
        "startDate": "2019-08-13 08:18:05",
        "endDate": "2019-08-19 08:18:05",
        "localizationCumprob": 0.99,
        "numberDetections": 1,
        "showSources": True,
        "showGalaxies": False,
        "showObservations": False,
        "noText": False,
    }

    status, data = api(
        "POST",
        f"gcn_event/{dateobs}/summary",
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
            f"gcn_event/{dateobs}/summary/{summary_id}",
            token=view_only_token,
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

    def _find(*substrings):
        # index of the first line containing all of `substrings`; asserts presence
        for i, line in enumerate(lines):
            if all(s in line for s in substrings):
                return i
        raise AssertionError(f"no summary line contains all of {substrings}")

    def _section_has_header(start, end, columns):
        # one line within lines[start:end] carries every expected column header
        assert any(all(col in line for col in columns) for line in lines[start:end]), (
            lines[start:end]
        )

    # Locate sections by content rather than fixed line offsets, so these
    # assertions survive harmless reformatting of the summary builder.

    # header block
    _find("TITLE: GCN SUMMARY")
    _find("SUBJECT: Follow-up")
    _find("DATE")
    _find(
        f"FROM: {super_admin_user.first_name} {super_admin_user.last_name} at ... <{super_admin_user.contact_email}>"
    )
    _find(f"reports on behalf of the {public_group.name} group:")

    # sources section, then a "Photometry of <id>" subsection
    found_idx = _find("Found", "in the event's localization")
    phot_idx = _find("Photometry of")
    assert found_idx < phot_idx

    _section_has_header(found_idx, phot_idx, ("id", "tns", "ra", "dec", "redshift"))
    _section_has_header(
        phot_idx, len(lines), ("mjd", "mag±err (ab)", "filter", "origin", "instrument")
    )

    # the source we posted is actually present in the summary
    assert obj_id in text


def test_gcn_summary_galaxies(
    super_admin_user,
    super_admin_token,
    view_only_token,
    public_group,
    gcn_GW190814,
):
    dateobs = gcn_GW190814.dateobs.strftime("%Y-%m-%dT%H:%M:%S")

    catalog_name = "test_galaxy_catalog"
    # in case the catalog already exists, delete it.
    status, data = api(
        "DELETE", f"galaxy_catalog/{catalog_name}", token=super_admin_token
    )

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
        "showGalaxies": True,
        "showObservations": False,
        "noText": False,
    }

    status, data = api(
        "POST",
        f"gcn_event/{dateobs}/summary",
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
            f"gcn_event/{dateobs}/summary/{summary_id}",
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
    lines = list(filter(None, data["text"].split("\n")))

    def _find(*substrings):
        # index of the first line containing all of `substrings`; asserts presence
        for i, line in enumerate(lines):
            if all(s in line for s in substrings):
                return i
        raise AssertionError(f"no summary line contains all of {substrings}")

    # Locate sections by content rather than fixed line offsets.

    # header block
    _find("TITLE: GCN SUMMARY")
    _find("SUBJECT: Follow-up")
    _find("DATE")
    _find(
        f"FROM: {super_admin_user.first_name} {super_admin_user.last_name} at ... <{super_admin_user.contact_email}>"
    )
    _find(f"reports on behalf of the {public_group.name} group:")

    # galaxies section: the count claim plus a table header carrying every column
    galaxy_idx = _find("Found **82 galaxies** in the event's localization:")
    assert any(
        all(
            col in line
            for col in (
                "Galaxy",
                "RA [deg]",
                "Dec [deg]",
                "Distance [Mpc]",
                "m_Ks [mag]",
                "m_NUV [mag]",
                "m_W1 [mag]",
                "dP_dV",
            )
        )
        for line in lines[galaxy_idx:]
    ), lines[galaxy_idx:]

    status, data = api(
        "DELETE", f"galaxy_catalog/{catalog_name}", token=super_admin_token
    )


def test_gcn_instrument_field(
    super_admin_token,
    gcn_GW190814,
):
    dateobs = gcn_GW190814.dateobs.strftime("%Y-%m-%dT%H:%M:%S")

    telescope_id, instrument_id, _, _ = add_telescope_and_instrument(
        "ZTF", super_admin_token, list(range(200, 250))
    )

    status, data = api(
        "GET",
        f"gcn_event/{dateobs}/instrument/{instrument_id}",
        token=super_admin_token,
    )
    assert status == 200
    assert data["status"] == "success"

    assert "field_ids" in data["data"]
    assert "probabilities" in data["data"]

    assert set(data["data"]["field_ids"]) == {201, 202, 246, 247}

    remove_telescope_and_instrument(telescope_id, instrument_id, super_admin_token)


def test_confirm_reject_source_in_gcn(
    super_admin_token,
    view_only_token,
    ztf_camera,
    upload_data_token,
    gcn_GW190814,
):
    dateobs = gcn_GW190814.dateobs.strftime("%Y-%m-%dT%H:%M:%S")

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

    params = {
        "sourcesIdList": obj_id,
    }
    status, data = api(
        "GET",
        f"sources_in_gcn/{dateobs}",
        params=params,
        token=upload_data_token,
    )
    assert status == 200
    assert len(data["data"]) == 0

    # confirm source
    params = {
        "source_id": obj_id,
        "localization_name": "LALInference.v1.fits.gz",
        "localization_cumprob": 0.95,
        "confirmed": True,
        "start_date": "2019-08-13 08:18:05",
        "end_date": "2019-08-19 08:18:05",
    }

    # verify that you can't confirm a source without the Manage GCNs permission
    status, data = api(
        "POST",
        f"sources_in_gcn/{dateobs}",
        data=params,
        token=upload_data_token,
    )
    assert status == 401

    status, data = api(
        "POST",
        f"sources_in_gcn/{dateobs}",
        data=params,
        token=super_admin_token,
    )
    assert status == 200

    params = {
        "sourcesIdList": obj_id,
    }
    status, data = api(
        "GET",
        f"sources_in_gcn/{dateobs}",
        params=params,
        token=upload_data_token,
    )
    assert status == 200
    data = data["data"]
    assert len(data) == 1
    assert data[0]["obj_id"] == obj_id
    assert data[0]["dateobs"] == dateobs
    assert data[0]["confirmed"] is True

    # find gcns associated to source
    status, data = api(
        "GET",
        f"associated_gcns/{obj_id}",
        token=upload_data_token,
    )
    assert status == 200
    data = data["data"]
    assert dateobs in data["gcns"]

    # reject source
    params = {
        "confirmed": False,
    }

    status, data = api(
        "PATCH",
        f"sources_in_gcn/{dateobs}/{obj_id}",
        data=params,
        token=upload_data_token,
    )
    assert status == 401

    status, data = api(
        "PATCH",
        f"sources_in_gcn/{dateobs}/{obj_id}",
        data=params,
        token=super_admin_token,
    )
    assert status == 200

    params = {
        "sourcesIdList": obj_id,
    }
    status, data = api(
        "GET",
        f"sources_in_gcn/{dateobs}",
        params=params,
        token=upload_data_token,
    )
    assert status == 200
    data = data["data"]
    assert len(data) == 1
    assert data[0]["obj_id"] == obj_id
    assert data[0]["dateobs"] == dateobs
    assert data[0]["confirmed"] is False

    # verify that no gcns are associated to source

    # find no gcns associated to source
    status, data = api(
        "GET",
        f"associated_gcns/{obj_id}",
        token=upload_data_token,
    )
    assert status == 200
    data = data["data"]
    assert len(data["gcns"]) == 0

    # mark source as unknow (delete it from the table)
    status, data = api(
        "DELETE",
        f"sources_in_gcn/{dateobs}/{obj_id}",
        token=upload_data_token,
    )
    assert status == 401

    status, data = api(
        "DELETE",
        f"sources_in_gcn/{dateobs}/{obj_id}",
        token=super_admin_token,
    )
    assert status == 200

    params = {
        "sourcesIdList": obj_id,
    }
    status, data = api(
        "GET",
        f"sources_in_gcn/{dateobs}",
        params=params,
        token=upload_data_token,
    )
    assert status == 200
    data = data["data"]
    assert len(data) == 0


@pytest.mark.skipif(not tach_isonline, reason="GCN TACH is not online")
def test_gcn_tach(
    super_admin_token,
    view_only_token,
    gcn_GRB180116A,
):
    dateobs = gcn_GRB180116A.dateobs.strftime("%Y-%m-%dT%H:%M:%S")
    status, data = api("GET", f"gcn_event/{dateobs}", token=super_admin_token)
    assert status == 200

    data = data["data"]
    assert "aliases" in data
    assert "GRB180116A" not in data["aliases"]
    aliases_len = len(data["aliases"])

    status, data = api("POST", f"gcn_event/{dateobs}/tach", token=view_only_token)
    assert status == 401

    status, data = api("POST", f"gcn_event/{dateobs}/tach", token=super_admin_token)
    assert status == 200
    assert data["status"] == "success"

    for n_times in range(30):
        status, data = api("GET", f"gcn_event/{dateobs}", token=super_admin_token)
        if data["status"] == "success":
            if len(data["data"]["aliases"]) > 1:
                aliases = data["data"]["aliases"]
                break
            time.sleep(1)

    assert n_times < 29
    assert len(aliases) == aliases_len + 1
    assert "GRB180116A" in aliases

    status, data = api("GET", f"gcn_event/{dateobs}/tach", token=super_admin_token)

    assert status == 200
    assert data["status"] == "success"
    data = data["data"]
    assert len(data["aliases"]) == 2
    assert len(data["circulars"]) == 3
    assert data["tach_id"] is not None


def test_gcn_allocation_triggers(
    public_group,
    super_admin_token,
    view_only_token,
    gcn_GRB180116A,
):
    dateobs = gcn_GRB180116A.dateobs.strftime("%Y-%m-%dT%H:%M:%S")

    status, data = api("GET", f"gcn_event/{dateobs}", token=super_admin_token)
    assert status == 200

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

    status, data = api(
        "PUT",
        f"gcn_event/{dateobs}/triggered/{allocation_id}",
        data={"triggered": True},
        token=super_admin_token,
    )
    assert status == 200
    assert data["status"] == "success"

    status, data = api(
        "PUT",
        f"gcn_event/{dateobs}/triggered/{allocation_id}",
        data={"triggered": False},
        token=super_admin_token,
    )
    assert status == 200
    assert data["status"] == "success"

    # now we verify that the view_only_token can't change the triggered status
    status, data = api(
        "PUT",
        f"gcn_event/{dateobs}/triggered/{allocation_id}",
        data={"triggered": True},
        token=view_only_token,
    )
    assert status == 401

    status, data = api("GET", f"gcn_event/{dateobs}", token=super_admin_token)
    assert status == 200
    assert data["status"] == "success"
    assert data["data"]["gcn_triggers"][0]["allocation_id"] == allocation_id
    assert data["data"]["gcn_triggers"][0]["triggered"] is False
