"""BOOM emits cross-survey matches (``survey_matches``) on a passing alert — e.g. a
ZTF result carrying the alert's LSST counterpart. Ingestion must create the
counterpart Obj and link it to the primary via a SuperObj (the "same physical
object" grouping). These tests cover ``_ingest_survey_matches``."""

import asyncio
import uuid

import pytest
import sqlalchemy as sa

from baselayer.app import models as baselayer_models
from skyportal.broker_apis.boom import _ingest_survey_matches
from skyportal.models import (
    DBSession,
    Instrument,
    Obj,
    ObjToSuperObj,
    SuperObj,
    User,
)
from skyportal.tests.fixtures import InstrumentFactory


@pytest.fixture()
def survey_instruments():
    """The match ingest looks up the survey instrument by name; ensure both the
    primary (ZTF) and counterpart (LSST) instruments exist."""
    created = []
    for name in ("ZTF", "LSST"):
        if (
            DBSession().scalar(sa.select(Instrument).where(Instrument.name == name))
            is None
        ):
            created.append(InstrumentFactory(name=name))
    DBSession().commit()
    yield
    for instrument in created:
        InstrumentFactory.teardown(instrument)


def _make_obj(obj_id, ra=10.0, dec=20.0):
    DBSession().add(Obj(id=obj_id, ra=ra, dec=dec, ra_dis=ra, dec_dis=dec))
    DBSession().commit()


def _cleanup(obj_ids):
    """Delete the test objs; ObjToSuperObj rows cascade, then drop orphan SuperObjs."""
    session = DBSession()
    super_ids = set(
        session.scalars(
            sa.select(ObjToSuperObj.super_obj_id).where(
                ObjToSuperObj.obj_id.in_(obj_ids)
            )
        ).all()
    )
    session.execute(sa.delete(Obj).where(Obj.id.in_(obj_ids)))
    if super_ids:
        session.execute(sa.delete(SuperObj).where(SuperObj.id.in_(super_ids)))
    session.commit()


def _record(lsst_id, ra=10.0, dec=20.0):
    return {
        "survey_matches": {
            "ztf": None,
            "lsst": {
                "objectId": lsst_id,
                "ra": ra,
                "dec": dec,
                "photometry": [
                    {
                        "jd": 2461232.5,
                        "band": "lssti",
                        "flux": 7400.0,
                        "flux_err": 322.0,
                        "ra": ra,
                        "dec": dec,
                        "programid": 1,
                    }
                ],
            },
        }
    }


def _ingest_matches(record, main_obj_id, main_survey, user_id):
    async def _run():
        async with baselayer_models.async_plain_session_factory() as session:
            user = await session.get(User, user_id)
            await _ingest_survey_matches(
                record, main_obj_id, main_survey, session, user
            )

    asyncio.run(_run())


def test_survey_match_creates_counterpart_obj_and_super_obj(
    super_admin_user, survey_instruments
):
    """A ZTF alert's LSST ``survey_matches`` entry creates the LSST Obj and a
    SuperObj linking the two — the cross-survey association surfaced on the source."""
    main_id = f"ZTF{uuid.uuid4().hex[:10]}"
    lsst_id = str(uuid.uuid4().int)[:18]
    _make_obj(main_id)
    try:
        _ingest_matches(_record(lsst_id), main_id, "ZTF", super_admin_user.id)
        DBSession().expire_all()

        lsst_obj = DBSession().scalar(sa.select(Obj).where(Obj.id == lsst_id))
        assert lsst_obj is not None, "LSST counterpart obj was not created"
        assert lsst_obj.origin == "LSST"

        super_obj = DBSession().scalar(
            sa.select(SuperObj)
            .join(ObjToSuperObj)
            .where(ObjToSuperObj.obj_id == main_id)
        )
        assert super_obj is not None, "SuperObj linking primary + match not created"
        linked = set(
            DBSession()
            .scalars(
                sa.select(ObjToSuperObj.obj_id).where(
                    ObjToSuperObj.super_obj_id == super_obj.id
                )
            )
            .all()
        )
        assert linked == {main_id, lsst_id}
    finally:
        _cleanup([main_id, lsst_id])


def test_survey_match_ingest_is_idempotent(super_admin_user, survey_instruments):
    """Re-ingesting the same match must not create a second SuperObj or duplicate
    the link (associate_super_obj adds only not-yet-linked matches)."""
    main_id = f"ZTF{uuid.uuid4().hex[:10]}"
    lsst_id = str(uuid.uuid4().int)[:18]
    _make_obj(main_id)
    try:
        _ingest_matches(_record(lsst_id), main_id, "ZTF", super_admin_user.id)
        _ingest_matches(_record(lsst_id), main_id, "ZTF", super_admin_user.id)
        DBSession().expire_all()

        super_ids = set(
            DBSession()
            .scalars(
                sa.select(ObjToSuperObj.super_obj_id).where(
                    ObjToSuperObj.obj_id == main_id
                )
            )
            .all()
        )
        assert len(super_ids) == 1, "re-ingest created a duplicate SuperObj"
        links = (
            DBSession()
            .scalars(
                sa.select(ObjToSuperObj.obj_id).where(
                    ObjToSuperObj.super_obj_id == super_ids.pop()
                )
            )
            .all()
        )
        assert sorted(links) == sorted({main_id, lsst_id}), "links not deduped"
    finally:
        _cleanup([main_id, lsst_id])
