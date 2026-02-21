import base64
import os
import re
import time
import uuid

import pytest

from skyportal.models import DBSession, Obj, Thumbnail
from skyportal.tests import api, assert_api


def test_token_user_post_get_thumbnail(upload_data_token, public_group, ztf_camera):
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
            "group_ids": [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data["data"]["id"] == obj_id

    # wait for the thumbnails to populate
    nretries = 0
    thumbnails_loaded = False
    thumbnails = []

    # wait for the thumbnails to populate, get the source
    while nretries < 30:
        # we put the sleep first, knowing that we will have to wait before the first try could be successful anyway
        time.sleep(10)
        status, data = api(
            "GET", f"sources/{obj_id}?includeThumbnails=true", token=upload_data_token
        )
        thumbnails = data.get("data", {}).get("thumbnails", [])
        if isinstance(thumbnails, list) and len(thumbnails) == 3:
            thumbnails_loaded = True
            break
        nretries += 1

    assert thumbnails_loaded

    orig_source_thumbnail_count = len(thumbnails)
    data = base64.b64encode(
        open(os.path.abspath("skyportal/tests/data/14gqr_new.png"), "rb").read()
    )
    ttype = "new"
    status, data = api(
        "POST",
        "thumbnail",
        data={"obj_id": obj_id, "data": data, "ttype": ttype},
        token=upload_data_token,
    )
    assert status == 200
    assert data["status"] == "success"
    thumbnail_id = data["data"]["id"]
    assert isinstance(thumbnail_id, int)

    status, data = api("GET", f"thumbnail/{thumbnail_id}", token=upload_data_token)
    assert status == 200
    assert data["status"] == "success"
    assert data["data"]["type"] == "new"

    # wait for the thumbnails to populate, get the source
    while nretries < 5:
        status, data = api(
            "GET", f"sources/{obj_id}?includeThumbnails=true", token=upload_data_token
        )
        thumbnails = data.get("data", {}).get("thumbnails", [])
        if (
            isinstance(thumbnails, list)
            and len(thumbnails) == orig_source_thumbnail_count + 1
        ):
            thumbnails_loaded = True
            break
        nretries += 1
        time.sleep(2)

    assert thumbnails_loaded


def test_cannot_post_thumbnail_invalid_ttype(
    upload_data_token, public_group, ztf_camera
):
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
            "group_ids": [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data["data"]["id"] == obj_id

    data = base64.b64encode(
        open(os.path.abspath("skyportal/tests/data/14gqr_new.png"), "rb").read()
    )
    ttype = "invalid_ttype"
    status, data = api(
        "POST",
        "thumbnail",
        data={"obj_id": obj_id, "data": data, "ttype": ttype},
        token=upload_data_token,
    )
    assert status == 400
    assert data["status"] == "error"
    assert "is not among the defined enum values" in data["message"]


def test_cannot_post_thumbnail_invalid_image_type(
    upload_data_token, public_group, ztf_camera
):
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
            "group_ids": [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data["data"]["id"] == obj_id

    data = base64.b64encode(
        open(
            os.path.abspath("skyportal/tests/data/candid-87704463155000_ref.jpg"), "rb"
        ).read()
    )
    ttype = "ref"
    status, data = api(
        "POST",
        "thumbnail",
        data={"obj_id": obj_id, "data": data, "ttype": ttype},
        token=upload_data_token,
    )
    assert status == 400
    assert data["status"] == "error"
    assert "Invalid thumbnail image type. Only PNG are supported." in data["message"]


def test_cannot_post_thumbnail_invalid_size(
    upload_data_token, public_group, ztf_camera
):
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
            "group_ids": [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data["data"]["id"] == obj_id

    data = base64.b64encode(
        open(os.path.abspath("skyportal/tests/data/14gqr_new_13px.png"), "rb").read()
    )
    ttype = "ref"
    status, data = api(
        "POST",
        "thumbnail",
        data={"obj_id": obj_id, "data": data, "ttype": ttype},
        token=upload_data_token,
    )
    assert status == 400
    assert data["status"] == "error"
    assert "Invalid thumbnail size." in data["message"]


def test_cannot_post_thumbnail_invalid_file_type(
    upload_data_token, public_group, ztf_camera
):
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
            "group_ids": [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data["data"]["id"] == obj_id

    data = base64.b64encode(os.urandom(2048))  # invalid image data
    ttype = "ref"
    status, data = api(
        "POST",
        "thumbnail",
        data={"obj_id": obj_id, "data": data, "ttype": ttype},
        token=upload_data_token,
    )
    assert status == 400
    assert data["status"] == "error"
    assert "cannot identify image file" in data["message"]


def test_delete_thumbnail_deletes_file_on_disk(
    upload_data_token, super_admin_token, public_group
):
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
            "group_ids": [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data["data"]["id"] == obj_id

    thumbnail_data = base64.b64encode(
        open(os.path.abspath("skyportal/tests/data/14gqr_new.png"), "rb").read()
    )
    ttype = "new"
    status, data = api(
        "POST",
        "thumbnail",
        data={"obj_id": obj_id, "data": thumbnail_data, "ttype": ttype},
        token=upload_data_token,
    )
    assert status == 200
    assert data["status"] == "success"
    thumbnail_id = data["data"]["id"]
    assert isinstance(thumbnail_id, int)

    status, data = api("GET", f"thumbnail/{thumbnail_id}", token=upload_data_token)
    assert status == 200
    assert data["status"] == "success"
    assert data["data"]["type"] == ttype

    nretries = 0
    thumbnail = None
    # look for the newly created thumbnail
    while nretries < 5:
        status, data = api(
            "GET", f"sources/{obj_id}?includeThumbnails=true", token=upload_data_token
        )
        thumbnails = data.get("data", {}).get("thumbnails", [])
        if isinstance(thumbnails, list) and any(
            t["id"] == thumbnail_id for t in thumbnails
        ):
            thumbnail = next((t for t in thumbnails if t["id"] == thumbnail_id), None)
            break
        nretries += 1
        time.sleep(2)

    assert thumbnail is not None

    fpath = thumbnail["file_uri"]
    assert os.path.exists(fpath)

    status, data = api("DELETE", f"thumbnail/{thumbnail_id}", token=super_admin_token)
    assert status == 200
    assert data["status"] == "success"

    assert not os.path.exists(fpath)


def test_change_thumbnail_folder(upload_data_token, super_admin_token, public_group):
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
            "group_ids": [public_group.id],
        },
        token=upload_data_token,
    )
    assert_api(status, data)
    assert data["data"]["id"] == obj_id

    thumbnail_data = base64.b64encode(
        open(os.path.abspath("skyportal/tests/data/14gqr_new.png"), "rb").read()
    )
    ttype = "new"
    status, data = api(
        "POST",
        "thumbnail",
        data={"obj_id": obj_id, "data": thumbnail_data, "ttype": ttype},
        token=upload_data_token,
    )
    assert_api(status, data)
    thumbnail_id = data["data"]["id"]
    assert isinstance(thumbnail_id, int)

    status, data = api("GET", f"thumbnail/{thumbnail_id}", token=upload_data_token)
    assert_api(status, data)
    assert data["data"]["type"] == ttype

    status, data = api("GET", f"thumbnail/{thumbnail_id}", token=upload_data_token)
    assert_api(status, data)
    thumbnail = data["data"]
    assert thumbnail["obj_id"] == obj_id
    fpath = thumbnail["file_uri"]
    assert os.path.exists(fpath)

    # check there are exactly two subfolders of two letters
    # and those letters should be hexadecimal digits (0-9, a-f)
    subfolders2 = os.path.dirname(fpath.split("thumbnails/")[1])
    assert bool(re.match(r"^[a-f0-9]{2}/[a-f-0-9]{2}$", subfolders2))

    # now push the thumbnails to 3 levels deep
    status, data = api(
        "PATCH",
        "thumbnailPath",
        params={
            "type": ttype,
            "requiredDepth": 3,
            "numPerPage": 500,
        },
        token=super_admin_token,
    )

    assert_api(status, data)
    assert data["data"]["totalMatches"] < 500  # otherwise some are not moved!
    assert data["data"]["inWrongFolder"] == 0  # all thumbnails are updated

    # check the new folder structure
    status, data = api("GET", f"thumbnail/{thumbnail_id}", token=upload_data_token)
    assert_api(status, data)
    thumbnail = data["data"]
    assert thumbnail["obj_id"] == obj_id
    fpath = thumbnail["file_uri"]
    assert os.path.exists(fpath)
    subfolders3 = os.path.dirname(fpath.split("thumbnails/")[1])
    assert bool(re.match(r"^[a-f0-9]{2}/[a-f-0-9]{2}/[a-f-0-9]{2}$", subfolders3))

    # return the thumbnails to 2 levels deep
    status, data = api(
        "PATCH",
        "thumbnailPath",
        params={
            "type": ttype,
            "requiredDepth": 2,
            "numPerPage": 500,
        },
        token=super_admin_token,
    )

    assert_api(status, data)
    assert data["data"]["totalMatches"] < 500  # otherwise some are not moved!
    assert data["data"]["inWrongFolder"] == 0  # all thumbnails are updated

    # make sure the new folder structure is back to normal
    status, data = api("GET", f"thumbnail/{thumbnail_id}", token=upload_data_token)
    assert_api(status, data)
    thumbnail = data["data"]
    assert thumbnail["obj_id"] == obj_id
    fpath = thumbnail["file_uri"]
    assert os.path.exists(fpath)

    subfolders4 = os.path.dirname(fpath.split("thumbnails/")[1])
    assert bool(re.match(r"^[a-f0-9]{2}/[a-f-0-9]{2}$", subfolders4))
    assert subfolders2 == subfolders4

    # find the old 3 level deep folder and make sure it is empty
    old_folder = os.path.join(fpath.split("thumbnails")[0], "thumbnails", subfolders3)
    assert os.path.exists(old_folder)
    assert len(os.listdir(old_folder)) == 0

    # delete empty folders
    status, data = api("DELETE", "thumbnailPath", token=super_admin_token)
    assert_api(status, data)

    assert not os.path.exists(old_folder)


@pytest.mark.flaky(reruns=3)
def test_token_user_delete_thumbnail_cascade_source(
    upload_data_token, super_admin_token, public_group, ztf_camera
):
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
            "group_ids": [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data["data"]["id"] == obj_id

    orig_source_thumbnail_count = len(
        DBSession.query(Obj).filter(Obj.id == obj_id).first().thumbnails
    )
    data = base64.b64encode(
        open(os.path.abspath("skyportal/tests/data/14gqr_new.png"), "rb").read()
    )
    ttype = "new"
    status, data = api(
        "POST",
        "thumbnail",
        data={"obj_id": obj_id, "data": data, "ttype": ttype},
        token=upload_data_token,
    )
    assert status == 200
    assert data["status"] == "success"
    thumbnail_id = data["data"]["id"]
    assert isinstance(thumbnail_id, int)

    status, data = api("GET", f"thumbnail/{thumbnail_id}", token=upload_data_token)
    assert status == 200
    assert data["status"] == "success"
    assert data["data"]["type"] == "new"

    assert (
        DBSession.query(Thumbnail).filter(Thumbnail.id == thumbnail_id).first().obj.id
    ) == obj_id
    assert (
        len(DBSession.query(Obj).filter(Obj.id == obj_id).first().thumbnails)
        == orig_source_thumbnail_count + 1
    )

    status, data = api("DELETE", f"thumbnail/{thumbnail_id}", token=super_admin_token)
    assert status == 200
    assert data["status"] == "success"

    assert (
        len(DBSession.query(Obj).filter(Obj.id == obj_id).first().thumbnails)
        == orig_source_thumbnail_count
    )
