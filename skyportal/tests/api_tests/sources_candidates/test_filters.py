import uuid

import pytest
from skyportal_py import SkyPortalError
from skyportal_py.brokers import BrokerPost
from skyportal_py.filters import FilterPatch, FilterPost

from skyportal.tests import api, client


def test_filter_list(view_only_token, public_filter):
    filters = client(view_only_token).fetch_filters()
    assert filters[0].name is not None
    assert filters[0].group_id is not None
    assert filters[0].stream_id is not None


def test_token_user_retrieving_filter(view_only_token, public_filter):
    fetched = client(view_only_token).fetch_filter(public_filter.id)
    assert fetched.name is not None
    assert fetched.group_id is not None
    assert fetched.stream_id is not None


def test_token_user_update_filter(manage_groups_token, public_filter):
    sp = client(manage_groups_token)
    sp.update_filter(public_filter.id, FilterPatch(name="new_name"))

    assert sp.fetch_filter(public_filter.id).name == "new_name"


def test_cannot_update_filter_group_stream(view_only_token, public_filter):
    sp = client(view_only_token)
    with pytest.raises(SkyPortalError) as err:
        sp.update_filter(public_filter.id, FilterPatch(group_id=0))
    assert err.value.status_code == 403

    with pytest.raises(SkyPortalError) as err:
        sp.update_filter(public_filter.id, FilterPatch(stream_id=0))
    assert err.value.status_code == 403


def test_token_user_post_delete_filter(
    manage_groups_token, group_with_stream, public_stream
):
    sp = client(manage_groups_token)
    filter_id = sp.post_filter(
        FilterPost(
            name=str(uuid.uuid4()),
            stream_id=public_stream.id,
            group_id=group_with_stream.id,
        )
    ).id

    assert sp.fetch_filter(filter_id).id == filter_id

    sp.delete_filter(filter_id)

    with pytest.raises(SkyPortalError, match="Cannot find a filter with ID"):
        sp.fetch_filter(filter_id)


def test_post_filter_with_unauthorized_stream(
    manage_groups_token, group_with_stream, public_stream
):
    with pytest.raises(SkyPortalError) as err:
        client(manage_groups_token).post_filter(
            FilterPost(
                name=str(uuid.uuid4()),
                stream_id=public_stream.id - 1,
                group_id=group_with_stream.id,
            )
        )
    assert err.value.status_code in [403, 500]


def _force_active(broker_id):
    """Activate a credential-gated broker without the live connection check."""
    import sqlalchemy as sa

    from skyportal.models import Broker, DBSession

    DBSession().execute(
        sa.update(Broker).where(Broker.id == broker_id).values(active=True)
    )
    DBSession().commit()


def _mark_broker_managed(filter_id, broker_id):
    """Point a filter at a broker the way BOOM filter creation does."""
    import sqlalchemy as sa
    from sqlalchemy.orm.attributes import flag_modified

    from skyportal.models import DBSession, Filter

    f = DBSession().scalars(sa.select(Filter).where(Filter.id == filter_id)).first()
    f.altdata = {"boom": {"filter_id": "boom-test-id"}}
    f.broker_id = broker_id
    flag_modified(f, "altdata")
    DBSession().commit()


def test_rename_requires_group_admin(upload_data_token, public_filter):
    """A rename is an admin action even for a user who may otherwise post data."""
    with pytest.raises(SkyPortalError, match="group admin") as err:
        client(upload_data_token).update_filter(
            public_filter.id, FilterPatch(name=f"nope_{uuid.uuid4().hex[:8]}")
        )
    assert err.value.status_code == 403


