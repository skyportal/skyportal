import traceback
import uuid
from datetime import datetime

import numpy as np

from baselayer.app.env import load_env
from skyportal.models.phot_stat import PhotStat
from skyportal.models.photometry import PHOT_ZP, Photometry
from skyportal.tests import api

_, cfg = load_env()
PHOT_DETECTION_THRESHOLD = cfg["misc.photometry_detection_threshold_nsigma"]


def test_phot_stats_permissions(upload_data_token, super_admin_token, public_source):
    # normal user cannot delete or update the phot stats
    status, data = api(
        "DELETE", f"sources/{public_source.id}/phot_stat", token=upload_data_token
    )
    assert status == 401
    assert "Unauthorized" in data["message"]

    status, data = api(
        "PUT",
        f"sources/{public_source.id}/phot_stat",
        token=upload_data_token,
        data={},
    )
    assert status == 401
    assert "Unauthorized" in data["message"]

    status, data = api(
        "GET",
        f"sources/{public_source.id}/phot_stat",
        token=upload_data_token,
        data={},
    )
    assert status == 200
    # super user can delete the phot stats
    status, data = api(
        "DELETE", f"sources/{public_source.id}/phot_stat", token=super_admin_token
    )
    assert status == 200

    # normal user cannot post a phot stat
    status, data = api(
        "POST",
        f"sources/{public_source.id}/phot_stat",
        token=upload_data_token,
        data={},
    )
    assert status == 401
    assert "Unauthorized" in data["message"]

    # super user can post a phot stat
    status, data = api(
        "POST",
        f"sources/{public_source.id}/phot_stat",
        token=super_admin_token,
        data={},
    )
    assert status == 200

    status, data = api(
        "GET",
        f"sources/{public_source.id}/phot_stat",
        token=upload_data_token,
        data={},
    )
    assert status == 200
    # super admin cannot re-post a phot stat

    status, data = api(
        "POST",
        f"sources/{public_source.id}/phot_stat",
        token=super_admin_token,
        data={},
    )
    assert status == 400
    assert "already exists" in data["message"]


def test_delete_phot_stat_does_not_cascade(
    upload_data_token, super_admin_token, public_source
):
    status, data = api(
        "GET",
        f"sources/{public_source.id}/photometry",
        token=upload_data_token,
    )
    assert status == 200
    phot_ids = [p["id"] for p in data["data"]]

    status, data = api(
        "DELETE", f"sources/{public_source.id}/phot_stat", token=super_admin_token
    )
    assert status == 200

    status, data = api(
        "GET",
        f"sources/{public_source.id}/phot_stat",
        token=upload_data_token,
        data={},
    )
    assert status == 400

    status, data = api(
        "GET",
        f"sources/{public_source.id}",
        token=upload_data_token,
    )
    assert status == 200
    assert data["data"]["id"] == public_source.id

    status, data = api(
        "GET",
        f"sources/{public_source.id}/photometry",
        token=upload_data_token,
    )
    assert status == 200
    assert {p["id"] for p in data["data"]} == set(phot_ids)


