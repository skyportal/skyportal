import json
import os
import time
import uuid
from contextlib import suppress
from datetime import timedelta

import numpy as np
import pytest
import requests
import sqlalchemy as sa
from astropy.table import Table
from astropy.time import Time
from skyportal_py import SkyPortalError
from skyportal_py.allocations import AllocationPost
from skyportal_py.galaxies import GalaxyCatalogPost
from skyportal_py.gcn_events import GcnEventObjPost, GcnEventPost, GcnSummaryPost
from skyportal_py.instruments import InstrumentPost
from skyportal_py.mmadetectors import MMADetectorPost
from skyportal_py.photometry import PhotometryPost
from skyportal_py.sources import SourcePost
from skyportal_py.telescopes import TelescopePost

from skyportal.handlers.api.gcn import add_default_gcn_tags
from skyportal.models import DBSession, DefaultGcnTag, User
from skyportal.tests import client, retry_until
from skyportal.tests.external.test_moving_objects import (
    add_telescope_and_instrument,
    remove_telescope_and_instrument,
)
from skyportal.utils.gcn import from_url
from skyportal.utils.naive_datetime import utcnow_naive

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
    sp = client(super_admin_token)
    datafile = f"{os.path.dirname(__file__)}/../../data/GW190425_initial.xml"
    with open(datafile, "rb") as fid:
        payload = fid.read()
    event_data = GcnEventPost(xml=payload)

    dateobs = "2019-04-25 08:18:05"
    try:
        sp.fetch_gcn_event(dateobs)
    except SkyPortalError as err:
        if err.status_code == 404:
            sp.post_gcn_event(event_data)

    dateobs = "2019-04-25 08:18:05"
    event = sp.fetch_gcn_event(dateobs)
    assert event.dateobs.isoformat() == "2019-04-25T08:18:05"
    assert "GW" in event.tags
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
    assert event.properties[0].data == property_dict

    page = sp.fetch_gcn_events(
        start_date="2019-04-25T00:00:00",
        end_date="2019-04-26T00:00:00",
        gcn_tag_keep=["GW"],
    )
    assert len(page.events) > 0
    event = page.events[0]
    assert event.dateobs.isoformat() == "2019-04-25T08:18:05"
    assert "GW" in event.tags

    page = sp.fetch_gcn_events(
        start_date="2019-04-25T00:00:00",
        end_date="2019-04-26T00:00:00",
        gcn_tag_keep=["Fermi"],
    )
    assert len(page.events) == 0

    skymap = "bayestar.fits.gz"
    localization = sp.fetch_localization(dateobs, skymap, include_2d_map=True)

    assert localization.dateobs.isoformat() == "2019-04-25T08:18:05"
    assert localization.localization_name == "bayestar.fits.gz"
    assert np.isclose(np.sum(localization.flat_2d), 1)

    with pytest.raises(SkyPortalError) as err:
        client(view_only_token).delete_localization(dateobs, skymap)
    assert err.value.status_code == 404

    sp.delete_localization(dateobs, skymap)

    # delete the event (result was not checked before, so tolerate failure)
    with suppress(SkyPortalError):
        sp.delete_gcn_event("2019-04-25T08:18:05")


def test_gcn_Fermi(super_admin_token, view_only_token):
    sp = client(super_admin_token)
    datafile = (
        f"{os.path.dirname(__file__)}/../../data/GRB180116A_Fermi_GBM_Gnd_Pos.xml"
    )
    with open(datafile, "rb") as fid:
        payload = fid.read()
    event_data = GcnEventPost(xml=payload)

    dateobs = "2018-01-16 00:36:53"
    try:
        sp.fetch_gcn_event(dateobs)
    except SkyPortalError as err:
        if err.status_code == 404:
            sp.post_gcn_event(event_data)

    event = sp.fetch_gcn_event(dateobs)
    assert event.dateobs.isoformat() == "2018-01-16T00:36:53"
    assert "GRB" in event.tags

    skymap = "214.74000_28.14000_11.19000"
    localization = sp.fetch_localization(dateobs, skymap, include_2d_map=True)

    assert localization.dateobs.isoformat() == "2018-01-16T00:36:53"
    assert localization.localization_name == "214.74000_28.14000_11.19000"
    assert np.isclose(np.sum(localization.flat_2d), 1)

    with pytest.raises(SkyPortalError) as err:
        client(view_only_token).delete_localization(dateobs, skymap)
    assert err.value.status_code == 404

    sp.delete_localization(dateobs, skymap)


