"""A broker cutout thumbnail records the survey it came from (e.g. ZTF, LSST) so
the source page can label per-survey tiles — obj.origin is too noisy to rely on."""

import asyncio
import base64
import io
import os

import pytest
import sqlalchemy as sa
from PIL import Image

from baselayer.app import models as baselayer_models
from skyportal.handlers.api.thumbnail import post_thumbnail
from skyportal.models import DBSession, Thumbnail


def _png_b64():
    buf = io.BytesIO()
    Image.new("RGB", (16, 16), (10, 20, 30)).save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("utf-8")


def _post(user, obj_id, ttype="new", survey=None):
    async def _run():
        async with baselayer_models.async_plain_session_factory() as session:
            return await post_thumbnail(
                {
                    "obj_id": obj_id,
                    "data": _png_b64(),
                    "ttype": ttype,
                    "survey": survey,
                },
                user.id,
                session,
            )

    return asyncio.run(_run())


def _thumbnails(obj_id):
    """Only the rows _post writes: survey tiles land asynchronously and race the counts."""
    DBSession().expire_all()
    return (
        DBSession()
        .scalars(
            sa.select(Thumbnail)
            .where(Thumbnail.obj_id == obj_id, Thumbnail.type == "new")
            .order_by(Thumbnail.id)
        )
        .all()
    )


@pytest.fixture()
def bare_source(public_source):
    """ObjFactory seeds ten blank 'new' rows per obj, which would drown the counts."""

    def clear():
        for thumbnail in _thumbnails(public_source.id):
            DBSession().delete(thumbnail)
        DBSession().commit()

    clear()
    yield public_source
    clear()


def test_post_thumbnail_persists_survey(super_admin_user, bare_source):
    thumbnail_id = _post(super_admin_user, bare_source.id, survey="LSST")

    DBSession().expire_all()
    thumbnail = DBSession().scalar(
        sa.select(Thumbnail).where(Thumbnail.id == thumbnail_id)
    )
    assert thumbnail is not None
    assert thumbnail.survey == "LSST", "thumbnail did not persist its survey"


def test_repost_same_survey_updates_single_row(super_admin_user, bare_source):
    first = _post(super_admin_user, bare_source.id, survey="ZTF")
    second = _post(super_admin_user, bare_source.id, survey="ZTF")

    assert first == second, "reposting the same survey created a second row"
    assert len(_thumbnails(bare_source.id)) == 1


def test_survey_case_and_whitespace_are_normalized(super_admin_user, bare_source):
    first = _post(super_admin_user, bare_source.id, survey="Ztf")
    second = _post(super_admin_user, bare_source.id, survey="  ztf ")

    assert first == second, '"Ztf" and "ztf" were stored as distinct surveys'
    thumbnails = _thumbnails(bare_source.id)
    assert len(thumbnails) == 1
    assert thumbnails[0].survey == "ZTF"


def test_legacy_null_survey_row_is_adopted(super_admin_user, bare_source):
    legacy = _post(super_admin_user, bare_source.id, survey=None)
    adopted = _post(super_admin_user, bare_source.id, survey="ZTF")

    assert legacy == adopted, "the pre-survey row was left as a duplicate tile"
    thumbnails = _thumbnails(bare_source.id)
    assert len(thumbnails) == 1
    assert thumbnails[0].survey == "ZTF"


def test_surveys_do_not_share_a_file_on_disk(super_admin_user, bare_source):
    _post(super_admin_user, bare_source.id, survey="ZTF")
    _post(super_admin_user, bare_source.id, survey="LSST")

    thumbnails = _thumbnails(bare_source.id)
    assert len(thumbnails) == 2
    uris = {t.file_uri for t in thumbnails}
    assert len(uris) == 2, "two surveys wrote to the same file"
    assert all(os.path.isfile(uri) for uri in uris)


@pytest.mark.parametrize("survey", ["../../evil", "ZTF/../..", "a/b"])
def test_survey_cannot_escape_the_thumbnail_folder(
    super_admin_user, bare_source, survey
):
    with pytest.raises(ValueError, match="Invalid survey"):
        _post(super_admin_user, bare_source.id, survey=survey)

    assert _thumbnails(bare_source.id) == []
