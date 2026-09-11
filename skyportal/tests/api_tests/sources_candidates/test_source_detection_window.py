import uuid

from skyportal.tests import api

# An arbitrary quiet patch of sky, and a window one day wide inside it.
RA, DEC = 42.01, 12.34
WINDOW_START_MJD = 59800.0
WINDOW_END_MJD = 59801.0


def _post_source_with_detections(obj_id, mjds, token, group, camera):
    status, _ = api(
        "POST",
        "sources",
        data={"id": obj_id, "ra": RA, "dec": DEC, "group_ids": [group.id]},
        token=token,
    )
    assert status == 200
    for mjd in mjds:
        status, _ = api(
            "POST",
            "photometry",
            data={
                "obj_id": obj_id,
                "mjd": mjd,
                "instrument_id": camera.id,
                "filter": "ztfg",
                "group_ids": [group.id],
                "mag": 18.0,
                "magerr": 0.1,
                "limiting_mag": 22.0,
                "magsys": "ab",
            },
            token=token,
        )
        assert status == 200


def _mjd_to_iso(mjd):
    from astropy.time import Time

    return Time(mjd, format="mjd").isot


def test_detected_window_keeps_sources_still_being_detected(
    upload_data_token, view_only_token, public_group, ztf_camera
):
    """A counterpart detected during the window, then again after it, is kept.

    startDate/endDate ask for the whole detection history to sit inside the
    range, so a transient that goes on being detected fails that test -- which
    is exactly the object a GCN search is looking for. detectedWindowStart and
    detectedWindowEnd ask the question the search actually means: was it
    detected during the window.
    """
    still_going = str(uuid.uuid4())
    contained = str(uuid.uuid4())

    # Detected inside the window, and still detected a fortnight later.
    _post_source_with_detections(
        still_going,
        [WINDOW_START_MJD + 0.5, WINDOW_END_MJD + 14.0],
        upload_data_token,
        public_group,
        ztf_camera,
    )
    # Detected only inside the window.
    _post_source_with_detections(
        contained,
        [WINDOW_START_MJD + 0.5],
        upload_data_token,
        public_group,
        ztf_camera,
    )

    window = {
        "requireDetections": True,
        "detectedWindowStart": _mjd_to_iso(WINDOW_START_MJD),
        "detectedWindowEnd": _mjd_to_iso(WINDOW_END_MJD),
        "group_ids": [public_group.id],
    }
    status, data = api("GET", "sources", params=window, token=view_only_token)
    assert status == 200
    found = {source["id"] for source in data["data"]["sources"]}
    assert still_going in found, (
        "a source detected in the window but still being detected afterwards "
        "must be kept"
    )
    assert contained in found

    # The old bounds keep their meaning: the whole history must be inside.
    bounds = {
        "requireDetections": True,
        "startDate": _mjd_to_iso(WINDOW_START_MJD),
        "endDate": _mjd_to_iso(WINDOW_END_MJD),
        "group_ids": [public_group.id],
    }
    status, data = api("GET", "sources", params=bounds, token=view_only_token)
    assert status == 200
    found = {source["id"] for source in data["data"]["sources"]}
    assert contained in found
    assert still_going not in found, (
        "startDate/endDate still bound the whole detection history"
    )


def test_detected_window_excludes_sources_outside_it(
    upload_data_token, view_only_token, public_group, ztf_camera
):
    """A source detected only long after the window is not a counterpart."""
    later = str(uuid.uuid4())
    _post_source_with_detections(
        later,
        [WINDOW_END_MJD + 30.0, WINDOW_END_MJD + 31.0],
        upload_data_token,
        public_group,
        ztf_camera,
    )

    status, data = api(
        "GET",
        "sources",
        params={
            "requireDetections": True,
            "detectedWindowStart": _mjd_to_iso(WINDOW_START_MJD),
            "detectedWindowEnd": _mjd_to_iso(WINDOW_END_MJD),
            "group_ids": [public_group.id],
        },
        token=view_only_token,
    )
    assert status == 200
    found = {source["id"] for source in data["data"]["sources"]}
    assert later not in found
