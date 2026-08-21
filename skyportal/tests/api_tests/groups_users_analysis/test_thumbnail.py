import asyncio
import base64
import os
import re
import time
import uuid

import pytest
import sqlalchemy as sa
from skyportal_py import SkyPortalError
from skyportal_py.sources import SourcePost
from skyportal_py.thumbnails import ThumbnailPost

from baselayer.app.models import async_plain_session_factory
from skyportal.models import DBSession, Obj, Thumbnail
from skyportal.tests import api, client


def test_token_user_post_get_thumbnail(upload_data_token, public_group, ztf_camera):
    sp = client(upload_data_token)
    obj_id = str(uuid.uuid4())
    saved = sp.post_source(
        SourcePost(
            id=obj_id,
            ra=234.22,
            dec=-22.33,
            redshift=3,
            transient=False,
            ra_dis=2.3,
            group_ids=[public_group.id],
        )
    )
    assert saved.id == obj_id

    # Don't wait for the thumbnail_queue background service — it fetches the
    # most-recent unprocessed obj and a busy test suite keeps pushing newer
    # objs to the front of the line. Call the same method synchronously.
    async def _backfill_thumbnails():
        async with async_plain_session_factory() as session:
            obj = await session.scalar(sa.select(Obj).where(Obj.id == obj_id))
            await obj.add_linked_thumbnails(["sdss", "ls", "ps1"], session)

    asyncio.run(_backfill_thumbnails())

    thumbnails = sp.fetch_source(obj_id, include_thumbnails=True).thumbnails
    assert isinstance(thumbnails, list) and len(thumbnails) == 3

    orig_source_thumbnail_count = len(thumbnails)
    data = base64.b64encode(
        open(os.path.abspath("skyportal/tests/data/14gqr_new.png"), "rb").read()
    ).decode()
    ttype = "new"
    thumbnail_id = sp.post_thumbnail(
        ThumbnailPost(obj_id=obj_id, data=data, ttype=ttype)
    ).id
    assert isinstance(thumbnail_id, int)

    assert sp.fetch_thumbnail(thumbnail_id).type == "new"

    # POST/thumbnail is synchronous; this short poll only guards read-after-write.
    nretries = 0
    thumbnails_loaded = False
    while nretries < 5:
        thumbnails = sp.fetch_source(obj_id, include_thumbnails=True).thumbnails
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
    client(upload_data_token).post_source(
        SourcePost(id=obj_id, ra=234.22, dec=-22.33, group_ids=[public_group.id])
    )

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
    client(upload_data_token).post_source(
        SourcePost(id=obj_id, ra=234.22, dec=-22.33, group_ids=[public_group.id])
    )

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
        # Remote (public_url) thumbnails are inserted unclassified so the
        # request path never blocks on a cutout fetch. Verify that on an
        # *uncommitted* row: a live thumbnail_queue service only sees committed
        # rows, so it can't have classified it first (which races a check of
        # the committed table).
        async with async_plain_session_factory() as session:
            probe = Thumbnail(
                obj_id=obj_id,
                public_url="https://example.invalid/thumb.png",
                type="ps1",
            )
            session.add(probe)
            await session.flush()
            assert probe.is_grayscale is None
            await session.rollback()

        async with async_plain_session_factory() as session:
            obj = await session.get(Obj, obj_id)
            await obj.add_linked_thumbnails(["sdss", "ls", "ps1"], session)

        # Drain the (globally-batched) queue until this obj's thumbnails are
        # classified. The stub keeps the test's own drain offline; a live
        # thumbnail_queue service may also classify some (to False on a failed
        # fetch), and whichever classifier reaches a NULL row first wins — so
        # assert only that the queue fills every thumbnail in (non-NULL).
        monkeypatch.setattr(tq, "_classify_remote_thumbnail", lambda url: True)
        values = []
        for _ in range(50):
            await tq.classify_pending_grayscale(
                session_factory=async_plain_session_factory
            )
            values = await _values()
            if values and all(v is not None for v in values):
                break
        assert values and all(v is not None for v in values)

    asyncio.run(_run())


def test_cannot_post_thumbnail_invalid_ttype(
    upload_data_token, public_group, ztf_camera
):
    obj_id = str(uuid.uuid4())
    saved = client(upload_data_token).post_source(
        SourcePost(
            id=obj_id,
            ra=234.22,
            dec=-22.33,
            redshift=3,
            transient=False,
            ra_dis=2.3,
            group_ids=[public_group.id],
        )
    )
    assert saved.id == obj_id

    data = base64.b64encode(
        open(os.path.abspath("skyportal/tests/data/14gqr_new.png"), "rb").read()
    )
    ttype = "invalid_ttype"
    # raw api: intentionally malformed payload the typed client can't produce
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
    sp = client(upload_data_token)
    obj_id = str(uuid.uuid4())
    saved = sp.post_source(
        SourcePost(
            id=obj_id,
            ra=234.22,
            dec=-22.33,
            redshift=3,
            transient=False,
            ra_dis=2.3,
            group_ids=[public_group.id],
        )
    )
    assert saved.id == obj_id

    data = base64.b64encode(
        open(
            os.path.abspath("skyportal/tests/data/candid-87704463155000_ref.jpg"), "rb"
        ).read()
    ).decode()
    ttype = "ref"
    with pytest.raises(
        SkyPortalError,
        match=re.escape("Invalid thumbnail image type. Only PNG are supported."),
    ) as err:
        sp.post_thumbnail(ThumbnailPost(obj_id=obj_id, data=data, ttype=ttype))
    assert err.value.status_code == 400