def test_phot_stats_simple_lightcurve(
    upload_data_token, super_admin_token, public_source, public_group, ztf_camera
):
    source_id = str(uuid.uuid4())
    status, data = api(
        "POST",
        "sources",
        data={
            "id": source_id,
            "ra": np.random.uniform(0, 360),
            "dec": np.random.uniform(-90, 90),
            "redshift": np.random.uniform(0, 1),
            "group_ids": [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data["status"] == "success"

    mjd = np.linspace(57000, 57100, 5)
    flux = np.array([10.0, 110.0, 170.0, 180.0, 100.0])
    mjd = mjd[::-1]
    flux = flux[::-1]

    # post all these points
    for i in range(len(mjd)):
        status, data = api(
            "POST",
            "photometry",
            data={
                "obj_id": source_id,
                "mjd": mjd[i],
                "instrument_id": ztf_camera.id,
                "flux": flux[i],
                "fluxerr": 10.0,
                "zp": 25.0,
                "magsys": "ab",
                "filter": "ztfr",
                "group_ids": [public_group.id],
                "altdata": {"some_key": str(uuid.uuid4())},
            },
            token=upload_data_token,
        )
        if status != 200:
            print(data)
        assert status == 200
        assert data["status"] == "success"

    status, data = api(
        "GET",
        f"sources/{source_id}/photometry",
        token=upload_data_token,
    )
    assert status == 200
    photometry = data["data"]

    # get the magnitudes, detections, and limits
    # in the order of MJD, not the order they were posted
    phot_dict = {p["mjd"]: p for p in photometry}
    mag = []
    det = []
    lim = []
    filt = []
    for j in mjd:
        assert j in phot_dict
        mag.append(phot_dict[j]["mag"])
        det.append(phot_dict[j]["snr"] > PHOT_DETECTION_THRESHOLD)
        lim.append(phot_dict[j]["limiting_mag"])
        filt.append(phot_dict[j]["filter"])

    mag = np.array(mag)
    det = np.array(det)
    lim = np.array(lim)
    filt = np.array(filt)
    assert all(isinstance(m, float) and not np.isnan(m) for m in mag)
    print(f"mags: {mag}")

    # get the photometry stats
    status, data = api(
        "GET",
        f"sources/{source_id}/phot_stat",
        token=upload_data_token,
    )
    assert status == 200
    phot_stat = data["data"]

    check_phot_stat_is_consistent(phot_stat, mjd, mag, filt, det, lim)


def test_phot_stats_for_public_source(upload_data_token, public_source):
    status, data = api(
        "GET",
        f"sources/{public_source.id}/photometry",
        token=upload_data_token,
    )
    assert status == 200
    photometry = data["data"]
    mag = [p["mag"] for p in photometry]
    assert all(isinstance(m, float) and not np.isnan(m) for m in mag)
    mag = np.array(mag)
    mjd = np.array([p["mjd"] for p in photometry])
    filt = np.array([p["filter"] for p in photometry])
    det = np.array([p["snr"] > PHOT_DETECTION_THRESHOLD for p in photometry])
    lim = np.array([p["limiting_mag"] for p in photometry])

    status, data = api(
        "GET",
        f"sources/{public_source.id}/phot_stat",
        token=upload_data_token,
        data={},
    )
    assert status == 200
    check_phot_stat_is_consistent(data["data"], mjd, mag, filt, det, lim)


def test_phot_stat_consistent(
    upload_data_token, super_admin_token, public_group, ztf_camera
):
    source_id = str(uuid.uuid4())
    status, data = api(
        "POST",
        "sources",
        data={
            "id": source_id,
            "ra": np.random.uniform(0, 360),
            "dec": np.random.uniform(-90, 90),
            "redshift": np.random.uniform(0, 1),
            "group_ids": [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data["status"] == "success"

    num_points = 20
    mjd = np.random.uniform(55000, 56000, num_points)
    mjd.sort()

    flux = np.random.normal(300, 10, num_points)
    flux[0:5] = 10.1

    filt = np.random.choice(["ztfg", "ztfr", "ztfi"], num_points)

    # post all these points
    phot_ids = []
    insert_idx = list(range(num_points))
    np.random.shuffle(insert_idx)  # input data in random order

    for i in insert_idx:
        status, data = api(
            "POST",
            "photometry",
            data={
                "obj_id": source_id,
                "mjd": mjd[i],
                "instrument_id": ztf_camera.id,
                "flux": flux[i],
                "fluxerr": 10.0,
                "zp": 25.0,
                "magsys": "ab",
                "filter": filt[i],
                "group_ids": [public_group.id],
                "altdata": {"some_key": str(uuid.uuid4())},
            },
            token=upload_data_token,
        )
        if status != 200:
            print(data)
        assert status == 200
        assert data["status"] == "success"
        phot_ids.append(data["data"]["ids"][0])

    status, data = api(
        "GET",
        f"sources/{source_id}/photometry",
        token=upload_data_token,
    )
    assert status == 200
    photometry = data["data"]
    assert len(photometry) == num_points

    # get the magnitudes, detections, and limits
    # in the order of MJD, not the order they were posted
    phot_dict = {p["mjd"]: p for p in photometry}
    mag = []
    det = []
    lim = []
    for j in mjd:
        assert j in phot_dict
        mag.append(phot_dict[j]["mag"])
        det.append(phot_dict[j]["snr"] > PHOT_DETECTION_THRESHOLD)
        lim.append(phot_dict[j]["limiting_mag"])

    mag = np.array(mag)
    det = np.array(det)
    lim = np.array(lim)
    assert all(isinstance(m, float) and not np.isnan(m) for m in mag)
    assert np.sum(det) == num_points - 5

    status, data = api(
        "GET",
        f"sources/{source_id}/phot_stat",
        token=upload_data_token,
    )
    assert status == 200
    phot_stat = data["data"]

    check_phot_stat_is_consistent(phot_stat, mjd, mag, filt, det, lim)

    # now re-calculate the points
    status, data = api(
        "DELETE", f"sources/{source_id}/phot_stat", token=super_admin_token
    )
    assert status == 200

    status, data = api(
        "POST", f"sources/{source_id}/phot_stat", token=super_admin_token
    )
    assert status == 200

    status, data = api(
        "GET",
        f"sources/{source_id}/phot_stat",
        token=upload_data_token,
    )
    assert status == 200
    phot_stat = data["data"]
    check_phot_stat_is_consistent(phot_stat, mjd, mag, filt, det, lim)

    # now delete a point
    status, data = api("DELETE", f"photometry/{phot_ids[6]}", token=upload_data_token)
    phot_ids.pop(6)

    assert status == 200

    idx = np.ones(num_points, dtype=bool)
    # point inserted at index 6 is some other index
    # in the lists of mjd/mag/filt/det/lim values
    idx[insert_idx[6]] = False
    mjd_less = mjd[idx]
    mag_less = mag[idx]
    filt_less = filt[idx]
    det_less = det[idx]
    lim_less = lim[idx]

    status, data = api("GET", f"sources/{source_id}/phot_stat", token=upload_data_token)

    assert status == 200
    phot_stat = data["data"]

    check_phot_stat_is_consistent(
        phot_stat, mjd_less, mag_less, filt_less, det_less, lim_less
    )

    # re-add that photometry point to check that the phot_stat updates
    status, data = api(
        "POST",
        "photometry",
        data={
            "obj_id": source_id,
            "mjd": mjd[insert_idx[6]],
            "instrument_id": ztf_camera.id,
            "flux": flux[insert_idx[6]],
            "fluxerr": 10.0,
            "zp": 25.0,
            "magsys": "ab",
            "filter": filt[insert_idx[6]],
            "group_ids": [public_group.id],
            "altdata": {"some_key": str(uuid.uuid4())},
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data["status"] == "success"
    phot_ids.insert(6, data["data"]["ids"][0])

    status, data = api("GET", f"sources/{source_id}/phot_stat", token=upload_data_token)

    assert status == 200
    phot_stat = data["data"]

    check_phot_stat_is_consistent(phot_stat, mjd, mag, filt, det, lim)

    # modify one of the points and see if it updates
    flux[2] = 700.2
    status, data = api(
        "PATCH",
        f"photometry/{phot_ids[insert_idx.index(2)]}",
        data={
            "obj_id": source_id,
            "mjd": mjd[2],
            "instrument_id": ztf_camera.id,
            "flux": flux[2],
            "fluxerr": 10.0,
            "zp": 25.0,
            "magsys": "ab",
            "filter": filt[2],
            "group_ids": [public_group.id],
            "altdata": {"some_key": str(uuid.uuid4())},
        },
        token=upload_data_token,
    )
    assert status == 200

    status, data = api(
        "GET", f"photometry/{phot_ids[insert_idx.index(2)]}", token=upload_data_token
    )
    assert status == 200
    assert mjd[2] == data["data"]["mjd"]
    mag[2] = data["data"]["mag"]
    det[2] = data["data"]["snr"] > PHOT_DETECTION_THRESHOLD

    status, data = api("GET", f"sources/{source_id}/phot_stat", token=upload_data_token)
    assert status == 200
    phot_stat = data["data"]

    check_phot_stat_is_consistent(phot_stat, mjd, mag, filt, det, lim)

    # add another photometry point via PUT
    flux = np.append(flux, np.random.normal(500, 10, 1))
    filt = np.append(filt, np.random.choice(["ztfg", "ztfr", "ztfi"], 1))

    status, data = api(
        "POST",
        "photometry",
        data={
            "obj_id": source_id,
            "mjd": 58000.0 + np.random.rand() * 100,
            "instrument_id": ztf_camera.id,
            "flux": flux[-1],
            "fluxerr": 10.0,
            "zp": 25.0,
            "magsys": "ab",
            "filter": filt[-1],
            "group_ids": [public_group.id],
            "altdata": {"some_key": str(uuid.uuid4())},
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data["status"] == "success"
    phot_ids.append(data["data"]["ids"][0])

    status, data = api("GET", f"photometry/{phot_ids[-1]}", token=upload_data_token)
    assert status == 200
    mag = np.append(mag, data["data"]["mag"])
    mjd = np.append(mjd, data["data"]["mjd"])
    det = np.append(det, True)
    lim = np.append(lim, mag[-1])

    status, data = api("GET", f"sources/{source_id}/phot_stat", token=upload_data_token)
    assert status == 200
    phot_stat = data["data"]

    check_phot_stat_is_consistent(phot_stat, mjd, mag, filt, det, lim)


def test_phot_stats_update_handler(
    upload_data_token, super_admin_token, public_group, ztf_camera
):
    num_sources = 4
    num_points = 5
    source_ids = []

    # keep track of when we started posting
    t0 = datetime.utcnow()

    for j in range(num_sources):
        source_ids.append(str(uuid.uuid4()))
        status, data = api(
            "POST",
            "sources",
            data={
                "id": source_ids[-1],
                "ra": np.random.uniform(0, 360),
                "dec": np.random.uniform(-90, 90),
                "redshift": np.random.uniform(0, 1),
                "group_ids": [public_group.id],
            },
            token=upload_data_token,
        )
        assert status == 200
        assert data["status"] == "success"

        # post some photometry for each source
        mjd = np.random.uniform(55000, 56000, num_points)
        mjd.sort()

        flux = np.random.normal(300, 10, num_points)
        flux[0:5] = 10.1

        filt = np.random.choice(["ztfg", "ztfr", "ztfi"], num_points)

        for i in range(num_points):
            status, data = api(
                "POST",
                "photometry",
                data={
                    "obj_id": source_ids[-1],
                    "mjd": mjd[i],
                    "instrument_id": ztf_camera.id,
                    "flux": flux[i],
                    "fluxerr": 10.0,
                    "zp": 25.0,
                    "magsys": "ab",
                    "filter": filt[i],
                    "group_ids": [public_group.id],
                    "altdata": {"some_key": str(uuid.uuid4())},
                },
                token=upload_data_token,
            )
            if status != 200:
                print(data)
            assert status == 200
            assert data["status"] == "success"

    # get all Objs with or without PhotStats
    status, data = api(
        "GET",
        "phot_stats",
        token=super_admin_token,
    )
    assert status == 200
    num_sources_total = data["data"]["totalWithPhotStats"]

    # get only the recent ones posted in this test
    status, data = api(
        "GET",
        "phot_stats",
        params={
            "createdAtStartTime": t0.isoformat(),
        },
        token=super_admin_token,
    )
    assert status == 200
    assert data["data"]["totalWithPhotStats"] == num_sources
    assert data["data"]["totalWithoutPhotStats"] == 0

    # get only sources posted before this test
    status, data = api(
        "GET",
        "phot_stats",
        params={
            "createdAtEndTime": t0.isoformat(),
            "fullUpdateEndTime": t0.isoformat(),
        },
        token=super_admin_token,
    )
    assert status == 200
    assert data["data"]["totalWithPhotStats"] == num_sources_total - num_sources

    # delete the phot stats from one object
    status, data = api(
        "DELETE",
        f"sources/{source_ids[0]}/phot_stat",
        token=super_admin_token,
    )
    assert status == 200

    status, data = api(
        "GET",
        "phot_stats",
        token=super_admin_token,
    )

    assert status == 200
    assert data["data"]["totalWithPhotStats"] == num_sources_total - 1

    # get only the recent ones posted in this test
    status, data = api(
        "GET",
        "phot_stats",
        params={"createdAtStartTime": t0.isoformat()},
        token=super_admin_token,
    )
    assert status == 200
    assert data["data"]["totalWithoutPhotStats"] == 1

    # time before we re-calculate the missing PhotStats
    t1 = datetime.utcnow()

    # only update sources from this test
    # that don't have PhotStats (the deleted one)
    status, data = api(
        "POST",
        "phot_stats",
        params={
            "createdAtStartTime": t0.isoformat(),
        },
        token=super_admin_token,
    )
    assert status == 200
    assert data["data"]["totalMatches"] == 1

    # the sources in this test should now all have phot stats
    status, data = api(
        "GET",
        "phot_stats",
        params={"createdAtStartTime": t0.isoformat()},
        token=super_admin_token,
    )
    assert status == 200
    assert data["data"]["totalWithPhotStats"] == num_sources
    assert data["data"]["totalWithoutPhotStats"] == 0

    # Only one source has a phot stat updated after t1
    status, data = api(
        "GET",
        "phot_stats",
        params={
            "createdAtStartTime": t0.isoformat(),
            "fullUpdateStartTime": t1.isoformat(),
        },
        token=super_admin_token,
    )
    assert status == 200
    assert data["data"]["totalWithPhotStats"] == 1
    assert data["data"]["totalWithoutPhotStats"] == 0

    t2 = datetime.utcnow()

    # no sources have had a quick update after t2
    status, data = api(
        "GET",
        "phot_stats",
        params={
            "createdAtStartTime": t0.isoformat(),
            "quickUpdateStartTime": t2.isoformat(),
        },
        token=super_admin_token,
    )
    assert status == 200
    assert data["data"]["totalWithPhotStats"] == 0
    assert data["data"]["totalWithoutPhotStats"] == 0

    # all sources from this test have been updated before t2
    status, data = api(
        "GET",
        "phot_stats",
        params={
            "createdAtStartTime": t0.isoformat(),
            "fullUpdateEndTime": t2.isoformat(),
        },
        token=super_admin_token,
    )
    assert status == 200
    assert data["data"]["totalWithPhotStats"] == num_sources
    assert data["data"]["totalWithoutPhotStats"] == 0

    # post another photometry point to trigger quick update:
    status, data = api(
        "POST",
        "photometry",
        data={
            "obj_id": source_ids[1],
            "mjd": np.random.uniform(55000, 56000),
            "instrument_id": ztf_camera.id,
            "flux": np.random.normal(300, 10),
            "fluxerr": 10.0,
            "zp": 25.0,
            "magsys": "ab",
            "filter": np.random.choice(["ztfg", "ztfr", "ztfi"]),
            "group_ids": [public_group.id],
            "altdata": {"some_key": str(uuid.uuid4())},
        },
        token=upload_data_token,
    )
    assert status == 200

    # check that the quick update has changed the PhotStat on one object
    status, data = api(
        "GET",
        "phot_stats",
        params={
            "createdAtStartTime": t0.isoformat(),
            "quickUpdateStartTime": t2.isoformat(),
        },
        token=super_admin_token,
    )
    assert status == 200
    assert data["data"]["totalWithPhotStats"] == 1
    assert data["data"]["totalWithoutPhotStats"] == 0

    # run a full update on all new sources
    status, data = api(
        "PATCH",
        "phot_stats",
        params={
            "createdAtStartTime": t0.isoformat(),
        },
        token=super_admin_token,
    )

    assert status == 200
    assert data["data"]["totalMatches"] == num_sources

    # make sure we recover all the sources with
    # a full update time after t2
    status, data = api(
        "GET",
        "phot_stats",
        params={
            "createdAtStartTime": t0.isoformat(),
            "fullUpdateStartTime": t2.isoformat(),
        },
        token=super_admin_token,
    )
    assert status == 200
    assert data["data"]["totalWithPhotStats"] == num_sources
    assert data["data"]["totalWithoutPhotStats"] == 0

    # no sources left updated before t2
    status, data = api(
        "GET",
        "phot_stats",
        params={
            "createdAtStartTime": t0.isoformat(),
            "fullUpdateEndTime": t2.isoformat(),
        },
        token=super_admin_token,
    )
    assert status == 200
    assert data["data"]["totalWithPhotStats"] == 0
    assert data["data"]["totalWithoutPhotStats"] == 0


def test_phot_stats_bad_data(upload_data_token, public_group, ztf_camera):
    source_id = str(uuid.uuid4())

    num_points = 5
    photometry = []
    for i in range(num_points):
        new_phot = Photometry()
        new_phot.flux = np.random.normal(300, 10)
        new_phot.fluxerr = 10.0
        new_phot.filter = np.random.choice(["ztfg", "ztfr", "ztfi"])
        new_phot.mjd = np.random.uniform(55000, 56000)
        new_phot.limiting_mag = -2.5 * np.log10(5 * new_phot.fluxerr) + PHOT_ZP
        new_phot.original_user_data = {"limiting_mag": np.nan}
        photometry.append(new_phot)

    ps = PhotStat(source_id)
    ps.full_update(photometry)

    mag = [p.mag for p in photometry]
    assert all(isinstance(m, float) and not np.isnan(m) for m in mag)
    mag = np.array(mag)
    mjd = np.array([p.mjd for p in photometry])
    filt = np.array([p.filter for p in photometry])
    det = np.array([p.snr > PHOT_DETECTION_THRESHOLD for p in photometry])
    lim = np.array([p.limiting_mag for p in photometry])

    check_phot_stat_is_consistent(ps.__dict__, mjd, mag, filt, det, lim)

    # try to set a bad value for one of the photometry points
    photometry[1].fluxerr = None

    ps.full_update(photometry)
    check_dict_has_no_nans(ps.__dict__)

    # try to post each point individually
    ps2 = PhotStat(source_id)
    for p in photometry:
        ps2.add_photometry_point(p)

    check_dict_has_no_nans(ps2.__dict__)

    # remove the bad point, as this is what the PhotStat
    # logic should do internally.
    idx = np.ones(len(mjd), dtype=bool)
    idx[1] = False
    mjd = mjd[idx]
    mag = mag[idx]
    filt = filt[idx]
    det = det[idx]
    lim = lim[idx]

    check_phot_stat_is_consistent(ps.__dict__, mjd, mag, filt, det, lim)
    check_phot_stat_is_consistent(ps2.__dict__, mjd, mag, filt, det, lim)


def check_phot_stat_is_consistent(phot_stat, mjd, mag, filt, det, lim):
    filter_set = set(filt)

    try:
        # check the number of observations/detections
        assert phot_stat["num_obs_global"] == len(mjd)
        assert phot_stat["num_det_global"] == len(mag[det])

        # per filter
        for f in filter_set:
            if len(mjd[filt == f]):
                assert phot_stat["num_obs_per_filter"][f] == len(mjd[filt == f])
            if len(mjd[det & (filt == f)]):
                assert phot_stat["num_det_per_filter"][f] == len(mjd[det & (filt == f)])

        # latest observation
        assert phot_stat["recent_obs_mjd"] == np.max(mjd)

        # check the first detection
        idx = np.argmin(mjd[det])
        assert phot_stat["first_detected_mjd"] == mjd[det][idx]
        assert phot_stat["first_detected_mag"] == mag[det][idx]
        assert phot_stat["first_detected_filter"] == filt[det][idx]

        # check the last detection
        idx = np.argmax(mjd[det])
        assert phot_stat["last_detected_mjd"] == mjd[det][idx]
        assert phot_stat["last_detected_mag"] == mag[det][idx]
        assert phot_stat["last_detected_filter"] == filt[det][idx]

        # check the mag mean, peak and rms
        assert np.isclose(phot_stat["mean_mag_global"], np.mean(mag[det]))
        assert np.isclose(phot_stat["peak_mag_global"], min(mag[det]))
        assert phot_stat["peak_mjd_global"] == mjd[det][np.argmin(mag[det])]
        assert np.isclose(phot_stat["faintest_mag_global"], max(mag[det]))
        assert np.isclose(phot_stat["mag_rms_global"], np.std(mag[det]))

        for f in filter_set:
            if len(mag[det & (filt == f)]):
                assert np.isclose(
                    phot_stat["mean_mag_per_filter"][f], np.mean(mag[det & (filt == f)])
                )
                assert np.isclose(
                    phot_stat["peak_mag_per_filter"][f], min(mag[det & (filt == f)])
                )
                assert (
                    phot_stat["peak_mjd_per_filter"][f]
                    == mjd[det & (filt == f)][np.argmin(mag[det & (filt == f)])]
                )
                assert np.isclose(
                    phot_stat["faintest_mag_per_filter"][f], max(mag[det & (filt == f)])
                )
                assert np.isclose(
                    phot_stat["mag_rms_per_filter"][f], np.std(mag[det & (filt == f)])
                )

        # check the deepest limits (non-detections)
        if len(lim[~det]):
            assert phot_stat["deepest_limit_global"] == min(lim[~det])
        for f in filter_set:
            if len(lim[~det & (filt == f)]) > 0:
                assert phot_stat["deepest_limit_per_filter"][f] == min(
                    lim[~det & (filt == f)]
                )

        # check the color
        for f1 in filter_set:
            for f2 in filter_set:
                if f1 == f2:
                    continue
                if (
                    len(mag[det & (filt == f1)]) == 0
                    or len(mag[det & (filt == f2)]) == 0
                ):
                    continue
                mag1 = np.mean(mag[det & (filt == f1)])
                mag2 = np.mean(mag[det & (filt == f2)])
                assert np.isclose(phot_stat["mean_color"][f"{f1}-{f2}"], mag1 - mag2)

        date_array = np.array(
            list(zip(mjd, det, filt, mag)),
            dtype=[
                ("mjd", "float"),
                ("det", "bool"),
                ("filt", "S256"),
                ("mag", "float"),
            ],
        )
        date_array.sort(order="mjd")

        # the last non-detection:
        if all(date_array["det"] == 0):
            assert phot_stat["last_non_detection_mjd"] == date_array["mjd"][-1]
            assert phot_stat["time_to_non_detection"] is None
        else:
            idx = np.argmax(date_array["det"]) - 1
            if idx >= 0:
                assert phot_stat["last_non_detection_mjd"] == date_array["mjd"][idx]
                dt = date_array["mjd"][idx + 1] - date_array["mjd"][idx]
                assert np.isclose(phot_stat["time_to_non_detection"], dt)
            else:
                assert phot_stat["last_non_detection_mjd"] is None
                assert phot_stat["time_to_non_detection"] is None

        # rise and decay rates:
        detections = date_array[date_array["det"]]

        # check the rise rate
        first_filter = detections["filt"][0]
        first_mjd = detections["mjd"][0]
        first_mag = detections["mag"][0]
        # peak in the SAME FILTER as the first detection:
        peak_idx = np.argmin(detections[detections["filt"] == first_filter]["mag"])
        peak_mjd = detections[detections["filt"] == first_filter]["mjd"][peak_idx]
        peak_mag = detections[detections["filt"] == first_filter]["mag"][peak_idx]
        if peak_mjd > first_mjd:
            rise_rate = -(peak_mag - first_mag) / (peak_mjd - first_mjd)
            assert np.isclose(phot_stat["rise_rate"], rise_rate)
        else:
            assert phot_stat["rise_rate"] is None

        # check the decay rate
        last_filter = date_array["filt"][date_array["det"]][-1]
        last_mjd = date_array["mjd"][date_array["det"]][-1]
        last_mag = date_array["mag"][date_array["det"]][-1]
        # peak in the SAME FILTER as the last detection:
        peak_idx = np.argmin(detections[detections["filt"] == last_filter]["mag"])
        peak_mjd = detections[detections["filt"] == last_filter]["mjd"][peak_idx]
        peak_mag = detections[detections["filt"] == last_filter]["mag"][peak_idx]
        if peak_mjd < last_mjd:
            decay_rate = -(peak_mag - last_mag) / (peak_mjd - last_mjd)
            assert np.isclose(phot_stat["decay_rate"], decay_rate)
        else:
            assert phot_stat["decay_rate"] is None

    except Exception as e:
        from pprint import pprint

        print("Data from photometry points:")
        print(f"mag: {mag}")
        print(f"mjd: {mjd}")
        print(f"filt: {filt}")
        print(f"det: {det}")
        print(f"lim: {lim}")
        print("PhotStat object:")
        pprint(phot_stat)
        print(traceback.format_exc())
        raise e


def check_dict_has_no_nans(some_dict):
    for k, v in some_dict.items():
        if v is not None:
            if isinstance(v, float):
                assert not np.isnan(v)
            if isinstance(v, dict):
                check_dict_has_no_nans(v)
