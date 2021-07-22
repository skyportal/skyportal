import uuid
import pytest
import numpy.testing as npt
import numpy as np
import arrow
from tdtax import taxonomy, __version__

from skyportal.tests import api
from skyportal.models import cosmo

from datetime import datetime, timezone, timedelta
from dateutil import parser


def test_source_list(view_only_token):
    status, data = api("GET", "sources", token=view_only_token)
    assert status == 200
    assert data["status"] == "success"


def test_source_existence(view_only_token, public_source):
    status, _ = api("HEAD", f"sources/{public_source.id}", token=view_only_token)
    assert status == 200

    status, _ = api("HEAD", f"sources/{public_source.id[:-1]}", token=view_only_token)

    assert status == 404


def test_token_user_retrieving_source(view_only_token, public_source):
    status, data = api("GET", f"sources/{public_source.id}", token=view_only_token)
    assert status == 200
    assert data["status"] == "success"
    assert all(
        k in data["data"] for k in ["ra", "dec", "redshift", "dm", "created_at", "id"]
    )
    assert "photometry" not in data["data"]


def test_token_user_retrieving_source_with_phot(view_only_token, public_source):
    status, data = api(
        "GET",
        f"sources/{public_source.id}",
        params={"includePhotometry": "true"},
        token=view_only_token,
    )
    assert status == 200
    assert data["status"] == "success"
    assert all(
        k in data["data"]
        for k in ["ra", "dec", "redshift", "dm", "created_at", "id", "photometry"]
    )


def test_token_user_retrieving_source_with_thumbnails(view_only_token, public_source):
    status, data = api(
        "GET",
        f"sources/{public_source.id}",
        params={"includeThumbnails": True},
        token=view_only_token,
    )
    assert status == 200
    assert data["status"] == "success"
    assert all(
        k in data["data"]
        for k in ["ra", "dec", "redshift", "dm", "created_at", "id", "thumbnails"]
    )


