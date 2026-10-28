"""The bulk TNS refresh: who may call the endpoint, what it accepts, and which
objects a stale-name selection picks up.

The tns_retrieval_queue service is disabled under test_config.yaml, so these
exercise everything the handler decides before it hands a batch to the queue,
and the selection itself through its query.
"""

import uuid

import sqlalchemy as sa
from tdtax import __version__, taxonomy

from skyportal.models import DBSession, Obj, User
from skyportal.tests import api
from skyportal.utils.tns import stale_tns_name_select


def set_tns_name(obj_id, tns_name):
    DBSession().execute(
        sa.update(Obj).where(Obj.id == obj_id).values(tns_name=tns_name)
    )
    DBSession().commit()


def stale_ids(username, limit=1000):
    user = DBSession().scalar(sa.select(User).where(User.username == username))
    return DBSession().scalars(stale_tns_name_select(user, limit)).all()


def classify(obj_id, token, taxonomy_token, group_id):
    status, data = api(
        "POST",
        "taxonomy",
        data={
            "name": "test taxonomy" + str(uuid.uuid4()),
            "hierarchy": taxonomy,
            "group_ids": [group_id],
            "provenance": f"tdtax_{__version__}",
            "version": __version__,
            "isLatest": True,
        },
        token=taxonomy_token,
    )
    assert status == 200
    status, _ = api(
        "POST",
        "classification",
        data={
            "obj_id": obj_id,
            "classification": "Algol",
            "taxonomy_id": data["data"]["taxonomy_id"],
            "probability": 1.0,
            "group_ids": [group_id],
        },
        token=token,
    )
    assert status == 200


def test_a_view_only_token_cannot_queue_a_refresh(public_source, view_only_token):
    status, _ = api(
        "POST",
        "sources/tns",
        data={"obj_ids": [public_source.id]},
        token=view_only_token,
    )
    assert status in (400, 401)


def test_a_request_names_either_objects_or_the_stale_selection(
    public_source, manage_sources_token
):
    for data in ({}, {"obj_ids": [public_source.id], "stale_names_only": True}):
        status, response = api(
            "POST", "sources/tns", data=data, token=manage_sources_token
        )
        assert status == 400
        assert "exactly one" in response["message"]


def test_a_negative_radius_is_refused(public_source, manage_sources_token):
    status, response = api(
        "POST",
        "sources/tns",
        data={"obj_ids": [public_source.id], "radius": -1},
        token=manage_sources_token,
    )
    assert status == 400
    assert "radius" in response["message"]


def test_an_unknown_object_is_named_rather_than_skipped(
    public_source, manage_sources_token
):
    status, response = api(
        "POST",
        "sources/tns",
        data={"obj_ids": [public_source.id, "ZTF99nosuchsource"]},
        token=manage_sources_token,
    )
    assert status == 400
    assert "ZTF99nosuchsource" in response["message"]


def test_a_batch_over_the_cap_is_refused(public_source, manage_sources_token):
    """max_objects lowers the cap, so one request cannot outrun its own limit."""
    status, response = api(
        "POST",
        "sources/tns",
        data={"obj_ids": [public_source.id, public_source.id], "max_objects": 1},
        token=manage_sources_token,
    )
    assert status == 400
    assert "more than 1" in response["message"]


def test_a_cap_below_one_is_refused(public_source, manage_sources_token):
    status, response = api(
        "POST",
        "sources/tns",
        data={"obj_ids": [public_source.id], "max_objects": 0},
        token=manage_sources_token,
    )
    assert status == 400
    assert "max_objects" in response["message"]


def test_a_classified_at_name_enters_the_stale_selection(
    public_source,
    public_group,
    group_admin_user,
    taxonomy_token,
    classification_token,
):
    classify(public_source.id, classification_token, taxonomy_token, public_group.id)
    set_tns_name(public_source.id, "AT 2026agsu")
    assert public_source.id in stale_ids(group_admin_user.username)


def test_an_upgraded_name_leaves_the_stale_selection(
    public_source,
    public_group,
    group_admin_user,
    taxonomy_token,
    classification_token,
):
    """The AT to SN upgrade is the whole point, so an SN name stops being picked."""
    classify(public_source.id, classification_token, taxonomy_token, public_group.id)
    set_tns_name(public_source.id, "AT 2026agsu")
    assert public_source.id in stale_ids(group_admin_user.username)

    set_tns_name(public_source.id, "SN 2026agsu")
    assert public_source.id not in stale_ids(group_admin_user.username)


def test_an_unclassified_at_name_is_left_alone(public_source_no_data, group_admin_user):
    """TNS has nothing new to say about an object nobody has classified."""
    set_tns_name(public_source_no_data.id, "AT 2026agsv")
    assert public_source_no_data.id not in stale_ids(group_admin_user.username)


def test_the_selection_honours_its_limit(
    public_source,
    public_group,
    group_admin_user,
    taxonomy_token,
    classification_token,
):
    classify(public_source.id, classification_token, taxonomy_token, public_group.id)
    set_tns_name(public_source.id, "AT 2026agsu")
    assert len(stale_ids(group_admin_user.username, limit=1)) == 1
