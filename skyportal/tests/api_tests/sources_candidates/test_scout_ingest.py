import uuid

import pytest
import sqlalchemy as sa

from skyportal.models import Annotation, DBSession, Obj, Source, SuperObj
from skyportal.utils.scout_ingest import (
    ScoutIngestError,
    ingest_scout_event,
)


def scout_event(tdes, event_type="new_candidate", **overrides):
    event = {
        "schema_version": "1.0",
        "event_type": event_type,
        "event_id": f"{tdes}:2026-08-13T00:00:00:{event_type}",
        "tdes": tdes,
        "iau_designation": None,
        "scout": {
            "last_run": "2026-08-13T00:00:00",
            "neo_score": 100,
            "geocentric_score": 0,
            "impact_rating": 3,
            "rms": 0.56,
            "num_obs": 25,
            "arc_days": 1.99,
            "vmag": 22.1,
            "ra_deg": 284.7087728,
            "dec_deg": -54.5907271,
            "rate": 10.69,
            "uncertainty_arcmin": 90.0,
            "uncertainty_p1_arcmin": 120.0,
            "h_mag": 23.7,
            "url": "https://cneos.jpl.nasa.gov/scout/#/object/",
        },
        "filters": {
            "version": "0.2",
            "passes": True,
            "results": {"neo_score": True, "rate": True},
        },
        "changes": {},
        "provenance": {
            "source": "NASA/JPL Scout API",
            "bridge_version": "0.1.0",
            "polled_at": "2026-08-13T00:00:00",
            "filter_mode": "strict",
        },
    }
    event.update(overrides)
    return event


@pytest.fixture
def scout_tdes():
    tdes = f"T{uuid.uuid4().hex[:7]}"
    yield tdes
    session = DBSession()
    session.execute(sa.delete(Source).where(Source.obj_id == tdes))
    session.execute(sa.delete(Annotation).where(Annotation.obj_id == tdes))
    for super_obj in session.scalars(
        sa.select(SuperObj).where(SuperObj.objs.any(Obj.id == tdes))
    ).unique():
        session.delete(super_obj)
    session.execute(sa.delete(Obj).where(Obj.id == tdes))
    session.commit()


def test_ingest_creates_source_annotation_and_super_obj(
    scout_tdes, public_group, super_admin_user
):
    session = DBSession()
    result = ingest_scout_event(
        session,
        scout_event(scout_tdes),
        [public_group.id],
        super_admin_user.id,
    )
    session.commit()

    assert result == {"obj_id": scout_tdes, "action": "created"}

    obj = session.scalar(sa.select(Obj).where(Obj.id == scout_tdes))
    assert obj.is_roid is True
    assert obj.ra == pytest.approx(284.7087728)
    # 90 arcmin of positional uncertainty, stored per axis in degrees
    assert obj.ra_err == pytest.approx(1.5)
    assert obj.healpix is not None

    source = session.scalar(sa.select(Source).where(Source.obj_id == scout_tdes))
    assert source.group_id == public_group.id
    assert source.active is True

    annotation = session.scalar(
        sa.select(Annotation).where(Annotation.obj_id == scout_tdes)
    )
    assert annotation.origin == "jpl-scout"
    assert annotation.data["neo_score"] == 100
    assert annotation.data["filter_rate"] is True
    assert annotation.data["filters_pass"] is True

    super_obj = session.scalar(
        sa.select(SuperObj).where(SuperObj.objs.any(Obj.id == scout_tdes))
    )
    assert super_obj.is_roid is True


def test_ingest_update_refreshes_position(scout_tdes, public_group, super_admin_user):
    session = DBSession()
    ingest_scout_event(
        session, scout_event(scout_tdes), [public_group.id], super_admin_user.id
    )
    session.commit()

    event = scout_event(scout_tdes, event_type="updated")
    event["scout"]["ra_deg"] = 285.0
    event["scout"]["uncertainty_arcmin"] = 30.0
    result = ingest_scout_event(session, event, [public_group.id], super_admin_user.id)
    session.commit()

    assert result["action"] == "updated"
    obj = session.scalar(sa.select(Obj).where(Obj.id == scout_tdes))
    assert obj.ra == pytest.approx(285.0)
    assert obj.ra_err == pytest.approx(0.5)


def test_ingest_cancellation_deactivates_source(
    scout_tdes, public_group, super_admin_user
):
    session = DBSession()
    ingest_scout_event(
        session, scout_event(scout_tdes), [public_group.id], super_admin_user.id
    )
    session.commit()

    result = ingest_scout_event(
        session,
        scout_event(scout_tdes, event_type="cancelled"),
        [public_group.id],
        super_admin_user.id,
    )
    session.commit()

    assert result["action"] == "deactivated"
    source = session.scalar(sa.select(Source).where(Source.obj_id == scout_tdes))
    assert source.active is False


def test_ingest_links_iau_designation(scout_tdes, public_group, super_admin_user):
    """A designated object keeps its NEOCP identity linked under one SuperObj."""
    session = DBSession()
    ingest_scout_event(
        session, scout_event(scout_tdes), [public_group.id], super_admin_user.id
    )
    session.commit()

    iau = f"2026 XX{uuid.uuid4().hex[:4]}"
    ingest_scout_event(
        session,
        scout_event(scout_tdes, event_type="updated", iau_designation=iau),
        [public_group.id],
        super_admin_user.id,
    )
    session.commit()

    obj = session.scalar(sa.select(Obj).where(Obj.id == scout_tdes))
    # Prefixed like the survey path, so one alias query spans both.
    assert obj.alias == [f"SSO {iau}"]

    super_obj = session.scalar(
        sa.select(SuperObj).where(SuperObj.objs.any(Obj.id == scout_tdes))
    )
    assert super_obj.name == f"SSO {iau}"


def test_ingest_skips_relaxed_test_events(scout_tdes, public_group, super_admin_user):
    session = DBSession()
    event = scout_event(scout_tdes)
    event["provenance"]["filter_mode"] = "relaxed_test"

    result = ingest_scout_event(session, event, [public_group.id], super_admin_user.id)
    session.commit()

    assert result["action"] == "skipped_relaxed_test"
    assert session.scalar(sa.select(Obj).where(Obj.id == scout_tdes)) is None


def test_ingest_rejects_bad_schema(scout_tdes, public_group, super_admin_user):
    session = DBSession()
    with pytest.raises(ScoutIngestError):
        ingest_scout_event(
            session,
            scout_event(scout_tdes, schema_version="9.9"),
            [public_group.id],
            super_admin_user.id,
        )