def test_gcn_from_moc(super_admin_token):
    sp = client(super_admin_token)
    name = str(uuid.uuid4())
    mmadetector_id = sp.post_mmadetector(
        MMADetectorPost(
            name=name,
            nickname=name,
            type="gravitational-wave",
            fixed_location=True,
            lat=0.0,
            lon=0.0,
        )
    ).id

    skymap = f"{os.path.dirname(__file__)}/../../data/GRB220617A_IPN_map_hpx.fits.gz"
    dateobs = "2022-06-18T18:31:12"
    tags = ["IPN", "GRB", name]
    skymap, _, _ = from_url(skymap)
    properties = {"BNS": 0.9, "NSBH": 0.1}

    event_data = GcnEventPost(
        dateobs=dateobs,
        skymap=skymap,
        tags=tags,
        properties=properties,
    )

    dateobs = "2022-06-18 18:31:12"
    try:
        sp.fetch_gcn_event(dateobs)
    except SkyPortalError as err:
        if err.status_code == 404:
            sp.post_gcn_event(event_data)

    event = sp.fetch_gcn_event(dateobs)
    assert event.dateobs.isoformat() == "2022-06-18T18:31:12"
    assert "IPN" in event.tags
    assert name in [detector.name for detector in event.detectors]
    properties_dict = event.properties[0]
    assert properties_dict.data == properties

    mmadetector = sp.fetch_mmadetector(mmadetector_id)
    assert "2022-06-18T18:31:12" in [event["dateobs"] for event in mmadetector.events]

    page = sp.fetch_gcn_events(gcn_properties_filter=["BNS: 0.5: gt", "NSBH: 0.5: lt"])
    assert "2022-06-18T18:31:12" in [event.dateobs.isoformat() for event in page.events]

    page = sp.fetch_gcn_events(gcn_properties_filter=["BNS: 0.5: lt", "NSBH: 0.5: lt"])
    assert "2022-06-18T18:31:12" not in [
        event.dateobs.isoformat() for event in page.events
    ]


def test_gcn_from_json(super_admin_token):
    sp = client(super_admin_token)
    datafile = f"{os.path.dirname(__file__)}/../../data/EP240508.json"
    with open(datafile, "rb") as fid:
        payload = fid.read()
    event_data = GcnEventPost(json_notice=json.loads(payload))

    dateobs = "2024-05-08T07:38:01"
    try:
        sp.fetch_gcn_event(dateobs)
    except SkyPortalError as err:
        if err.status_code == 404:
            sp.post_gcn_event(event_data)

    dateobs = "2024-05-08T07:38:01"
    event = sp.fetch_gcn_event(dateobs)
    assert event.dateobs.isoformat() == "2024-05-08T07:38:01"
    assert "Einstein Probe" in event.tags

    skymap = "229.83800_-29.74700_0.05090"
    n_retries = 0
    while True:
        try:
            localization = sp.fetch_localization(dateobs, skymap, include_2d_map=True)

            assert localization.dateobs is not None
            assert localization.dateobs.isoformat() == "2024-05-08T07:38:01"
            assert localization.localization_name == skymap
            assert np.isclose(np.sum(localization.flat_2d or []), 1)
            break
        except AssertionError as e:
            if n_retries == 5:
                raise e
            n_retries += 1
            time.sleep(2)

    sp.delete_localization(dateobs, skymap)

    # delete the event (result was not checked before, so tolerate failure)
    with suppress(SkyPortalError):
        sp.delete_gcn_event("2024-05-08T07:38:01")


