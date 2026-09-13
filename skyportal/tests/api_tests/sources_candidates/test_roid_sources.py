"""A moving object's position is one epoch's, so the positional inferences
SkyPortal draws for static sources must not be drawn for it."""

import uuid

import numpy as np
import sqlalchemy as sa

from skyportal.models import DBSession, Obj
from skyportal.tests import api


def make_source(obj_id, ra, dec, group_id, token, is_roid=False):
    status, _ = api(
        "POST",
        "sources",
        data={"id": obj_id, "ra": ra, "dec": dec, "group_ids": [group_id]},
        token=token,
    )
    assert status == 200
    if is_roid:
        session = DBSession()
        obj = session.scalar(sa.select(Obj).where(Obj.id == obj_id))
        obj.is_roid = True
        session.commit()


def test_roid_has_no_duplicates(public_group, upload_data_token):
    """The asteroid is passing through; the static source is not its duplicate."""
    roid_id, static_id = str(uuid.uuid4()), str(uuid.uuid4())
    ra = 200.0 * np.random.random()
    dec = 90.0 * np.random.random()

    make_source(roid_id, ra, dec, public_group.id, upload_data_token, is_roid=True)
    make_source(
        static_id, ra + 0.0001, dec + 0.0005, public_group.id, upload_data_token
    )

    status, data = api("GET", f"sources/{roid_id}", token=upload_data_token)
    assert status == 200
    assert data["data"]["duplicates"] == []
    # Positional galaxy association is equally meaningless for it.
    assert data["data"]["galaxies"] is None


def test_roid_is_not_a_duplicate_of_a_static_source(public_group, upload_data_token):
    """...and the transit must not show up on the static source either."""
    roid_id, static_id = str(uuid.uuid4()), str(uuid.uuid4())
    ra = 200.0 * np.random.random()
    dec = 90.0 * np.random.random()

    make_source(static_id, ra, dec, public_group.id, upload_data_token)
    make_source(
        roid_id,
        ra + 0.0001,
        dec + 0.0005,
        public_group.id,
        upload_data_token,
        is_roid=True,
    )

    status, data = api("GET", f"sources/{static_id}", token=upload_data_token)
    assert status == 200
    assert [d["obj_id"] for d in data["data"]["duplicates"]] == []


def test_static_sources_still_duplicate_each_other(public_group, upload_data_token):
    """Guard: the exemption must not disable duplicate detection generally."""
    first_id, second_id = str(uuid.uuid4()), str(uuid.uuid4())
    ra = 200.0 * np.random.random()
    dec = 90.0 * np.random.random()

    make_source(first_id, ra, dec, public_group.id, upload_data_token)
    make_source(
        second_id, ra + 0.0001, dec + 0.0005, public_group.id, upload_data_token
    )

    status, data = api("GET", f"sources/{first_id}", token=upload_data_token)
    assert status == 200
    assert [d["obj_id"] for d in data["data"]["duplicates"]] == [second_id]