def test_token_user_retrieving_source_without_nested(
    view_only_token, public_group, upload_data_token
):
    obj_id1 = str(uuid.uuid4())
    obj_id2 = str(uuid.uuid4())
    status, data = api(
        "POST",
        "sources",
        data={
            "id": obj_id1,
            "ra": 234.22,
            "dec": -22.33,
            "redshift": 3,
            "group_ids": [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 200
    status, data = api(
        "POST",
        "sources",
        data={
            "id": obj_id2,
            "ra": 234.22,
            "dec": -22.33,
            "redshift": 3,
            "group_ids": [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 200

    status, data = api(
        "GET",
        "sources",
        params={"removeNested": True, "group_ids": [public_group.id]},
        token=view_only_token,
    )
    assert status == 200
    assert data["status"] == "success"
    assert len(data["data"]["sources"]) == 2
    assert all(
        k in data["data"]["sources"][0]
        for k in ["ra", "dec", "redshift", "created_at", "id"]
    )
    assert all(
        k not in data["data"]["sources"][0]
        for k in ["annotations", "groups", "thumbnails", "classifications"]
    )


def test_duplicate_sources(public_group, upload_data_token, ztf_camera):
    obj_id1 = str(uuid.uuid4())
    obj_id2 = str(uuid.uuid4())
    ra = 200.0 * np.random.random()
    dec = 90.0 * np.random.random()
    status, data = api(
        "POST",
        "sources",
        data={
            "id": obj_id1,
            "ra": ra,
            "dec": dec,
            "redshift": 3,
            "group_ids": [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 200
    status, data = api(
        "POST",
        "sources",
        data={
            "id": obj_id2,
            "ra": ra + 0.0001,
            "dec": dec + 0.0005,
            "redshift": 3,
            "group_ids": [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 200
    status, data = api(
        "POST",
        "photometry",
        data={
            "obj_id": obj_id1,
            "mjd": 59801.4,
            "instrument_id": ztf_camera.id,
            "filter": "ztfg",
            "group_ids": [public_group.id],
            "mag": 12.4,
            "magerr": 0.3,
            "limiting_mag": 22,
            "magsys": "ab",
        },
        token=upload_data_token,
    )
    assert status == 200
    status, data = api(
        "POST",
        "photometry",
        data={
            "obj_id": obj_id2,
            "mjd": 59801.3,
            "instrument_id": ztf_camera.id,
            "filter": "ztfg",
            "group_ids": [public_group.id],
            "mag": 12.4,
            "magerr": 0.3,
            "limiting_mag": 22,
            "magsys": "ab",
        },
        token=upload_data_token,
    )
    assert status == 200

    status, data = api(
        "GET",
        f"sources/{obj_id1}",
        token=upload_data_token,
    )
    assert status == 200
    assert data["status"] == "success"
    assert data["data"]["duplicates"] == [obj_id2]

    status, data = api(
        "GET",
        f"sources/{obj_id2}",
        token=upload_data_token,
    )
    assert status == 200
    assert data["status"] == "success"
    assert data["data"]["duplicates"] == [obj_id1]


def test_token_user_update_source(upload_data_token, public_source):
    status, data = api(
        "PATCH",
        f"sources/{public_source.id}",
        data={
            "ra": 234.22,
            "dec": -22.33,
            "redshift": 3,
            "transient": False,
            "ra_dis": 2.3,
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data["status"] == "success"

    status, data = api("GET", f"sources/{public_source.id}", token=upload_data_token)
    assert status == 200
    assert data["status"] == "success"
    npt.assert_almost_equal(data["data"]["ra"], 234.22)
    npt.assert_almost_equal(data["data"]["redshift"], 3.0)
    npt.assert_almost_equal(
        cosmo.luminosity_distance(3.0).value, data["data"]["luminosity_distance"]
    )


def test_distance_modulus(upload_data_token, public_source):
    status, data = api(
        "PATCH",
        f"sources/{public_source.id}",
        data={
            "ra": 234.22,
            "dec": -22.33,
            "altdata": {"dm": 28.5},
            "transient": False,
            "ra_dis": 2.3,
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data["status"] == "success"

    status, data = api("GET", f"sources/{public_source.id}", token=upload_data_token)
    assert status == 200
    assert data["status"] == "success"
    npt.assert_almost_equal(10 ** ((28.5 / 5) - 5), data["data"]["luminosity_distance"])
    npt.assert_almost_equal(28.5, data["data"]["dm"])
    npt.assert_almost_equal(
        10 ** ((28.5 / 5) - 5), data["data"]["angular_diameter_distance"]
    )


def test_parallax(upload_data_token, public_source):
    parallax = 0.001  # in arcsec = 1 kpc
    d_pc = 1 / parallax
    dm = 5.0 * np.log10(d_pc / (10.0))

    status, data = api(
        "PATCH",
        f"sources/{public_source.id}",
        data={
            "ra": 234.22,
            "dec": -22.33,
            "altdata": {"parallax": parallax},
            "transient": False,
            "ra_dis": 2.3,
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data["status"] == "success"

    status, data = api("GET", f"sources/{public_source.id}", token=upload_data_token)
    assert status == 200
    assert data["status"] == "success"

    npt.assert_almost_equal(dm, data["data"]["dm"])


def test_low_redshift(upload_data_token, public_source):
    status, data = api(
        "PATCH",
        f"sources/{public_source.id}",
        data={
            "ra": 234.22,
            "dec": -22.33,
            "transient": False,
            "ra_dis": 2.3,
            "redshift": 0.00001,
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data["status"] == "success"

    status, data = api("GET", f"sources/{public_source.id}", token=upload_data_token)
    assert status == 200
    assert data["status"] == "success"

    assert data["data"]["dm"] is None


def test_cannot_update_source_without_permission(view_only_token, public_source):
    status, data = api(
        "PATCH",
        f"sources/{public_source.id}",
        data={
            "ra": 234.22,
            "dec": -22.33,
            "redshift": 3,
            "transient": False,
            "ra_dis": 2.3,
        },
        token=view_only_token,
    )
    assert status == 400
    assert data["status"] == "error"


def test_token_user_post_new_source(upload_data_token, view_only_token, public_group):
    obj_id = str(uuid.uuid4())
    alias = str(uuid.uuid4())
    origin = str(uuid.uuid4())
    t0 = datetime.now(timezone.utc)
    status, data = api(
        "POST",
        "sources",
        data={
            "id": obj_id,
            "ra": 234.22,
            "dec": -22.33,
            "redshift": 3,
            "transient": False,
            "ra_dis": 2.3,
            "group_ids": [public_group.id],
            "alias": [alias],
            "origin": origin,
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data["data"]["id"] == obj_id

    status, data = api("GET", f"sources/{obj_id}", token=view_only_token)
    assert status == 200
    assert data["data"]["id"] == obj_id
    npt.assert_almost_equal(data["data"]["ra"], 234.22)

    saved_at = parser.parse(data["data"]["groups"][0]["saved_at"] + " UTC")
    assert abs(saved_at - t0) < timedelta(seconds=60)

    assert alias == data["data"]["alias"][0]
    assert origin == data["data"]["origin"]


def test_cannot_post_source_with_null_radec(
    upload_data_token, view_only_token, public_group
):
    obj_id = str(uuid.uuid4())
    status, data = api(
        "POST",
        "sources",
        data={
            "id": obj_id,
            "ra": None,
            "dec": None,
            "redshift": 3,
            "transient": False,
            "ra_dis": 2.3,
            "group_ids": [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 400


def test_add_source_without_group_id(upload_data_token, view_only_token, public_group):
    obj_id = str(uuid.uuid4())
    status, data = api(
        "POST",
        "sources",
        data={
            "id": obj_id,
            "ra": 234.22,
            "dec": -22.33,
            "redshift": 3,
            "transient": False,
            "ra_dis": 2.3,
        },
        token=upload_data_token,
    )
    assert status == 200
    status, data = api("GET", f"sources/{obj_id}", token=view_only_token)
    assert status == 200
    assert data["data"]["id"] == obj_id
    npt.assert_almost_equal(data["data"]["ra"], 234.22)


def test_starlist(upload_data_token, public_source):
    status, data = api(
        "PATCH",
        f"sources/{public_source.id}",
        data={"ra": 234.22, "dec": 22.33},
        token=upload_data_token,
    )
    assert status == 200
    assert data["status"] == "success"

    status, data = api(
        "GET",
        f"sources/{public_source.id}/offsets",
        params={"facility": "P200", "num_offset_stars": "1"},
        token=upload_data_token,
    )
    assert status == 200
    assert data["status"] == "success"
    assert data["data"]["noffsets"] == 1
    assert data["data"]["queries_issued"] == 1
    assert data["data"]["facility"] == "P200"
    assert "starlist_str" in data["data"]
    assert isinstance(data["data"]["starlist_info"][0]["ra"], float)

    status, data = api(
        "GET",
        f"sources/{public_source.id}/offsets",
        token=upload_data_token,
    )
    assert status == 200
    assert data["status"] == "success"
    assert data["data"]["noffsets"] == 3
    assert data["data"]["facility"] == "Keck"
    assert "starlist_str" in data["data"]
    assert isinstance(data["data"]["starlist_info"][2]["dec"], float)

    ztf_star_position = data["data"]["starlist_info"][2]["dec"]

    # use DR2 for offsets ... it should not be identical position as DR2
    status, data = api(
        "GET",
        f"sources/{public_source.id}/offsets",
        params={"use_ztfref": "false"},
        token=upload_data_token,
    )
    assert status == 200
    assert data["status"] == "success"
    assert isinstance(data["data"]["starlist_info"][2]["dec"], float)
    gaiadr2_star_position = data["data"]["starlist_info"][2]["dec"]
    with pytest.raises(AssertionError):
        npt.assert_almost_equal(gaiadr2_star_position, ztf_star_position, decimal=10)


@pytest.mark.xfail(strict=False)
def test_finder(upload_data_token, public_source):
    status, data = api(
        "PATCH",
        f"sources/{public_source.id}",
        data={"ra": 234.22, "dec": -22.33},
        token=upload_data_token,
    )
    assert status == 200
    assert data["status"] == "success"

    response = api(
        "GET",
        f"sources/{public_source.id}/finder",
        params={"imsize": "2"},
        token=upload_data_token,
        raw_response=True,
    )
    status = response.status_code
    data = response.text
    assert status == 200
    assert isinstance(data, str)
    assert data[0:10].find("PDF") != -1
    assert response.headers.get("Content-Type", "Empty").find("application/pdf") != -1

    # try an image source we dont know about
    status, data = api(
        "GET",
        f"sources/{public_source.id}/finder",
        params={"image_source": "whoknows"},
        token=upload_data_token,
    )
    assert status == 400

    # try an image too big
    status, data = api(
        "GET",
        f"sources/{public_source.id}/finder",
        params={"imsize": "30"},
        token=upload_data_token,
    )
    assert status == 400


def test_source_notifications_unauthorized(
    source_notification_user_token, public_group, public_source
):
    status, data = api(
        "POST",
        "source_notifications",
        data={
            "groupIds": [public_group.id],
            "sourceId": public_source.id,
            "level": "hard",
            "additionalNotes": "",
        },
        token=source_notification_user_token,
    )
    assert status == 400
    assert "Unauthorized" in data["message"]


def test_token_user_source_summary(
    public_group, public_source, view_only_token_two_groups, public_group2
):

    now = datetime.utcnow().isoformat()

    status, data = api(
        "GET",
        f"sources?saveSummary=true&group_ids={public_group.id}",
        token=view_only_token_two_groups,
    )
    assert status == 200
    assert "sources" in data["data"]
    sources = data["data"]["sources"]

    assert len(sources) == 1
    source = sources[0]
    assert "ra" not in source
    assert "dec" not in source

    assert source["obj_id"] == public_source.id
    assert source["group_id"] == public_group.id

    status, data = api(
        "GET",
        "sources",
        params={
            "saveSummary": "true",
            "savedAfter": f"{now}",
            "group_ids": f"{public_group.id}",
        },
        token=view_only_token_two_groups,
    )
    assert status == 200
    assert "sources" in data["data"]
    sources = data["data"]["sources"]

    assert len(sources) == 0

    status, data = api(
        "GET",
        "sources",
        params={"saveSummary": "true", "group_ids": f"{public_group2.id}"},
        token=view_only_token_two_groups,
    )
    assert status == 200
    assert "sources" in data["data"]
    sources = data["data"]["sources"]
    assert len(sources) == 0

    status, data = api(
        "GET",
        "sources",
        params={
            "saveSummary": "true",
            "savedBefore": f"{now}",
            "group_ids": f"{public_group.id}",
        },
        token=view_only_token_two_groups,
    )
    assert status == 200
    assert "sources" in data["data"]
    sources = data["data"]["sources"]

    assert len(sources) == 1
    source = sources[0]

    assert source["obj_id"] == public_source.id
    assert source["group_id"] == public_group.id

    # check the datetime formatting is properly validated
    status, data = api(
        "GET",
        "sources",
        params={
            "saveSummary": "true",
            "savedBefore": "2020-104-01T00:00:01.2412",
            "group_ids": f"{public_group.id}",
        },
        token=view_only_token_two_groups,
    )
    assert status == 400


def test_sources_sorting(upload_data_token, view_only_token, public_group):
    obj_id = str(uuid.uuid4())
    obj_id2 = str(uuid.uuid4())
    ra1 = 230
    ra2 = 240

    # Upload two new sources
    status, data = api(
        "POST",
        "sources",
        data={
            "id": obj_id,
            "ra": ra1,
            "dec": -22.33,
            "redshift": 3,
            "transient": False,
            "ra_dis": 2.3,
            "group_ids": [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data["data"]["id"] == obj_id
    status, data = api(
        "POST",
        "sources",
        data={
            "id": obj_id2,
            "ra": ra2,
            "dec": -22.33,
            "redshift": 3,
            "transient": False,
            "ra_dis": 2.3,
            "group_ids": [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data["data"]["id"] == obj_id2

    # Sort sources by ra, desc and check that source 2 is first
    status, data = api(
        "GET",
        "sources",
        params={"sortBy": "ra", "sortOrder": "desc", "group_ids": f"{public_group.id}"},
        token=view_only_token,
    )
    assert status == 200
    assert data["data"]["sources"][0]["id"] == obj_id2
    npt.assert_almost_equal(data["data"]["sources"][0]["ra"], ra2)
    assert data["data"]["sources"][1]["id"] == obj_id
    npt.assert_almost_equal(data["data"]["sources"][1]["ra"], ra1)


def test_object_last_detected(
    upload_data_token,
    view_only_token,
    public_source,
    ztf_camera,
    public_group,
    upload_data_token_two_groups,
    public_group2,
):
    # Some very high mjd to make this the latest point
    # This is not a detection though
    status, data = api(
        'POST',
        'photometry',
        data={
            'obj_id': str(public_source.id),
            'mjd': 99999.0,
            'instrument_id': ztf_camera.id,
            'mag': None,
            'magerr': None,
            'limiting_mag': 22.3,
            'magsys': 'ab',
            'filter': 'ztfg',
            'group_ids': [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data['status'] == 'success'

    # Another high mjd, but this time a photometry point not visible to the user
    status, data = api(
        'POST',
        'photometry',
        data={
            'obj_id': str(public_source.id),
            'mjd': 99900.0,
            'instrument_id': ztf_camera.id,
            'mag': None,
            'magerr': None,
            'limiting_mag': 22.3,
            'magsys': 'ab',
            'filter': 'ztfg',
            'group_ids': [public_group2.id],
        },
        token=upload_data_token_two_groups,
    )
    assert status == 200
    assert data['status'] == 'success'

    # A high mjd, but lower than the first point
    # Since this is a detection, it should be returned as "last_detected"
    status, data = api(
        'POST',
        'photometry',
        data={
            'obj_id': str(public_source.id),
            'mjd': 90000.0,
            'instrument_id': ztf_camera.id,
            'flux': 12.24,
            'fluxerr': 0.031,
            'zp': 25.0,
            'magsys': 'ab',
            'filter': 'ztfg',
            'group_ids': [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data['status'] == 'success'

    status, data = api(
        "GET",
        f"sources/{public_source.id}",
        params={"includeDetectionStats": "true"},
        token=view_only_token,
    )
    assert status == 200
    assert data["status"] == "success"
    assert (
        data["data"]["last_detected_at"]
        == arrow.get((90000.0 - 40_587) * 86400.0).isoformat()
    )


def test_source_photometry_summary_info(
    upload_data_token, view_only_token, public_source_no_data, ztf_camera, public_group
):
    pt1 = {"mjd": 58001.0, "flux": 13.24}
    pt2 = {"mjd": 58002.0, "flux": 15.24}
    status, data = api(
        'POST',
        'photometry',
        data={
            'obj_id': str(public_source_no_data.id),
            'mjd': [pt1["mjd"], pt2["mjd"]],
            'instrument_id': ztf_camera.id,
            'flux': [pt1["flux"], pt2["flux"]],
            'fluxerr': [0.031, 0.031],
            'filter': ['ztfg', 'ztfg'],
            'zp': [25.0, 25.0],
            'magsys': ['ab', 'ab'],
            'ra': 264.1947917,
            'dec': [50.5478333, 50.5478333],
            'dec_unc': 0.2,
            'group_ids': [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data["status"] == "success"
    assert len(data["data"]["ids"]) == 2

    mag1_ab = -2.5 * np.log10(pt1["flux"]) + 25.0
    iso1 = arrow.get((pt1["mjd"] - 40_587) * 86400.0).isoformat()
    mag2_ab = -2.5 * np.log10(pt2["flux"]) + 25.0
    iso2 = arrow.get((pt2["mjd"] - 40_587) * 86400.0).isoformat()

    status, data = api(
        "GET",
        f"sources/{public_source_no_data.id}",
        params={"includeDetectionStats": "true"},
        token=view_only_token,
    )
    assert status == 200
    assert data["status"] == "success"
    assert data["data"]["last_detected_at"] == iso2
    assert data["data"]["last_detected_mag"] == mag2_ab
    assert data["data"]["peak_detected_at"] == iso1
    assert data["data"]["peak_detected_mag"] == mag1_ab


# Sources filtering tests
def test_sources_filter_by_name_or_id(upload_data_token, view_only_token, public_group):
    obj_id = "test_source_1"
    obj_id2 = "some_other_object"

    # Upload two new sources
    status, data = api(
        "POST",
        "sources",
        data={"id": obj_id, "ra": 230, "dec": -22.33, "group_ids": [public_group.id]},
        token=upload_data_token,
    )
    assert status == 200
    assert data["data"]["id"] == obj_id
    status, data = api(
        "POST",
        "sources",
        data={"id": obj_id2, "ra": 230, "dec": -22.33, "group_ids": [public_group.id]},
        token=upload_data_token,
    )
    assert status == 200
    assert data["data"]["id"] == obj_id2

    # Filter for obj 1 only, using a substring not matched in the other one
    status, data = api(
        "GET",
        "sources",
        params={"sourceID": f"{obj_id[0:5]}", "group_ids": f"{public_group.id}"},
        token=view_only_token,
    )
    assert status == 200
    assert len(data["data"]["sources"]) == 1
    assert data["data"]["sources"][0]["id"] == obj_id


def test_sources_filter_by_position(upload_data_token, view_only_token, public_group):
    obj_id1 = str(uuid.uuid4())
    obj_id2 = str(uuid.uuid4())

    # Upload two new sources
    status, data = api(
        "POST",
        "sources",
        data={"id": obj_id1, "ra": 230, "dec": -22.33, "group_ids": [public_group.id]},
        token=upload_data_token,
    )
    assert status == 200
    assert data["data"]["id"] == obj_id1
    status, data = api(
        "POST",
        "sources",
        data={"id": obj_id2, "ra": 500, "dec": 0, "group_ids": [public_group.id]},
        token=upload_data_token,
    )
    assert status == 200
    assert data["data"]["id"] == obj_id2

    # Filter for obj 1 only
    status, data = api(
        "GET",
        "sources",
        params={"ra": 229, "dec": -22, "radius": 5, "group_ids": f"{public_group.id}"},
        token=view_only_token,
    )
    assert status == 200
    assert len(data["data"]["sources"]) == 1
    assert data["data"]["sources"][0]["id"] == obj_id1


def test_sources_filter_by_time_saved(upload_data_token, view_only_token, public_group):
    obj_id1 = str(uuid.uuid4())
    obj_id2 = str(uuid.uuid4())

    # Upload two new sources
    status, data = api(
        "POST",
        "sources",
        data={
            "id": obj_id1,
            "ra": 234.22,
            "dec": -22.33,
            "group_ids": [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data["data"]["id"] == obj_id1
    t = datetime.now(timezone.utc)
    status, data = api(
        "POST",
        "sources",
        data={
            "id": obj_id2,
            "ra": 234.22,
            "dec": -22.33,
            "group_ids": [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data["data"]["id"] == obj_id2

    # Filter for obj 1 only
    status, data = api(
        "GET",
        "sources",
        params={"savedBefore": t.isoformat(), "group_ids": f"{public_group.id}"},
        token=view_only_token,
    )
    assert status == 200
    assert len(data["data"]["sources"]) == 1
    assert data["data"]["sources"][0]["id"] == obj_id1

    # Filter for obj 2 only
    status, data = api(
        "GET",
        "sources",
        params={"savedAfter": t.isoformat(), "group_ids": f"{public_group.id}"},
        token=view_only_token,
    )
    assert status == 200
    assert len(data["data"]["sources"]) == 1
    assert data["data"]["sources"][0]["id"] == obj_id2


def test_sources_filter_by_last_detected(
    upload_data_token, view_only_token, public_group, ztf_camera
):
    obj_id1 = str(uuid.uuid4())
    obj_id2 = str(uuid.uuid4())

    # Upload two new sources
    status, data = api(
        "POST",
        "sources",
        data={
            "id": obj_id1,
            "ra": 234.22,
            "dec": -22.33,
            "group_ids": [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data["data"]["id"] == obj_id1

    status, data = api(
        "POST",
        "sources",
        data={
            "id": obj_id2,
            "ra": 234.22,
            "dec": -22.33,
            "group_ids": [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data["data"]["id"] == obj_id2

    # Add a detection to obj 1
    status, data = api(
        'POST',
        'photometry',
        data={
            'obj_id': obj_id1,
            'mjd': [59000.0],
            'instrument_id': ztf_camera.id,
            'flux': 12.24,
            'fluxerr': 0.031,
            'zp': 25.0,
            'magsys': 'ab',
            'filter': 'ztfg',
            'group_ids': [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data['status'] == 'success'

    # Filter for obj 1 only
    status, data = api(
        "GET",
        "sources",
        params={
            "startDate": arrow.get((58500 - 40_587) * 86400.0).isoformat(),
            "group_ids": f"{public_group.id}",
        },
        token=view_only_token,
    )
    assert status == 200
    assert len(data["data"]["sources"]) == 1
    assert data["data"]["sources"][0]["id"] == obj_id1

    status, data = api(
        "GET",
        "sources",
        params={
            "endDate": arrow.get((59000 - 40_587) * 86400.0).isoformat(),
            "group_ids": f"{public_group.id}",
        },
        token=view_only_token,
    )
    assert status == 200
    assert len(data["data"]["sources"]) == 1
    assert data["data"]["sources"][0]["id"] == obj_id1


def test_sources_filter_by_simbad_class(
    upload_data_token, view_only_token, public_group
):
    obj_id1 = str(uuid.uuid4())
    obj_id2 = str(uuid.uuid4())
    simbad_class = str(uuid.uuid4())

    # Upload two new sources
    status, data = api(
        "POST",
        "sources",
        data={
            "id": obj_id1,
            "ra": 234.22,
            "dec": -22.33,
            "altdata": {"simbad": {"class": simbad_class}},
            "group_ids": [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data["data"]["id"] == obj_id1

    status, data = api(
        "POST",
        "sources",
        data={
            "id": obj_id2,
            "ra": 234.22,
            "dec": -22.33,
            "group_ids": [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data["data"]["id"] == obj_id2

    # Filter for obj 1 only
    status, data = api(
        "GET",
        "sources",
        params={"simbadClass": simbad_class, "group_ids": f"{public_group.id}"},
        token=view_only_token,
    )
    assert status == 200
    assert len(data["data"]["sources"]) == 1
    assert data["data"]["sources"][0]["id"] == obj_id1


def test_sources_filter_by_classifications(
    upload_data_token,
    taxonomy_token,
    classification_token,
    view_only_token,
    public_group,
):
    # Post a source with a classification, and one without
    obj_id1 = str(uuid.uuid4())
    obj_id2 = str(uuid.uuid4())
    status, data = api(
        "POST",
        "sources",
        data={
            "id": obj_id1,
            "ra": 234.22,
            "dec": -22.33,
            "group_ids": [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 200
    status, data = api(
        "POST",
        "sources",
        data={
            "id": obj_id2,
            "ra": 234.22,
            "dec": -22.33,
            "group_ids": [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 200

    taxonomy_name = "test taxonomy" + str(uuid.uuid4())
    status, data = api(
        "POST",
        "taxonomy",
        data={
            "name": taxonomy_name,
            "hierarchy": taxonomy,
            "group_ids": [public_group.id],
            "provenance": f"tdtax_{__version__}",
            "version": __version__,
            "isLatest": True,
        },
        token=taxonomy_token,
    )
    assert status == 200
    taxonomy_id = data["data"]["taxonomy_id"]

    status, data = api(
        "POST",
        "classification",
        data={
            "obj_id": obj_id1,
            "classification": "Algol",
            "taxonomy_id": taxonomy_id,
            "probability": 1.0,
            "group_ids": [public_group.id],
        },
        token=classification_token,
    )
    assert status == 200

    # Filter for sources with classification "Algol" - should only get obj_id1 back
    status, data = api(
        "GET",
        "sources",
        params={
            "classifications": f"{taxonomy_name}: Algol",
            "group_ids": f"{public_group.id}",
        },
        token=view_only_token,
    )
    assert status == 200
    assert len(data["data"]["sources"]) == 1
    assert data["data"]["sources"][0]["id"] == obj_id1


def test_sources_filter_by_redshift(upload_data_token, view_only_token, public_group):
    obj_id1 = str(uuid.uuid4())
    obj_id2 = str(uuid.uuid4())

    # Upload two new sources
    status, data = api(
        "POST",
        "sources",
        data={
            "id": obj_id1,
            "ra": 234.22,
            "dec": -22.33,
            "redshift": 3,
            "group_ids": [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data["data"]["id"] == obj_id1

    status, data = api(
        "POST",
        "sources",
        data={
            "id": obj_id2,
            "ra": 234.22,
            "dec": -22.33,
            "redshift": 1,
            "group_ids": [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data["data"]["id"] == obj_id2

    # Filter for obj 1 only
    status, data = api(
        "GET",
        "sources",
        params={"minRedshift": 2, "group_ids": f"{public_group.id}"},
        token=view_only_token,
    )
    assert status == 200
    assert len(data["data"]["sources"]) == 1
    assert data["data"]["sources"][0]["id"] == obj_id1

    # Filter for obj 2 only
    status, data = api(
        "GET",
        "sources",
        params={"maxRedshift": 2, "group_ids": f"{public_group.id}"},
        token=view_only_token,
    )
    assert status == 200
    assert len(data["data"]["sources"]) == 1
    assert data["data"]["sources"][0]["id"] == obj_id2


def test_sources_filter_by_peak_mag(
    upload_data_token, view_only_token, public_group, ztf_camera
):
    obj_id1 = str(uuid.uuid4())
    obj_id2 = str(uuid.uuid4())

    # Upload two new sources with differing large mags
    status, data = api(
        "POST",
        "sources",
        data={
            "id": obj_id1,
            "ra": 234.22,
            "dec": -22.33,
            "group_ids": [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data["data"]["id"] == obj_id1

    status, data = api(
        'POST',
        'photometry',
        data={
            'obj_id': obj_id1,
            'mjd': 58000.0,
            'instrument_id': ztf_camera.id,
            'mag': 55,
            'magerr': 0.1,
            'limiting_mag': 22.3,
            'magsys': 'ab',
            'filter': 'ztfg',
            'group_ids': [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data['status'] == 'success'

    status, data = api(
        "POST",
        "sources",
        data={
            "id": obj_id2,
            "ra": 234.22,
            "dec": -22.33,
            "group_ids": [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data["data"]["id"] == obj_id2

    status, data = api(
        'POST',
        'photometry',
        data={
            'obj_id': obj_id2,
            'mjd': 58000.0,
            'instrument_id': ztf_camera.id,
            'mag': 50,
            'magerr': 0.1,
            'limiting_mag': 22.3,
            'magsys': 'ab',
            'filter': 'ztfg',
            'group_ids': [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data['status'] == 'success'

    # Filter for obj 1 only
    status, data = api(
        "GET",
        "sources",
        params={"minPeakMagnitude": 51, "group_ids": f"{public_group.id}"},
        token=view_only_token,
    )
    assert status == 200
    assert len(data["data"]["sources"]) == 1
    assert data["data"]["sources"][0]["id"] == obj_id1

    # Filter for obj 2 only
    status, data = api(
        "GET",
        "sources",
        params={"maxPeakMagnitude": 51, "group_ids": f"{public_group.id}"},
        token=view_only_token,
    )
    assert status == 200
    assert len(data["data"]["sources"]) == 1
    assert data["data"]["sources"][0]["id"] == obj_id2


def test_sources_filter_by_latest_mag(
    upload_data_token, view_only_token, public_group, ztf_camera
):
    obj_id1 = str(uuid.uuid4())
    obj_id2 = str(uuid.uuid4())

    # Upload two new sources with differing latest mags
    status, data = api(
        "POST",
        "sources",
        data={
            "id": obj_id1,
            "ra": 234.22,
            "dec": -22.33,
            "group_ids": [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data["data"]["id"] == obj_id1

    status, data = api(
        'POST',
        'photometry',
        data={
            'obj_id': obj_id1,
            'mjd': 59000.0,
            'instrument_id': ztf_camera.id,
            'mag': 25,
            'magerr': 0.1,
            'limiting_mag': 22.3,
            'magsys': 'ab',
            'filter': 'ztfg',
            'group_ids': [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data['status'] == 'success'

    status, data = api(
        "POST",
        "sources",
        data={
            "id": obj_id2,
            "ra": 234.22,
            "dec": -22.33,
            "group_ids": [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data["data"]["id"] == obj_id2

    status, data = api(
        'POST',
        'photometry',
        data={
            'obj_id': obj_id2,
            'mjd': 59000.0,
            'instrument_id': ztf_camera.id,
            'mag': 22,
            'magerr': 0.1,
            'limiting_mag': 22.3,
            'magsys': 'ab',
            'filter': 'ztfg',
            'group_ids': [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data['status'] == 'success'

    # Filter for obj 1 only
    status, data = api(
        "GET",
        "sources",
        params={"minLatestMagnitude": 23, "group_ids": f"{public_group.id}"},
        token=view_only_token,
    )
    assert status == 200
    assert len(data["data"]["sources"]) == 1
    assert data["data"]["sources"][0]["id"] == obj_id1

    # Filter for obj 2 only
    status, data = api(
        "GET",
        "sources",
        params={"maxLatestMagnitude": 23, "group_ids": f"{public_group.id}"},
        token=view_only_token,
    )
    assert status == 200
    assert len(data["data"]["sources"]) == 1
    assert data["data"]["sources"][0]["id"] == obj_id2


def test_sources_filter_by_has_tns_name(
    upload_data_token, view_only_token, public_group
):
    obj_id1 = str(uuid.uuid4())
    obj_id2 = str(uuid.uuid4())

    # Upload two new sources
    status, data = api(
        "POST",
        "sources",
        data={
            "id": obj_id1,
            "ra": 234.22,
            "dec": -22.33,
            "altdata": {"tns": {"name": "test_tns_name"}},
            "group_ids": [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data["data"]["id"] == obj_id1

    status, data = api(
        "POST",
        "sources",
        data={
            "id": obj_id2,
            "ra": 234.22,
            "dec": -22.33,
            "group_ids": [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data["data"]["id"] == obj_id2

    # Filter for obj 1 only
    status, data = api(
        "GET",
        "sources",
        params={"hasTNSname": "true", "group_ids": f"{public_group.id}"},
        token=view_only_token,
    )
    assert status == 200
    assert len(data["data"]["sources"]) == 1
    assert data["data"]["sources"][0]["id"] == obj_id1


def test_sources_filter_by_has_spectrum(
    view_only_token,
    public_group,
    public_source,
    public_source_no_data,
):
    # Filter for obj 1 only, since the no data source will not have spectra
    status, data = api(
        "GET",
        "sources",
        params={"hasSpectrum": "true", "group_ids": f"{public_group.id}"},
        token=view_only_token,
    )
    assert status == 200
    assert len(data["data"]["sources"]) == 1
    assert data["data"]["sources"][0]["id"] == public_source.id


def test_sources_hidden_photometry_not_leaked(
    public_source,
    ztf_camera,
    public_group,
    public_group2,
    view_only_token,
    upload_data_token_two_groups,
):
    obj_id = str(public_source.id)
    # Post photometry to the object belonging to a different group
    status, data = api(
        'POST',
        'photometry',
        data={
            'obj_id': obj_id,
            'mjd': 58000.0,
            'instrument_id': ztf_camera.id,
            'flux': 12.24,
            'fluxerr': 0.031,
            'zp': 25.0,
            'magsys': 'ab',
            'filter': 'ztfg',
            'group_ids': [public_group2.id],
            'altdata': {'some_key': 'some_value'},
        },
        token=upload_data_token_two_groups,
    )
    assert status == 200
    assert data['status'] == 'success'
    photometry_id = data['data']['ids'][0]

    # Check the photometry sent back with the source
    status, data = api(
        "GET",
        "sources",
        params={"group_ids": f"{public_group.id}", "includePhotometry": "true"},
        token=view_only_token,
    )
    assert status == 200
    assert len(data["data"]["sources"]) == 1
    assert data["data"]["sources"][0]["id"] == obj_id
    assert len(public_source.photometry) - 1 == len(
        data["data"]["sources"][0]["photometry"]
    )
    assert photometry_id not in map(
        lambda x: x["id"], data["data"]["sources"][0]["photometry"]
    )

    # Check for single GET call as well
    status, data = api(
        "GET",
        f"sources/{obj_id}",
        params={"includePhotometry": "true"},
        token=view_only_token,
    )
    assert status == 200
    assert data["data"]["id"] == obj_id
    assert len(public_source.photometry) - 1 == len(data["data"]["photometry"])
    assert photometry_id not in map(lambda x: x["id"], data["data"]["photometry"])