def test_gcn_from_igwn_json(super_admin_token):
    sp = client(super_admin_token)
    # LVK IGWN gwalert JSON (replaces the retired GCN Classic LVC VOEvents). The
    # skymap is embedded in the alert as base64 and ingested directly.
    datafile = f"{os.path.dirname(__file__)}/../../data/igwn_gwalert_preliminary.json"
    with open(datafile, "rb") as fid:
        payload = fid.read()

    dateobs = "2026-06-05T11:57:26"
    try:
        sp.fetch_gcn_event(dateobs)
    except SkyPortalError as err:
        if err.status_code == 404:
            sp.post_gcn_event(GcnEventPost(json_notice=json.loads(payload)))

    event = sp.fetch_gcn_event(dateobs)
    assert event.dateobs.isoformat() == dateobs
    for tag in ("GW", "BNS", "Significant"):
        assert tag in event.tags
    assert "LVC#MS260605l" in event.aliases

    skymap = "MS260605l-PRELIMINARY.multiorder.fits"
    n_retries = 0
    while True:
        try:
            localization = sp.fetch_localization(dateobs, skymap, include_2d_map=True)
            assert localization.localization_name == skymap
            assert np.isclose(np.sum(localization.flat_2d or []), 1)
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
    sp.post_gcn_event(GcnEventPost(json_notice=json.loads(retraction)))

    n_retries = 0
    while True:
        event = sp.fetch_gcn_event(dateobs)
        if "retracted" in event.tags or n_retries == 5:
            break
        n_retries += 1
        time.sleep(2)
    assert "retracted" in event.tags

    # cleanup (results were not checked before, so tolerate failure)
    with suppress(SkyPortalError):
        sp.delete_localization(dateobs, skymap)
    with suppress(SkyPortalError):
        sp.delete_gcn_event(dateobs)


def test_gcn_from_polygon(super_admin_token):
    sp = client(super_admin_token)
    localization_name = str(uuid.uuid4())
    dateobs = "2022-09-03T14:44:12"
    polygon = [(30.0, 60.0), (40.0, 60.0), (40.0, 70.0), (30.0, 70.0)]
    tags = ["IPN", "GRB"]
    skymap = {"polygon": polygon, "localization_name": localization_name}

    sp.post_gcn_event(GcnEventPost(dateobs=dateobs, skymap=skymap, tags=tags))

    dateobs = "2022-09-03 14:44:12"
    event = sp.fetch_gcn_event(dateobs)
    assert event.dateobs.isoformat() == "2022-09-03T14:44:12"
    assert "IPN" in event.tags