def test_cannot_post_thumbnail_invalid_size(
    upload_data_token, public_group, ztf_camera
):
    sp = client(upload_data_token)
    obj_id = str(uuid.uuid4())
    saved = sp.post_source(
        SourcePost(
            id=obj_id,
            ra=234.22,
            dec=-22.33,
            redshift=3,
            transient=False,
            ra_dis=2.3,
            group_ids=[public_group.id],
        )
    )
    assert saved.id == obj_id

    data = base64.b64encode(
        open(os.path.abspath("skyportal/tests/data/14gqr_new_13px.png"), "rb").read()
    ).decode()
    ttype = "ref"
    with pytest.raises(
        SkyPortalError, match=re.escape("Invalid thumbnail size.")
    ) as err:
        sp.post_thumbnail(ThumbnailPost(obj_id=obj_id, data=data, ttype=ttype))
    assert err.value.status_code == 400


def test_cannot_post_thumbnail_invalid_file_type(
    upload_data_token, public_group, ztf_camera
):
    sp = client(upload_data_token)
    obj_id = str(uuid.uuid4())
    saved = sp.post_source(
        SourcePost(
            id=obj_id,
            ra=234.22,
            dec=-22.33,
            redshift=3,
            transient=False,
            ra_dis=2.3,
            group_ids=[public_group.id],
        )
    )
    assert saved.id == obj_id

    data = base64.b64encode(os.urandom(2048)).decode()  # invalid image data
    ttype = "ref"
    with pytest.raises(SkyPortalError, match="cannot identify image file") as err:
        sp.post_thumbnail(ThumbnailPost(obj_id=obj_id, data=data, ttype=ttype))
    assert err.value.status_code == 400


def test_delete_thumbnail_deletes_file_on_disk(
    upload_data_token, super_admin_token, public_group
):
    sp = client(upload_data_token)
    obj_id = str(uuid.uuid4())
    saved = sp.post_source(
        SourcePost(
            id=obj_id,
            ra=234.22,
            dec=-22.33,
            redshift=3,
            transient=False,
            ra_dis=2.3,
            group_ids=[public_group.id],
        )
    )
    assert saved.id == obj_id

    thumbnail_data = base64.b64encode(
        open(os.path.abspath("skyportal/tests/data/14gqr_new.png"), "rb").read()
    ).decode()
    ttype = "new"
    thumbnail_id = sp.post_thumbnail(
        ThumbnailPost(obj_id=obj_id, data=thumbnail_data, ttype=ttype)
    ).id
    assert isinstance(thumbnail_id, int)

    assert sp.fetch_thumbnail(thumbnail_id).type == ttype

    nretries = 0
    thumbnail = None
    # look for the newly created thumbnail
    while nretries < 5:
        thumbnails = sp.fetch_source(obj_id, include_thumbnails=True).thumbnails
        if isinstance(thumbnails, list) and any(
            t.id == thumbnail_id for t in thumbnails
        ):
            thumbnail = next((t for t in thumbnails if t.id == thumbnail_id), None)
            break
        nretries += 1
        time.sleep(2)

    assert thumbnail is not None

    fpath = thumbnail.file_uri
    assert os.path.exists(fpath)

    client(super_admin_token).delete_thumbnail(thumbnail_id)

    assert not os.path.exists(fpath)


