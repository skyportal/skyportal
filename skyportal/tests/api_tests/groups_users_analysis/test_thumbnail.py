import asyncio
import base64
import os
import re
import time
import uuid

import pytest
import sqlalchemy as sa

from baselayer.app.models import async_plain_session_factory
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

    # Don't wait for the thumbnail_queue background service — it fetches the
    # most-recent unprocessed obj and a busy test suite keeps pushing newer
    # objs to the front of the line. Call the same method synchronously.
    async def _backfill_thumbnails():
        async with async_plain_session_factory() as session:
            obj = await session.scalar(sa.select(Obj).where(Obj.id == obj_id))
            await obj.add_linked_thumbnails(["sdss", "ls", "ps1"], session)

    asyncio.run(_backfill_thumbnails())

    status, data = api(
        "GET", f"sources/{obj_id}?includeThumbnails=true", token=upload_data_token
    )
    thumbnails = data.get("data", {}).get("thumbnails", [])
    assert isinstance(thumbnails, list) and len(thumbnails) == 3

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

    # POST/thumbnail is synchronous; this short poll only guards read-after-write.
    nretries = 0
    thumbnails_loaded = False
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


def test_thumbnail_queue_fetch_obj_finds_unprocessed_source(
    upload_data_token, public_group
):
    """Direct test for services/thumbnail_queue/fetch_obj — the only
    queue-specific logic not exercised by the synchronous bypass above.
    """
    from services.thumbnail_queue.thumbnail_queue import fetch_obj

    obj_id = str(uuid.uuid4())
    status, _ = api(
        "POST",
        "sources",
        data={
            "id": obj_id,
            "ra": 234.22,
            "dec": -22.33,
            "group_ids": [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 200

    async def _fetch_backfill_fetch():
        async with async_plain_session_factory() as session:
            # The new obj has no (sdss, ls, ps1) thumbnails, so fetch_obj's
            # most-recent-missing query must surface it.
            obj, err = await fetch_obj(session)
            assert err is None
            assert obj is not None and obj.id == obj_id

            # After backfill the same query must no longer return it.
            await obj.add_linked_thumbnails(["sdss", "ls", "ps1"], session)
            obj, err = await fetch_obj(session)
            assert err is None
            assert obj is None or obj.id != obj_id

    asyncio.run(_fetch_backfill_fetch())


def test_thumbnail_queue_classifies_remote_grayscale(
    upload_data_token, public_group, monkeypatch
):
    """Remote thumbnails are inserted unclassified (is_grayscale NULL) so the
    request path never blocks on a cutout fetch; the queue's
    classify_pending_grayscale fills them in. The fetch is stubbed to stay
    offline and deterministic.
    """
    from services.thumbnail_queue import thumbnail_queue as tq

    obj_id = str(uuid.uuid4())
    status, _ = api(
        "POST",
        "sources",
        data={
            "id": obj_id,
            "ra": 234.22,
            "dec": -22.33,
            "group_ids": [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 200

    async def _values():
        async with async_plain_session_factory() as session:
            return (
                (
                    await session.execute(
                        sa.select(Thumbnail.is_grayscale).where(
                            Thumbnail.obj_id == obj_id
                        )
                    )
                )
                .scalars()
                .all()
            )

    async def _run():
        # Remote (public_url-only) thumbnails start unclassified.
        async with async_plain_session_factory() as session:
            obj = await session.get(Obj, obj_id)
            await obj.add_linked_thumbnails(["sdss", "ls", "ps1"], session)
        values = await _values()
        assert values and all(v is None for v in values)

        # Stub the network fetch, then drain the (globally-batched) queue until
        # this obj's thumbnails are classified.
        monkeypatch.setattr(tq, "_classify_remote_thumbnail", lambda url: True)
        for _ in range(50):
            await tq.classify_pending_grayscale(
                session_factory=async_plain_session_factory
            )
            values = await _values()
            if values and all(v is not None for v in values):
                break
        assert values and all(v is True for v in values)

    asyncio.run(_run())


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


def test_survey_thumbnail_skymapper_and_on_demand(
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
            "group_ids": [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 200

    # Default survey-thumbnail generation is SDSS/PS1/LS only; SkyMapper and the
    # pointed instruments (HST/Chandra/JWST) are on-demand.
    status, data = api(
        "POST",
        "internal/survey_thumbnail",
        data={"objID": obj_id},
        token=super_admin_token,
    )
    assert status == 200

    status, data = api(
        "GET", f"sources/{obj_id}?includeThumbnails=true", token=upload_data_token
    )
    types = {t["type"] for t in data["data"]["thumbnails"]}
    assert {"sdss", "ls", "ps1"} <= types
    assert not ({"sm", "hst", "chandra", "jwst"} & types)

    # Unknown thumbnail types are rejected.
    status, data = api(
        "POST",
        "internal/survey_thumbnail",
        data={"objID": obj_id, "types": ["bogus"]},
        token=super_admin_token,
    )
    assert status == 400
    assert "must be a subset" in data["message"]

    # SkyMapper is available on-demand (placeholder here since the cutout service
    # is disabled in test config, but the thumbnail is created).
    status, data = api(
        "POST",
        "internal/survey_thumbnail",
        data={"objID": obj_id, "types": ["sm"]},
        token=super_admin_token,
    )
    assert status == 200
    status, data = api(
        "GET", f"sources/{obj_id}?includeThumbnails=true", token=upload_data_token
    )
    assert "sm" in {t["type"] for t in data["data"]["thumbnails"]}
