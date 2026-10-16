"""What a Zooniverse answer writes back into SkyPortal.

The Panoptes half of a classification cannot be exercised without Zooniverse,
so these drive `record_in_skyportal` directly: the answer index is mapped to a
taxonomy class, the object is saved to the configured groups, and a failure on
either is reported rather than raised (Panoptes has already taken the answer by
then, so the volunteer must not be asked to classify the subject twice).
"""

import asyncio
import uuid

import pytest
import sqlalchemy as sa

from baselayer.app import models as baselayer_models
from skyportal.handlers.api.zooniverse import record_in_skyportal
from skyportal.models import Classification, DBSession, Obj, Source, Taxonomy

CLASS_MAP = {"0": "Algol", "1": "RS CVn"}


@pytest.fixture()
def taxonomy(public_group, super_admin_user):
    taxonomy = Taxonomy(
        name=f"zooniverse-{uuid.uuid4().hex[:8]}",
        hierarchy={
            "class": "Sources",
            "subclasses": [{"class": name} for name in CLASS_MAP.values()],
        },
        version="0.1",
        groups=[public_group],
    )
    DBSession().add(taxonomy)
    DBSession().commit()
    yield taxonomy
    DBSession().execute(sa.delete(Taxonomy).where(Taxonomy.id == taxonomy.id))
    DBSession().commit()


@pytest.fixture()
def unsaved_obj():
    obj = Obj(id=f"ZTF{uuid.uuid4().hex[:10]}", ra=10.0, dec=20.0)
    DBSession().add(obj)
    DBSession().commit()
    yield obj
    DBSession().execute(sa.delete(Obj).where(Obj.id == obj.id))
    DBSession().commit()


def record(user, conf, data, value):
    """`post_classification` verifies access at commit time, so the session has
    to be the verified one a handler would hand it."""

    async def _run():
        async with baselayer_models.AsyncVerifiedSession(user) as session:
            user_in_session = await session.merge(user)
            session.user_or_token = user_in_session
            return await record_in_skyportal(
                session, user_in_session.id, conf, data, value
            )

    return asyncio.run(_run())


def test_an_answer_saves_and_classifies_in_skyportal(
    super_admin_user, public_group, taxonomy, unsaved_obj
):
    outcome = record(
        super_admin_user,
        {
            "save_group_ids": [public_group.id],
            "taxonomy_id": taxonomy.id,
            "class_map": CLASS_MAP,
            "classification_source": "volunteer",
        },
        {"obj_id": unsaved_obj.id},
        1,
    )
    assert "save_error" not in outcome, outcome
    assert "classification_error" not in outcome, outcome
    assert outcome["saved_to_groups"] == [public_group.id]

    DBSession().expire_all()
    assert DBSession().scalar(
        sa.select(Source).where(
            Source.obj_id == unsaved_obj.id, Source.group_id == public_group.id
        )
    )
    classification = DBSession().scalar(
        sa.select(Classification).where(Classification.obj_id == unsaved_obj.id)
    )
    assert classification.classification == "RS CVn"
    # Origin is what separates a volunteer's call from a scanner's in the UI.
    assert classification.origin == "zooniverse"
    assert classification.author_id == super_admin_user.id


def test_an_unmapped_answer_writes_nothing(
    super_admin_user, public_group, taxonomy, unsaved_obj
):
    """A task whose answers are not in class_map still classifies on Zooniverse,
    and simply leaves SkyPortal alone."""
    outcome = record(
        super_admin_user,
        {
            "taxonomy_id": taxonomy.id,
            "class_map": CLASS_MAP,
            "classification_source": "volunteer",
        },
        {"obj_id": unsaved_obj.id},
        7,
    )
    assert outcome == {}

    DBSession().expire_all()
    assert (
        DBSession().scalar(
            sa.select(Classification).where(Classification.obj_id == unsaved_obj.id)
        )
        is None
    )


def test_classifying_without_a_taxonomy_is_reported_not_raised(
    super_admin_user, unsaved_obj
):
    outcome = record(
        super_admin_user,
        {"class_map": CLASS_MAP, "classification_source": "volunteer"},
        {"obj_id": unsaved_obj.id},
        0,
    )
    assert "taxonomy" in outcome["classification_error"].lower()


def test_a_failed_save_is_reported_and_does_not_stop_the_classification(
    super_admin_user, public_group, taxonomy, unsaved_obj
):
    outcome = record(
        super_admin_user,
        {
            "taxonomy_id": taxonomy.id,
            "class_map": CLASS_MAP,
            "classification_source": "volunteer",
        },
        {"obj_id": unsaved_obj.id, "save_group_ids": [-1]},
        0,
    )
    assert "save_error" in outcome, outcome
    assert outcome.get("skyportal_classification_id") is not None, outcome


def test_under_consensus_an_answer_saves_but_does_not_classify(
    super_admin_user, public_group, taxonomy, unsaved_obj
):
    """The default: Caesar aggregates the volunteers and posts one verdict per
    object, so a single answer must not put a class on the source."""
    outcome = record(
        super_admin_user,
        {
            "save_group_ids": [public_group.id],
            "taxonomy_id": taxonomy.id,
            "class_map": CLASS_MAP,
        },
        {"obj_id": unsaved_obj.id},
        1,
    )
    assert outcome["saved_to_groups"] == [public_group.id]
    assert "skyportal_classification_id" not in outcome

    DBSession().expire_all()
    assert (
        DBSession().scalar(
            sa.select(Classification).where(Classification.obj_id == unsaved_obj.id)
        )
        is None
    )