def test_change_thumbnail_folder(upload_data_token, super_admin_token, public_group):
    sp = client(upload_data_token)
    admin = client(super_admin_token)
    obj_id = str(uuid.uuid4())
    saved = sp.post_source(
        SourcePost(
            id=obj_id,
            ra=234.22,
            dec=-22.33,
            redshift=3,
            transient=False,
            ra_dis=2.3,
            group_ids=[public_group.id],
        )
    )
    assert saved.id == obj_id

    thumbnail_data = base64.b64encode(
        open(os.path.abspath("skyportal/tests/data/14gqr_new.png"), "rb").read()
    ).decode()
    ttype = "new"
    thumbnail_id = sp.post_thumbnail(
        ThumbnailPost(obj_id=obj_id, data=thumbnail_data, ttype=ttype)
    ).id
    assert isinstance(thumbnail_id, int)

    assert sp.fetch_thumbnail(thumbnail_id).type == ttype

    thumbnail = sp.fetch_thumbnail(thumbnail_id)
    assert thumbnail.obj_id == obj_id
    fpath = thumbnail.file_uri
    assert os.path.exists(fpath)

    # check there are exactly two subfolders of two letters
    # and those letters should be hexadecimal digits (0-9, a-f)
    subfolders2 = os.path.dirname(fpath.split("thumbnails/")[1])
    assert bool(re.match(r"^[a-f0-9]{2}/[a-f-0-9]{2}$", subfolders2))

    # now push the thumbnails to 3 levels deep
    # (this always sent a `type` param the server ignores — it reads `types` —
    # so the server-default types are checked, which include "new")
    report = admin.update_thumbnail_paths(required_depth=3, num_per_page=500)

    assert report.total_matches < 500  # otherwise some are not moved!
    assert report.in_wrong_folder == 0  # all thumbnails are updated

    # check the new folder structure
    thumbnail = sp.fetch_thumbnail(thumbnail_id)
    assert thumbnail.obj_id == obj_id
    fpath = thumbnail.file_uri
    assert os.path.exists(fpath)
    subfolders3 = os.path.dirname(fpath.split("thumbnails/")[1])
    assert bool(re.match(r"^[a-f0-9]{2}/[a-f-0-9]{2}/[a-f-0-9]{2}$", subfolders3))

    # return the thumbnails to 2 levels deep
    report = admin.update_thumbnail_paths(required_depth=2, num_per_page=500)

    assert report.total_matches < 500  # otherwise some are not moved!
    assert report.in_wrong_folder == 0  # all thumbnails are updated

    # make sure the new folder structure is back to normal
    thumbnail = sp.fetch_thumbnail(thumbnail_id)
    assert thumbnail.obj_id == obj_id
    fpath = thumbnail.file_uri
    assert os.path.exists(fpath)

    subfolders4 = os.path.dirname(fpath.split("thumbnails/")[1])
    assert bool(re.match(r"^[a-f0-9]{2}/[a-f-0-9]{2}$", subfolders4))
    assert subfolders2 == subfolders4

    # find the old 3 level deep folder and make sure it is empty
    old_folder = os.path.join(fpath.split("thumbnails")[0], "thumbnails", subfolders3)
    assert os.path.exists(old_folder)
    assert len(os.listdir(old_folder)) == 0

    # delete empty folders
    admin.delete_thumbnail_folders()

    assert not os.path.exists(old_folder)


@pytest.mark.flaky(reruns=3)
def test_token_user_delete_thumbnail_cascade_source(
    upload_data_token, super_admin_token, public_group, ztf_camera
):
    sp = client(upload_data_token)
    obj_id = str(uuid.uuid4())
    saved = sp.post_source(
        SourcePost(
            id=obj_id,
            ra=234.22,
            dec=-22.33,
            redshift=3,
            transient=False,
            ra_dis=2.3,
            group_ids=[public_group.id],
        )
    )
    assert saved.id == obj_id

    orig_source_thumbnail_count = len(
        DBSession.query(Obj).filter(Obj.id == obj_id).first().thumbnails
    )
    data = base64.b64encode(
        open(os.path.abspath("skyportal/tests/data/14gqr_new.png"), "rb").read()
    ).decode()
    ttype = "new"
    thumbnail_id = sp.post_thumbnail(
        ThumbnailPost(obj_id=obj_id, data=data, ttype=ttype)
    ).id
    assert isinstance(thumbnail_id, int)

    assert sp.fetch_thumbnail(thumbnail_id).type == "new"

    assert (
        DBSession.query(Thumbnail).filter(Thumbnail.id == thumbnail_id).first().obj.id
    ) == obj_id
    assert (
        len(DBSession.query(Obj).filter(Obj.id == obj_id).first().thumbnails)
        == orig_source_thumbnail_count + 1
    )

    client(super_admin_token).delete_thumbnail(thumbnail_id)

    assert (
        len(DBSession.query(Obj).filter(Obj.id == obj_id).first().thumbnails)
        == orig_source_thumbnail_count
    )


def test_survey_thumbnail_skymapper_and_on_demand(
    upload_data_token, super_admin_token, public_group
):
    sp = client(upload_data_token)
    obj_id = str(uuid.uuid4())
    sp.post_source(
        SourcePost(id=obj_id, ra=234.22, dec=-22.33, group_ids=[public_group.id])
    )

    # Default survey-thumbnail generation is SDSS/PS1/LS only; SkyMapper and the
    # pointed instruments (HST/Chandra/JWST) are on-demand.
    # raw api: internal endpoint outside skyportal-py's scope
    status, data = api(
        "POST",
        "internal/survey_thumbnail",
        data={"objID": obj_id},
        token=super_admin_token,
    )
    assert status == 200

    types = {
        t.type for t in sp.fetch_source(obj_id, include_thumbnails=True).thumbnails
    }
    assert {"sdss", "ls", "ps1"} <= types
    assert not ({"sm", "hst", "chandra", "jwst"} & types)

    # Unknown thumbnail types are rejected.
    # raw api: internal endpoint outside skyportal-py's scope
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
    # raw api: internal endpoint outside skyportal-py's scope
    status, data = api(
        "POST",
        "internal/survey_thumbnail",
        data={"objID": obj_id, "types": ["sm"]},
        token=super_admin_token,
    )
    assert status == 200
    assert "sm" in {
        t.type for t in sp.fetch_source(obj_id, include_thumbnails=True).thumbnails
    }
