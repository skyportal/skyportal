import asyncio
import uuid

import pytest
import sqlalchemy as sa

from baselayer.app import models as baselayer_models
from skyportal.models import (
    Candidate,
    DBSession,
    Instrument,
    Obj,
    Photometry,
    Source,
    SuperObj,
    User,
)
from skyportal.tests.fixtures import FilterFactory, InstrumentFactory, StreamFactory
from skyportal.utils.sso_ingest import (
    designation_to_obj_id,
    extract_designation,
    ingest_sso_alert,
    sso_filter_targets,
    sso_routing_for,
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


def test_sso_filter_targets_reads_altdata_and_autosave(
    public_group, public_stream, public_filter
):
    """`altdata['sso']` opts a filter in; `autosave` decides save vs. scan."""
    saving = FilterFactory(
        group=public_group, stream=public_stream, altdata={"sso": True}, autosave=True
    )
    scanning = FilterFactory(
        group=public_group, stream=public_stream, altdata={"sso": True}, autosave=False
    )
    DBSession().commit()
    try:
        targets = sso_filter_targets([saving, scanning, public_filter])
        # An unmarked filter is absent entirely, not present-with-None.
        assert public_filter.id not in targets
        assert targets[saving.id] == public_group.id
        assert targets[scanning.id] is None
    finally:
        FilterFactory.teardown(saving.id)
        FilterFactory.teardown(scanning.id)


def test_sso_routing_splits_saving_from_scanning():
    targets = {1: 10, 2: None, 3: 10}

    # A passing filter that opted in routes the alert; groups come only from
    # the autosaving ones.
    assert sso_routing_for([1, 2, 99], targets) == ([1, 2], [10])
    assert sso_routing_for([2], targets) == ([2], [])
    assert sso_routing_for([1, 3], targets) == ([1, 3], [10])

    # No opted-in filter passed -> sidereal path, even with a designation.
    assert sso_routing_for([99], targets) == ([], [])
    assert sso_routing_for(None, targets) == ([], [])


def test_scanning_filter_makes_a_candidate_not_a_source(
    ztf_instrument, designation, public_group, public_stream, super_admin_user
):
    """Without autosave the asteroid is scannable, not saved."""
    obj_id = designation_to_obj_id(designation)
    scanning = FilterFactory(
        group=public_group, stream=public_stream, altdata={"sso": True}, autosave=False
    )
    DBSession().commit()
    filter_id = scanning.id

    try:
        _, group_ids = sso_routing_for([filter_id], sso_filter_targets([scanning]))
        assert group_ids == []

        async def _run():
            async with baselayer_models.async_plain_session_factory() as session:
                user = await session.get(User, super_admin_user.id)
                return await ingest_sso_alert(
                    data=alert(designation, 2460000.5, 10.0, 20.0),
                    survey="ZTF",
                    session=session,
                    user=user,
                    designation=designation,
                    group_ids=group_ids,
                    filter_ids=[filter_id],
                    passing_alert_id=4242,
                )

        asyncio.run(_run())

        session = DBSession()
        session.expire_all()
        assert (
            session.scalars(sa.select(Source).where(Source.obj_id == obj_id)).all()
            == []
        )
        candidates = session.scalars(
            sa.select(Candidate).where(Candidate.obj_id == obj_id)
        ).all()
        assert [c.filter_id for c in candidates] == [filter_id]
    finally:
        session = DBSession()
        session.execute(sa.delete(Candidate).where(Candidate.obj_id == obj_id))
        session.commit()
        FilterFactory.teardown(filter_id)