def test_gcn_Swift(super_admin_token):
    sp = client(super_admin_token)
    datafile = f"{os.path.dirname(__file__)}/../../data/SWIFT_1125809-092.xml"
    with open(datafile, "rb") as fid:
        payload = fid.read()
    event_data_1 = GcnEventPost(xml=payload)

    datafile = f"{os.path.dirname(__file__)}/../../data/SWIFT_1125809-104.xml"
    with open(datafile, "rb") as fid:
        payload = fid.read()
    event_data_2 = GcnEventPost(xml=payload)

    dateobs = "2022-09-30 11:11:52"
    try:
        sp.fetch_gcn_event(dateobs)
    except SkyPortalError as err:
        if err.status_code == 404:
            sp.post_gcn_event(event_data_1)
            sp.post_gcn_event(event_data_2)

    event = sp.fetch_gcn_event(dateobs)
    assert event.dateobs.isoformat() == "2022-09-30T11:11:52"
    assert any(
        loc.localization_name == "64.71490_13.35000_0.00130"
        for loc in event.localizations
    )
    assert any(
        loc.localization_name == "64.73730_13.35170_0.05000"
        for loc in event.localizations
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
    client(upload_data_token).post_source(
        SourcePost(
            id=obj_id,
            ra=24.6258,
            dec=-32.9024,
            redshift=3,
        )
    )

    client(view_only_token).fetch_source(obj_id)

    client(upload_data_token).post_photometry(
        PhotometryPost(
            obj_id=obj_id,
            mjd=58709 + 1,
            instrument_id=ztf_camera.id,
            flux=12.24,
            fluxerr=0.031,
            zp=25.0,
            magsys="ab",
            filter="ztfg",
            ra=24.6258,
            dec=-32.9024,
            ra_unc=0.01,
            dec_unc=0.01,
        )
    )

    # get the gcn event summary
    summary_id = (
        client(super_admin_token)
        .post_gcn_summary(
            dateobs,
            GcnSummaryPost(
                title="gcn summary",
                subject="follow-up",
                user_ids=[super_admin_user.id],
                group_id=public_group.id,
                start_date="2019-08-13 08:18:05",
                end_date="2019-08-19 08:18:05",
                localization_cumprob=0.99,
                number_detections=1,
                show_sources=True,
                show_galaxies=False,
                show_observations=False,
                no_text=False,
            ),
        )
        .id
    )

    def summary_ready():
        summary = client(view_only_token).fetch_gcn_summary(dateobs, summary_id)
        assert summary.text != "pending"
        return summary.text

    text = retry_until(summary_ready, timeout=200)
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
    sp = client(super_admin_token)
    dateobs = gcn_GW190814.dateobs.strftime("%Y-%m-%dT%H:%M:%S")

    catalog_name = "test_galaxy_catalog"
    # in case the catalog already exists, delete it.
    with suppress(SkyPortalError):
        sp.delete_galaxy_catalog(catalog_name)

    datafile = f"{os.path.dirname(__file__)}/../../../../data/CLU_mini.hdf5"
    sp.post_galaxy_catalog(
        GalaxyCatalogPost(
            catalog_name=catalog_name,
            catalog_data=Table.read(datafile)
            .to_pandas()
            .replace({np.nan: None})
            .to_dict(orient="list"),
        )
    )

    def galaxies_loaded():
        galaxies = (
            client(view_only_token).fetch_galaxies(catalog_name=catalog_name).galaxies
        )
        assert len(galaxies) == 92
        assert any(
            galaxy.name == "6dFgs gJ0001313-055904"
            and galaxy.mstar == 336.60756522868667
            for galaxy in galaxies
        )

    retry_until(galaxies_loaded, timeout=80)

    # get the gcn event summary
    summary_id = sp.post_gcn_summary(
        dateobs,
        GcnSummaryPost(
            title="gcn summary",
            subject="follow-up",
            user_ids=[super_admin_user.id],
            group_id=public_group.id,
            start_date="2019-08-13 08:18:05",
            end_date="2019-08-19 08:18:05",
            localization_cumprob=0.99,
            show_sources=False,
            show_galaxies=True,
            show_observations=False,
            no_text=False,
        ),
    ).id

    def summary_ready():
        summary = client(view_only_token).fetch_gcn_summary(dateobs, summary_id)
        assert summary.text != "pending"
        return summary.text

    lines = list(filter(None, retry_until(summary_ready, timeout=200).split("\n")))

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

    with suppress(SkyPortalError):
        sp.delete_galaxy_catalog(catalog_name)


def test_gcn_instrument_field(
    super_admin_token,
    gcn_GW190814,
):
    dateobs = gcn_GW190814.dateobs.strftime("%Y-%m-%dT%H:%M:%S")

    telescope_id, instrument_id, _, _ = add_telescope_and_instrument(
        "ZTF", super_admin_token, list(range(200, 250))
    )

    fields = client(super_admin_token).fetch_gcn_event_instrument_fields(
        dateobs, instrument_id
    )

    assert fields.field_ids
    assert fields.probabilities

    assert set(fields.field_ids) == {201, 202, 246, 247}

    remove_telescope_and_instrument(telescope_id, instrument_id, super_admin_token)


def test_confirm_reject_source_in_gcn(
    super_admin_token,
    view_only_token,
    ztf_camera,
    upload_data_token,
    gcn_GW190814,
):
    sp = client(upload_data_token)
    dateobs = gcn_GW190814.dateobs.strftime("%Y-%m-%dT%H:%M:%S")

    obj_id = str(uuid.uuid4())
    sp.post_source(
        SourcePost(
            id=obj_id,
            ra=24.6258,
            dec=-32.9024,
            redshift=3,
        )
    )

    client(view_only_token).fetch_source(obj_id)

    sp.post_photometry(
        PhotometryPost(
            obj_id=obj_id,
            mjd=58709 + 1,
            instrument_id=ztf_camera.id,
            flux=12.24,
            fluxerr=0.031,
            zp=25.0,
            magsys="ab",
            filter="ztfg",
            ra=24.6258,
            dec=-32.9024,
            ra_unc=0.01,
            dec_unc=0.01,
        )
    )

    sources = sp.fetch_gcn_event_sources(dateobs, source_ids=[obj_id])
    assert len(sources) == 0

    # confirm source
    # vetting needs no GCN-specific ACL, just the ability to write data
    sp.post_gcn_event_source(
        dateobs,
        GcnEventObjPost(
            source_id=obj_id,
            localization_name="LALInference.v1.fits.gz",
            localization_cumprob=0.95,
            status="confirmed",
            start_date="2019-08-13 08:18:05",
            end_date="2019-08-19 08:18:05",
        ),
    )

    sources = sp.fetch_gcn_event_sources(dateobs, source_ids=[obj_id])
    assert len(sources) == 1
    assert sources[0].obj_id == obj_id
    assert sources[0].dateobs.isoformat() == dateobs
    assert sources[0].status == "confirmed"

    # find gcns associated to source
    gcns = sp.fetch_gcn_events_associated_with_source(obj_id)
    assert dateobs in gcns

    # reject source
    sp.update_gcn_event_source(dateobs, obj_id, "rejected")

    sources = sp.fetch_gcn_event_sources(dateobs, source_ids=[obj_id])
    assert len(sources) == 1
    assert sources[0].obj_id == obj_id
    assert sources[0].dateobs.isoformat() == dateobs
    assert sources[0].status == "rejected"

    # verify that no gcns are associated to source

    # find no gcns associated to source
    gcns = sp.fetch_gcn_events_associated_with_source(obj_id)
    assert len(gcns) == 0

    # mark source as unknow (delete it from the table)
    sp.delete_gcn_event_source(dateobs, obj_id)

    sources = sp.fetch_gcn_event_sources(dateobs, source_ids=[obj_id])
    assert len(sources) == 0


@pytest.mark.skipif(not tach_isonline, reason="GCN TACH is not online")
def test_gcn_tach(
    super_admin_token,
    view_only_token,
    gcn_GRB180116A,
):
    sp = client(super_admin_token)
    dateobs = gcn_GRB180116A.dateobs.strftime("%Y-%m-%dT%H:%M:%S")
    event = sp.fetch_gcn_event(dateobs)

    assert event.aliases is not None
    assert "GRB180116A" not in event.aliases
    aliases_len = len(event.aliases)

    with pytest.raises(SkyPortalError) as err:
        client(view_only_token).post_gcn_event_tach(dateobs)
    assert err.value.status_code == 401

    sp.post_gcn_event_tach(dateobs)

    for n_times in range(30):
        event = sp.fetch_gcn_event(dateobs)
        if len(event.aliases) > 1:
            aliases = event.aliases
            break
        time.sleep(1)

    assert n_times < 29
    assert len(aliases) == aliases_len + 1
    assert "GRB180116A" in aliases

    tach = sp.fetch_gcn_event_tach(dateobs)

    assert len(tach.aliases) == 2
    assert len(tach.circulars) == 3
    assert tach.tach_id is not None


def test_gcn_allocation_triggers(
    public_group,
    super_admin_token,
    view_only_token,
    gcn_GRB180116A,
):
    sp = client(super_admin_token)
    dateobs = gcn_GRB180116A.dateobs.strftime("%Y-%m-%dT%H:%M:%S")

    sp.fetch_gcn_event(dateobs)

    name = str(uuid.uuid4())
    telescope_id = sp.post_telescope(
        TelescopePost(
            name=name,
            nickname=name,
            lat=0.0,
            lon=0.0,
            elevation=0.0,
            diameter=10.0,
        )
    ).id

    instrument_name = str(uuid.uuid4())
    instrument_id = sp.post_instrument(
        InstrumentPost(
            name=instrument_name,
            type="imager",
            band="Optical",
            filters=["ztfr"],
            telescope_id=telescope_id,
            api_classname="ZTFAPI",
            api_classname_obsplan="ZTFMMAAPI",
            field_fov_type="circle",
            field_fov_attributes=3.0,
            sensitivity_data={
                "ztfr": {
                    "limiting_magnitude": 20.3,
                    "magsys": "ab",
                    "exposure_time": 30,
                    "zeropoint": 26.3,
                }
            },
        )
    ).id

    allocation_id = sp.post_allocation(
        AllocationPost(
            group_id=public_group.id,
            instrument_id=instrument_id,
            pi="Shri Kulkarni",
            hours_allocated=200,
            validity_ranges=[
                {
                    "start_date": "2021-02-27T00:00:00.000Z",
                    "end_date": "3021-07-20T00:00:00.000Z",
                }
            ],
            proposal_id="COO-2020A-P01",
            default_share_group_ids=[public_group.id],
        )
    ).id

    sp.fetch_allocation(allocation_id)

    sp.update_gcn_event_trigger(dateobs, allocation_id, triggered=True)

    sp.update_gcn_event_trigger(dateobs, allocation_id, triggered=False)

    # now we verify that the view_only_token can't change the triggered status
    with pytest.raises(SkyPortalError) as err:
        client(view_only_token).update_gcn_event_trigger(
            dateobs, allocation_id, triggered=True
        )
    assert err.value.status_code == 401

    event = sp.fetch_gcn_event(dateobs)
    assert event.gcn_triggers[0].allocation_id == allocation_id
    assert event.gcn_triggers[0].triggered is False


def test_gcn_autogenerated_source_has_t0(super_admin_token):
    """A source auto-created from a tight localization carries the event time as t0."""
    sp = client(super_admin_token)
    dateobs = (utcnow_naive() - timedelta(days=3)).replace(microsecond=0)
    sp.post_gcn_event(
        GcnEventPost(
            dateobs=dateobs.isoformat(),
            # error well under SOURCE_RADIUS_THRESHOLD, so post_gcn_source fires
            skymap={"ra": 42.0, "dec": 12.0, "error": 0.04},
            # no group_ids -> sitewide public group, which post_gcn_source requires
        )
    )

    obj_id = f"GCN-{dateobs.strftime('%y%m%d_%H%M%S')}"
    source = None
    for _ in range(30):
        try:
            source = sp.fetch_source(obj_id)
            break
        except SkyPortalError:
            time.sleep(1)
    assert source is not None, f"source {obj_id} was never created"
    assert source.t0 == pytest.approx(Time(dateobs.isoformat()).mjd)


def test_default_gcn_tag_matches_on_notice_type(super_admin_token, user):
    """A DefaultGcnTag scoped by notice_types matches an event with that notice.

    The filter key was read as "notice_type" while the presence check used
    "notice_types", so every notice-type-scoped default raised KeyError and was
    silently skipped by the surrounding except. The positive case below is what
    distinguishes the bug: before the fix no such tag was ever returned.

    Calls add_default_gcn_tags directly -- the handler only runs the default-tag
    pass when it ingests a new skymap, so re-posting an existing event does not
    exercise it.
    """
    sp = client(super_admin_token)
    datafile = (
        f"{os.path.dirname(__file__)}/../../data/GRB180116A_Fermi_GBM_Gnd_Pos.xml"
    )
    with open(datafile, "rb") as fid:
        payload = fid.read()
    dateobs = "2018-01-16 00:36:53"

    try:
        sp.post_gcn_event(GcnEventPost(xml=payload))
    except SkyPortalError as err:
        # 400 if an earlier test already posted it
        assert err.status_code == 400, str(err)

    event = sp.fetch_gcn_event(dateobs)
    notice_types = [n.notice_type for n in event.gcn_notices]
    assert notice_types, "event has no notices to match on"

    matching, nonmatching = str(uuid.uuid4()), str(uuid.uuid4())
    user_id = user.id
    with DBSession() as session:
        session.add_all(
            [
                DefaultGcnTag(
                    requester_id=user.id,
                    default_tag_name=matching,
                    filters={"notice_types": [notice_types[0]]},
                ),
                DefaultGcnTag(
                    requester_id=user.id,
                    default_tag_name=nonmatching,
                    filters={"notice_types": ["NOT_A_REAL_NOTICE_TYPE"]},
                ),
            ]
        )
        session.commit()

    try:
        with DBSession() as session:
            # re-fetch: the fixture instance is detached, and the
            # access-controlled select lazy-loads user.acls
            u = session.get(User, user_id)
            session.user_or_token = u
            produced = {
                tag.text
                for tag in add_default_gcn_tags(
                    u, session, dateobs=Time(dateobs).datetime
                )
            }
        assert matching in produced, (
            f"notice-type-scoped default was not applied; produced={produced}"
        )
        assert nonmatching not in produced, "a non-matching notice type was applied"
    finally:
        with DBSession() as session:
            for name in (matching, nonmatching):
                row = session.scalar(
                    sa.select(DefaultGcnTag).where(
                        DefaultGcnTag.default_tag_name == name
                    )
                )
                if row is not None:
                    session.delete(row)
            session.commit()
