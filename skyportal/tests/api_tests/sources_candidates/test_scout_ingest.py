import uuid

import pytest
import sqlalchemy as sa

from skyportal.models import (
    Annotation,
    DBSession,
    Obj,
    ObjTag,
    ObjTagOption,
    Source,
    SuperObj,
)
from skyportal.utils.scout_ingest import (
    IMPACTOR_TAG,
    OBJ_ID_PREFIX,
    ScoutIngestError,
    ingest_scout_event,
)
from skyportal.utils.sso_ingest import designation_to_obj_id, sso_label


def scout_obj_id(tdes):
    return designation_to_obj_id(tdes, prefix=OBJ_ID_PREFIX)


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
    session.execute(sa.delete(Source).where(Source.obj_id == scout_obj_id(tdes)))
    session.execute(
        sa.delete(Annotation).where(Annotation.obj_id == scout_obj_id(tdes))
    )
    for super_obj in session.scalars(
        sa.select(SuperObj).where(SuperObj.objs.any(Obj.id == scout_obj_id(tdes)))
    ).unique():
        session.delete(super_obj)
    session.execute(sa.delete(Obj).where(Obj.id == scout_obj_id(tdes)))
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

    assert result == {"obj_id": scout_obj_id(scout_tdes), "action": "created"}

    obj = session.scalar(sa.select(Obj).where(Obj.id == scout_obj_id(scout_tdes)))
    assert obj.is_roid is True
    assert obj.ra == pytest.approx(284.7087728)
    # 90 arcmin of positional uncertainty, stored per axis in degrees
    assert obj.ra_err == pytest.approx(1.5)
    assert obj.healpix is not None

    source = session.scalar(
        sa.select(Source).where(Source.obj_id == scout_obj_id(scout_tdes))
    )
    assert source.group_id == public_group.id
    assert source.active is True

    annotation = session.scalar(
        sa.select(Annotation).where(Annotation.obj_id == scout_obj_id(scout_tdes))
    )
    assert annotation.origin == "jpl-scout"
    assert annotation.data["neo_score"] == 100
    assert annotation.data["filter_rate"] is True
    assert annotation.data["filters_pass"] is True

    super_obj = session.scalar(
        sa.select(SuperObj).where(SuperObj.objs.any(Obj.id == scout_obj_id(scout_tdes)))
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
    obj = session.scalar(sa.select(Obj).where(Obj.id == scout_obj_id(scout_tdes)))
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
    source = session.scalar(
        sa.select(Source).where(Source.obj_id == scout_obj_id(scout_tdes))
    )
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

    obj = session.scalar(sa.select(Obj).where(Obj.id == scout_obj_id(scout_tdes)))
    # Prefixed like the survey path, so one alias query spans both.
    assert obj.alias == [f"SSO {iau}"]

    super_obj = session.scalar(
        sa.select(SuperObj).where(SuperObj.objs.any(Obj.id == scout_obj_id(scout_tdes)))
    )
    assert super_obj.name == f"SSO {iau}"


def test_ingest_skips_relaxed_test_events(scout_tdes, public_group, super_admin_user):
    session = DBSession()
    event = scout_event(scout_tdes)
    event["provenance"]["filter_mode"] = "relaxed_test"

    result = ingest_scout_event(session, event, [public_group.id], super_admin_user.id)
    session.commit()

    assert result["action"] == "skipped_relaxed_test"
    assert (
        session.scalar(sa.select(Obj).where(Obj.id == scout_obj_id(scout_tdes))) is None
    )


def test_ingest_rejects_bad_schema(scout_tdes, public_group, super_admin_user):
    session = DBSession()
    with pytest.raises(ScoutIngestError):
        ingest_scout_event(
            session,
            scout_event(scout_tdes, schema_version="9.9"),
            [public_group.id],
            super_admin_user.id,
        )


def impactor_tags(obj_id):
    session = DBSession()
    return session.scalars(
        sa.select(ObjTag)
        .join(ObjTagOption, ObjTagOption.id == ObjTag.objtagoption_id)
        .where(ObjTag.obj_id == obj_id, ObjTagOption.name == IMPACTOR_TAG)
    ).all()


def test_a_rated_object_is_tagged_as_an_impactor(
    scout_tdes, public_group, super_admin_user
):
    """Scout's impact_rating is a 0-4 scale, so any non-zero value earns the tag."""
    session = DBSession()
    event = scout_event(scout_tdes)
    event["scout"]["impact_rating"] = 2
    ingest_scout_event(session, event, [public_group.id], super_admin_user.id)
    session.commit()

    assert len(impactor_tags(scout_obj_id(scout_tdes))) == 1


def test_the_tag_is_removed_when_the_rating_returns_to_zero(
    scout_tdes, public_group, super_admin_user
):
    """More observations routinely rule an impact out; the tag must not persist."""
    session = DBSession()
    event = scout_event(scout_tdes)
    event["scout"]["impact_rating"] = 1
    ingest_scout_event(session, event, [public_group.id], super_admin_user.id)
    session.commit()
    assert len(impactor_tags(scout_obj_id(scout_tdes))) == 1

    cleared = scout_event(scout_tdes, event_type="updated")
    cleared["scout"]["impact_rating"] = 0
    ingest_scout_event(session, cleared, [public_group.id], super_admin_user.id)
    session.commit()

    assert impactor_tags(scout_obj_id(scout_tdes)) == []


def test_an_unrated_object_is_not_tagged(scout_tdes, public_group, super_admin_user):
    session = DBSession()
    event = scout_event(scout_tdes)
    event["scout"]["impact_rating"] = 0
    ingest_scout_event(session, event, [public_group.id], super_admin_user.id)
    session.commit()

    assert impactor_tags(scout_obj_id(scout_tdes)) == []


def test_a_designated_body_joins_the_survey_super_obj(
    scout_tdes, public_group, super_admin_user
):
    """The survey path groups by name; scout must land in that same group rather
    than leaving one body grouped twice."""
    session = DBSession()
    iau = f"2026 {uuid.uuid4().hex[:3].upper()}"
    survey_obj = Obj(id=designation_to_obj_id(iau), ra=1.0, dec=2.0)
    session.add(survey_obj)
    session.add(SuperObj(name=sso_label(iau), is_roid=True, objs=[survey_obj]))
    session.commit()

    ingest_scout_event(
        session,
        scout_event(scout_tdes, iau_designation=iau),
        [public_group.id],
        super_admin_user.id,
    )
    session.commit()

    groups = (
        session.scalars(sa.select(SuperObj).where(SuperObj.name == sso_label(iau)))
        .unique()
        .all()
    )
    assert len(groups) == 1, "one body should not be grouped twice"
    assert {obj.id for obj in groups[0].objs} == {
        survey_obj.id,
        scout_obj_id(scout_tdes),
    }

    session.execute(sa.delete(Obj).where(Obj.id == survey_obj.id))
    session.commit()
