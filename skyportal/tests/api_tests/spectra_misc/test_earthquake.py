import contextlib
import os
import uuid
from datetime import datetime

import numpy as np
import pytest
from skyportal_py import SkyPortalError
from skyportal_py.earthquakes import EarthquakePost
from skyportal_py.mmadetectors import MMADetectorPost

from skyportal.tests import client


def test_earthquake_predictions_and_measurements(super_admin_token, view_only_token):
    sp = client(super_admin_token)
    name = str(uuid.uuid4())
    detector_id = sp.post_mmadetector(
        MMADetectorPost(
            name=name,
            nickname=name,
            type="gravitational-wave",
            fixed_location=True,
            lat=0.0,
            lon=0.0,
        )
    ).id

    event_id = str(uuid.uuid4())
    event_id = sp.post_earthquake(
        EarthquakePost(
            event_id=event_id,
            latitude=39.3648333,
            longitude=-123.2506667,
            depth=7380.0,
            magnitude=2.93,
            date="2020-08-19 02:00:39",
        )
    ).id

    sp.post_earthquake_prediction(event_id, detector_id)

    sp.post_earthquake_measurement(event_id, detector_id, rfamp=1e-5, lockloss=1)

    event = sp.fetch_earthquake(event_id)
    predictions = event.predictions
    assert predictions[0].p == datetime(2020, 8, 19, 3, 47, 22, 163374)
    assert predictions[0].r2p0 == datetime(2020, 8, 19, 3, 47, 22, 163374)
    measurements = event.measurements
    assert np.isclose(measurements[0].rfamp, 1e-5)
    assert measurements[0].lockloss == 1

    sp.update_earthquake_measurement(event_id, detector_id, rfamp=1e-3, lockloss=0)

    event = sp.fetch_earthquake(event_id)
    measurements = event.measurements
    assert np.isclose(measurements[0].rfamp, 1e-3)
    assert measurements[0].lockloss == 0

    sp.delete_earthquake_measurement(event_id, detector_id)

    event = sp.fetch_earthquake(event_id)
    measurements = event.measurements
    assert len(measurements) == 0


def test_earthquake_quakeml(super_admin_token, view_only_token):
    sp = client(super_admin_token)
    datafile = f"{os.path.dirname(__file__)}/../../data/quakeml.xml"
    with open(datafile, "rb") as fid:
        payload = fid.read()

    event_id = sp.post_earthquake(EarthquakePost(xml=payload)).id

    event = sp.fetch_earthquake(event_id)
    notice = event.notices[0]
    assert notice.date == datetime(2020, 8, 19, 2, 0, 39)
    assert np.isclose(notice.lat, 39.3648333)
    assert np.isclose(notice.lon, -123.2506667)
    assert np.isclose(notice.magnitude, 2.93)
    assert np.isclose(notice.depth, 7380.0)

    page = sp.fetch_earthquakes(
        start_date="2020-01-01T00:00:00",
        end_date="2021-01-01T00:00:00",
    )
    assert len(page.events) > 0
    notice = page.events[0].notices[0]
    assert notice.date == datetime(2020, 8, 19, 2, 0, 39)
    assert np.isclose(notice.lat, 39.3648333)
    assert np.isclose(notice.lon, -123.2506667)
    assert np.isclose(notice.magnitude, 2.93)
    assert np.isclose(notice.depth, 7380.0)

    page = sp.fetch_earthquakes(
        start_date="2021-01-01T00:00:00",
        end_date="2022-01-01T00:00:00",
    )
    assert len(page.events) == 0


def test_earthquake_dictionary(super_admin_token, view_only_token):
    sp = client(super_admin_token)
    event_id = sp.post_earthquake(
        EarthquakePost(
            event_id="quakeml:nc.anss.org-Event-NC-73446401",
            latitude=39.3648333,
            longitude=-123.2506667,
            depth=7380.0,
            magnitude=2.93,
            date="2020-08-19 02:00:39",
        )
    ).id

    event = sp.fetch_earthquake(event_id)
    assert event.notices[0].date == datetime(2020, 8, 19, 2, 0, 39)

    with pytest.raises(SkyPortalError, match="Earthquake event not found") as err:
        client(view_only_token).delete_earthquake(event_id)
    assert err.value.status_code == 404

    sp.delete_earthquake(event_id)

    # original test issues this GET without checking the response
    with contextlib.suppress(SkyPortalError):
        sp.fetch_earthquake(event_id)