def test_rename_is_blocked_when_the_broker_rename_fails(
    super_admin_token, public_filter
):
    """The local name must not drift from the broker's.

    The broker here is unreachable, so the propagation attempt fails -- and that
    has to abort the whole rename rather than leaving the two names disagreeing.
    """
    sp = client(super_admin_token)
    broker_id = sp.post_broker(
        BrokerPost(
            name=str(uuid.uuid4()),
            broker_classname="BOOMBROKER",
            altdata={"host": "boom.invalid", "username": "x", "password": "y"},
        )
    ).id
    _force_active(broker_id)

    original_name = sp.fetch_filter(public_filter.id).name

    _mark_broker_managed(public_filter.id, broker_id)

    new_name = f"renamed_{uuid.uuid4().hex[:8]}"
    with pytest.raises(SkyPortalError, match="(?i)rename") as err:
        sp.update_filter(public_filter.id, FilterPatch(name=new_name))
    assert err.value.status_code == 400

    assert sp.fetch_filter(public_filter.id).name == original_name, (
        "local rename outlived the failure"
    )


def test_group_admin_can_rename_filter(group_admin_token, public_filter):
    """The admin gate must not be so tight that it blocks the group's own admin."""
    sp = client(group_admin_token)
    new_name = f"renamed_by_group_admin_{uuid.uuid4().hex[:8]}"
    sp.update_filter(public_filter.id, FilterPatch(name=new_name))

    assert sp.fetch_filter(public_filter.id).name == new_name


def test_super_admin_can_rename_filter(super_admin_token, public_filter):
    """A system admin needs no group membership to rename."""
    sp = client(super_admin_token)
    new_name = f"renamed_by_super_admin_{uuid.uuid4().hex[:8]}"
    sp.update_filter(public_filter.id, FilterPatch(name=new_name))

    assert sp.fetch_filter(public_filter.id).name == new_name


def test_update_filter_autosave(manage_groups_token, public_filter):
    """Ingestion honours the autosave column, so the API must be able to set it."""
    sp = client(manage_groups_token)
    assert sp.fetch_filter(public_filter.id).autosave is False

    sp.update_filter(public_filter.id, FilterPatch(autosave=True))
    assert sp.fetch_filter(public_filter.id).autosave is True

    sp.update_filter(public_filter.id, FilterPatch(autosave=False))
    assert sp.fetch_filter(public_filter.id).autosave is False


def test_update_filter_autosave_writes_no_altdata_mirror(
    manage_groups_token, public_filter
):
    """The column is the only store: nothing mirrors it into altdata, where it
    could drift and let a filter auto-save while the UI shows it off."""
    sp = client(manage_groups_token)
    sp.update_filter(public_filter.id, FilterPatch(autosave=True))

    fetched = sp.fetch_filter(public_filter.id)
    assert fetched.autosave is True
    assert "autoSave" not in (fetched.altdata or {})


def test_attach_a_broker_to_an_existing_filter(super_admin_token, public_filter):
    """A filter created without a broker can be given one.

    Without this the only repair is recreating the filter: POST takes broker_id
    but PATCH used to reject it, and a filter with no broker is never ingested.
    """
    sp = client(super_admin_token)
    assert sp.fetch_filter(public_filter.id).broker_id is None, (
        "fixture already has a broker"
    )

    broker_id = sp.post_broker(
        BrokerPost(
            name=str(uuid.uuid4()),
            broker_classname="GENERICBROKER",
            altdata={"base_url": "https://broker.test", "token": "secret"},
        )
    ).id

    sp.update_filter(public_filter.id, FilterPatch(broker_id=broker_id))

    assert sp.fetch_filter(public_filter.id).broker_id == broker_id

    # moving it again would orphan whatever the first broker holds for it
    with pytest.raises(SkyPortalError) as err:
        sp.update_filter(public_filter.id, FilterPatch(broker_id=broker_id + 1))
    assert err.value.status_code == 400

    # the same broker is a no-op, not an error
    sp.update_filter(public_filter.id, FilterPatch(broker_id=broker_id))


def test_attach_an_unknown_broker_to_a_filter(super_admin_token, public_filter2):
    with pytest.raises(SkyPortalError) as err:
        client(super_admin_token).update_filter(
            public_filter2.id, FilterPatch(broker_id=10**7)
        )
    assert err.value.status_code == 400
