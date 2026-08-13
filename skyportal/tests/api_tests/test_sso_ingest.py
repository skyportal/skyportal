import asyncio
import uuid

import pytest
import sqlalchemy as sa

from baselayer.app import models as baselayer_models
from skyportal.models import (
    DBSession,
    Instrument,
    Obj,
    Photometry,
    Source,
    SuperObj,
    User,
)
from skyportal.tests.fixtures import InstrumentFactory, StreamFactory
from skyportal.utils.sso_ingest import (
    designation_to_obj_id,
    extract_designation,
    ingest_sso_alert,
)


@pytest.fixture()
def ztf_instrument():
    created = None
    if (
        DBSession().scalar(sa.select(Instrument).where(Instrument.name == "ZTF"))
        is None
    ):
        created = InstrumentFactory(name="ZTF")
        DBSession().commit()
    yield
    if created is not None:
        InstrumentFactory.teardown(created)


@pytest.fixture()
def ztf_stream():
    """Photometry is gated on a stream mapping (survey, programid); provide one."""
    stream = StreamFactory(altdata={"collection": "ZTF_alerts", "selector": [1]})
    DBSession().commit()
    stream_id = stream.id
    yield stream
    StreamFactory.teardown(stream_id)


@pytest.fixture()
def designation():
    designation = f"{uuid.uuid4().hex[:8]}"
    yield designation
    session = DBSession()
    obj_id = designation_to_obj_id(designation)
    session.execute(sa.delete(Source).where(Source.obj_id == obj_id))
    session.execute(sa.delete(Photometry).where(Photometry.obj_id == obj_id))
    for super_obj in session.scalars(
        sa.select(SuperObj).where(SuperObj.name == designation)
    ).unique():
        session.delete(super_obj)
    session.execute(sa.delete(Obj).where(Obj.id == obj_id))
    session.commit()


def alert(designation, jd, ra, dec, mag=19.5):
    """A ZTF-shaped alert whose position-keyed history is deliberately wrong."""
    return {
        "objectId": f"ZTF{uuid.uuid4().hex[:10]}",
        "candidate": {
            "jd": jd,
            "ra": ra,
            "dec": dec,
            "band": "r",
            "magpsf": mag,
            "sigmapsf": 0.05,
            "programid": 1,
        },
        # Whatever else has passed through these coordinates; must not be ingested.
        "prv_candidates": [
            {"jd": jd - 100, "band": "r", "magpsf": 20.5, "sigmapsf": 0.1}
        ],
        "fp_hists": [{"jd": jd - 50, "band": "g", "magpsf": 21.0, "sigmapsf": 0.2}],
        "properties": {
            "sso": {
                "is_sso": True,
                "designation": designation,
                "separation_arcsec": 0.8,
            }
        },
    }


def run_ingest(data, designation, user_id, group_ids):
    async def _run():
        async with baselayer_models.async_plain_session_factory() as session:
            user = await session.get(User, user_id)
            return await ingest_sso_alert(
                data, "ZTF", session, user, designation, group_ids
            )

    return asyncio.run(_run())


@pytest.mark.parametrize(
    "data,annotations,expected",
    [
        ({"properties": {"sso": {"designation": "9816"}}}, None, "9816"),
        ({}, {3: {"sso": {"designation": "2026 XX1"}}}, "2026 XX1"),
        ({}, {3: {"ssnamenr": "220"}}, "220"),
        ({"candidate": {"ssnamenr": "null"}}, {3: {"ssnamenr": -999}}, None),
        ({}, None, None),
    ],
)
def test_extract_designation(data, annotations, expected):
    assert extract_designation(data, annotations) == expected


def test_obj_id_is_url_safe_and_namespaced():
    # Bare numeric designations would otherwise collide with unrelated obj IDs.
    assert designation_to_obj_id("220") == "sso_220"
    assert designation_to_obj_id("2026 XX1") == "sso_2026_XX1"


def test_detections_group_under_one_obj(
    ztf_instrument, designation, public_group, super_admin_user
):
    """Separate alerts for one asteroid must build one object, not one each."""
    obj_id = designation_to_obj_id(designation)

    first = run_ingest(
        alert(designation, 2460000.5, 10.0, 20.0),
        designation,
        super_admin_user.id,
        [public_group.id],
    )
    second = run_ingest(
        alert(designation, 2460001.5, 10.5, 20.4),
        designation,
        super_admin_user.id,
        [public_group.id],
    )

    assert first["id"] == second["id"] == obj_id

    session = DBSession()
    session.expire_all()
    obj = session.scalar(sa.select(Obj).where(Obj.id == obj_id))
    assert obj.is_roid is True
    assert obj.mpc_name == designation
    # Position tracks the most recent detection, with its epoch recorded.
    assert obj.ra == pytest.approx(10.5)
    assert obj.altdata["last_detection_jd"] == 2460001.5
    assert obj.altdata["last_separation_arcsec"] == pytest.approx(0.8)

    sources = session.scalars(sa.select(Source).where(Source.obj_id == obj_id)).all()
    assert len(sources) == 1


def test_only_the_triggering_detection_is_ingested(
    ztf_instrument, ztf_stream, designation, public_group, super_admin_user
):
    """Position-keyed history belongs to the field, not the asteroid."""
    obj_id = designation_to_obj_id(designation)

    run_ingest(
        alert(designation, 2460000.5, 10.0, 20.0),
        designation,
        super_admin_user.id,
        [public_group.id],
    )

    session = DBSession()
    session.expire_all()
    photometry = session.scalars(
        sa.select(Photometry).where(Photometry.obj_id == obj_id)
    ).all()

    assert len(photometry) == 1
    assert photometry[0].mjd == pytest.approx(2460000.5 - 2400000.5)
    # Each point carries the position it was measured at.
    assert photometry[0].ra == pytest.approx(10.0)


def test_detections_link_under_a_designation_super_obj(
    ztf_instrument, designation, public_group, super_admin_user
):
    obj_id = designation_to_obj_id(designation)
    run_ingest(
        alert(designation, 2460000.5, 10.0, 20.0),
        designation,
        super_admin_user.id,
        [public_group.id],
    )

    session = DBSession()
    session.expire_all()
    super_obj = session.scalar(sa.select(SuperObj).where(SuperObj.name == designation))
    assert super_obj is not None
    assert super_obj.is_roid is True
    assert obj_id in {obj.id for obj in super_obj.objs}
