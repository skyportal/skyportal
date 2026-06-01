"""Integration tests for meta-object (SuperObj) read-aggregation.

A SuperObj links several per-survey Objs as one astrophysical object. With the
aggregation flag set, a source's per-source data products — photometry,
classifications, annotations, comments, and tags — are returned as one union
across the linked Objs, each entry keeping its ``obj_id`` for provenance, while
row-level security still holds: a user who can read only one underlying source
must not see any of the others' entries.
"""

import uuid

import sqlalchemy as sa
from tdtax import __version__, taxonomy

from skyportal.models import DBSession, Obj, SuperObj
from skyportal.tests import api


def _link_super_obj(obj_ids):
    """Link the given Objs under a fresh SuperObj; return (super_obj_id, teardown)."""
    session = DBSession()
    objs = [session.scalar(sa.select(Obj).where(Obj.id == oid)) for oid in obj_ids]
    super_obj = SuperObj(name="meta-" + str(uuid.uuid4()))
    super_obj.objs = objs
    session.add(super_obj)
    session.commit()
    super_obj_id = super_obj.id

    def teardown():
        s = DBSession()
        so = s.scalar(sa.select(SuperObj).where(SuperObj.id == super_obj_id))
        if so is not None:
            # Clear the M2M links first so the cascade does not delete the Objs
            # (they are owned by the source fixtures).
            so.objs = []
            s.commit()
            s.delete(so)
            s.commit()

    return super_obj_id, teardown


def _obj_ids(entries):
    return {e["obj_id"] for e in entries}


def _post_taxonomy(token, group_ids):
    status, data = api(
        "POST",
        "taxonomy",
        data={
            "name": "test taxonomy" + str(uuid.uuid4()),
            "hierarchy": taxonomy,
            "group_ids": group_ids,
            "provenance": f"tdtax_{__version__}",
            "version": __version__,
            "isLatest": True,
        },
        token=token,
    )
    assert status == 200, data
    return data["data"]["taxonomy_id"]


def _post_classification(token, obj_id, taxonomy_id, group_ids, classification):
    status, data = api(
        "POST",
        "classification",
        data={
            "obj_id": obj_id,
            "classification": classification,
            "taxonomy_id": taxonomy_id,
            "probability": 1.0,
            "group_ids": group_ids,
        },
        token=token,
    )
    assert status == 200, data
    return data["data"]["classification_id"]


def _post_photometry(token, obj_id, instrument_id, group_ids, mjd):
    status, data = api(
        "POST",
        "photometry",
        data={
            "obj_id": obj_id,
            "mjd": mjd,
            "instrument_id": instrument_id,
            "flux": 12.24,
            "fluxerr": 0.031,
            "zp": 25.0,
            "magsys": "ab",
            "filter": "ztfg",
            "group_ids": group_ids,
        },
        token=token,
    )
    assert status == 200, data
    return data["data"]["ids"][0]


def _seed_obj(token, obj_id, group_id, taxonomy_id, label):
    """Add one classification, annotation, comment, and tag to obj_id, each
    scoped to group_id. label distinguishes this obj's entries."""
    _post_classification(token, obj_id, taxonomy_id, [group_id], "RRab")

    status, data = api(
        "POST",
        f"sources/{obj_id}/annotations",
        data={
            "origin": f"origin_{label}",
            "data": {f"key_{label}": label},
            "group_ids": [group_id],
        },
        token=token,
    )
    assert status == 200, data

    status, data = api(
        "POST",
        f"sources/{obj_id}/comments",
        data={"text": f"comment_{label}", "group_ids": [group_id]},
        token=token,
    )
    assert status == 200, data

    status, data = api(
        "POST",
        "objtagoption",
        data={"name": f"Tag{label}{uuid.uuid4().hex[:8]}"},
        token=token,
    )
    assert status == 200, data
    objtagoption_id = data["data"]["id"]
    status, data = api(
        "POST",
        "objtag",
        data={
            "objtagoption_id": objtagoption_id,
            "obj_id": obj_id,
            "group_ids": [group_id],
        },
        token=token,
    )
    assert status == 200, data


def test_super_obj_flag_on_without_super_obj_is_noop(
    super_admin_token,
    public_source,
    public_group,
    ztf_camera,
):
    """The production default: ``fetchSource`` always sends the aggregation flag,
    so a normal source with no SuperObj is the most-traveled path. With the flag
    ON it must return exactly the source's own entries for every data type — i.e.
    the non-aggregated behavior is unchanged."""
    obj1 = public_source.id

    taxonomy_id = _post_taxonomy(super_admin_token, [public_group.id])
    _seed_obj(super_admin_token, obj1, public_group.id, taxonomy_id, "solo")
    _post_photometry(super_admin_token, obj1, ztf_camera.id, [public_group.id], 58000.0)

    # Embedded source response: flag on, but no SuperObj -> own entries only.
    status, data = api(
        "GET",
        f"sources/{obj1}?includeSuperObjs=true&includeComments=true",
        token=super_admin_token,
    )
    assert status == 200, data
    src = data["data"]
    for key in ["classifications", "annotations", "comments", "tags"]:
        assert _obj_ids(src[key]) == {obj1}, f"{key} changed for a non-meta source"

    # Per-type endpoints: flag on is likewise a no-op.
    status, data = api(
        "GET",
        f"sources/{obj1}/classifications?includeSuperObjs=true",
        token=super_admin_token,
    )
    assert status == 200, data
    assert _obj_ids(data["data"]) == {obj1}

    status, data = api(
        "GET", f"objtag?obj_id={obj1}&includeSuperObjs=true", token=super_admin_token
    )
    assert status == 200, data
    assert _obj_ids(data["data"]) == {obj1}

    status, data = api(
        "GET",
        f"sources/{obj1}/photometry?includeSuperObjsPhotometry=true",
        token=super_admin_token,
    )
    assert status == 200, data
    assert {p["obj_id"] for p in data["data"]} == {obj1}


def test_super_obj_photometry_aggregation_and_rls(
    super_admin_token,
    upload_data_token,
    view_only_token,
    public_source,
    public_source_group2,
    public_group,
    public_group2,
    ztf_camera,
):
    """A meta-object linking a group1 source and a group2 source aggregates
    photometry from both (with per-Obj provenance) only for a user who can read
    each underlying point (RLS)."""
    obj1 = public_source.id  # in public_group (group1)
    obj2 = public_source_group2.id  # in public_group2 (group2)

    _post_photometry(upload_data_token, obj1, ztf_camera.id, [public_group.id], 58000.0)
    _post_photometry(
        super_admin_token, obj2, ztf_camera.id, [public_group2.id], 58001.0
    )

    super_obj_id, teardown = _link_super_obj([obj1, obj2])
    try:
        url = f"sources/{obj1}/photometry"

        # --- Flag off: only the source's own photometry ---
        status, data = api("GET", url, token=super_admin_token)
        assert status == 200, data
        assert {p["obj_id"] for p in data["data"]} == {obj1}

        # --- Flag on, admin: union across both linked Objs, with provenance ---
        status, data = api(
            "GET", f"{url}?includeSuperObjsPhotometry=true", token=super_admin_token
        )
        assert status == 200, data
        assert {p["obj_id"] for p in data["data"]} == {obj1, obj2}

        # --- Flag on, RLS: a group1-only user must NOT see group2's points ---
        status, data = api(
            "GET", f"{url}?includeSuperObjsPhotometry=true", token=view_only_token
        )
        assert status == 200, data
        assert {p["obj_id"] for p in data["data"]} == {obj1}
    finally:
        teardown()


def test_super_obj_classification_aggregation_and_rls(
    super_admin_token,
    classification_token,
    view_only_token,
    public_source,
    public_source_group2,
    public_group,
    public_group2,
):
    """A meta-object linking a group1 source and a group2 source aggregates
    classifications from both — preserving per-Obj provenance — but only for a
    user who can read each underlying classification (RLS). Covers both the
    embedded source response and the per-type classifications endpoint."""
    obj1 = public_source.id  # in public_group (group1)
    obj2 = public_source_group2.id  # in public_group2 (group2)

    # One taxonomy visible to both groups (posted by an admin).
    taxonomy_id = _post_taxonomy(super_admin_token, [public_group.id, public_group2.id])

    # A classification on each underlying source, each scoped to its own group.
    _post_classification(
        classification_token, obj1, taxonomy_id, [public_group.id], "RRab"
    )
    _post_classification(
        super_admin_token, obj2, taxonomy_id, [public_group2.id], "RRc"
    )

    super_obj_id, teardown = _link_super_obj([obj1, obj2])
    try:
        # --- Flag off: behavior is unchanged (only the source's own class.) ---
        status, data = api("GET", f"sources/{obj1}", token=super_admin_token)
        assert status == 200, data
        classes = data["data"]["classifications"]
        assert {c["classification"] for c in classes} == {"RRab"}
        assert all(c["obj_id"] == obj1 for c in classes)

        # --- Flag on, admin: union across both linked Objs, with provenance ---
        status, data = api(
            "GET", f"sources/{obj1}?includeSuperObjs=true", token=super_admin_token
        )
        assert status == 200, data
        classes = data["data"]["classifications"]
        assert {c["classification"] for c in classes} == {"RRab", "RRc"}
        by_class = {c["classification"]: c["obj_id"] for c in classes}
        assert by_class["RRab"] == obj1
        assert by_class["RRc"] == obj2  # provenance: traceable to source B

        # --- Flag on, RLS: a group1-only user must NOT see group2's class. ---
        status, data = api(
            "GET", f"sources/{obj1}?includeSuperObjs=true", token=view_only_token
        )
        assert status == 200, data
        classes = data["data"]["classifications"]
        assert {c["classification"] for c in classes} == {"RRab"}
        assert all(c["obj_id"] == obj1 for c in classes)

        # --- Per-type endpoint honors the same flag (admin: union) ---
        status, data = api(
            "GET",
            f"sources/{obj1}/classifications?includeSuperObjs=true",
            token=super_admin_token,
        )
        assert status == 200, data
        classes = data["data"]
        assert {c["classification"] for c in classes} == {"RRab", "RRc"}

        # --- Per-type endpoint, RLS: group1-only user sees only its own ---
        status, data = api(
            "GET",
            f"sources/{obj1}/classifications?includeSuperObjs=true",
            token=view_only_token,
        )
        assert status == 200, data
        assert {c["classification"] for c in data["data"]} == {"RRab"}
    finally:
        teardown()


def test_super_obj_all_aggregations_and_rls(
    super_admin_token,
    view_only_token,
    public_source,
    public_source_group2,
    public_group,
    public_group2,
):
    """A meta-object linking a group1 and a group2 source aggregates all four
    per-source data products (classifications, annotations, comments, tags) with
    per-Obj provenance, gated by RLS — for both the embedded source response and
    the per-type tag endpoint."""
    obj1 = public_source.id  # in public_group (group1)
    obj2 = public_source_group2.id  # in public_group2 (group2)

    taxonomy_id = _post_taxonomy(super_admin_token, [public_group.id, public_group2.id])

    _seed_obj(super_admin_token, obj1, public_group.id, taxonomy_id, "one")
    _seed_obj(super_admin_token, obj2, public_group2.id, taxonomy_id, "two")

    super_obj_id, teardown = _link_super_obj([obj1, obj2])
    try:
        # --- Flag off: each type is just the source's own (no aggregation) ---
        status, data = api(
            "GET", f"sources/{obj1}?includeComments=true", token=super_admin_token
        )
        assert status == 200, data
        src = data["data"]
        for key in ["classifications", "annotations", "comments", "tags"]:
            assert _obj_ids(src[key]) == {obj1}, f"{key} should be obj1-only when off"

        # --- Flag on, admin: every type is the union across both linked Objs ---
        status, data = api(
            "GET",
            f"sources/{obj1}?includeSuperObjs=true&includeComments=true",
            token=super_admin_token,
        )
        assert status == 200, data
        src = data["data"]
        for key in ["classifications", "annotations", "comments", "tags"]:
            assert _obj_ids(src[key]) == {obj1, obj2}, f"{key} union missing a source"

        # --- Flag on, RLS: a group1-only user sees only the group1 source ---
        status, data = api(
            "GET",
            f"sources/{obj1}?includeSuperObjs=true&includeComments=true",
            token=view_only_token,
        )
        assert status == 200, data
        src = data["data"]
        for key in ["classifications", "annotations", "comments", "tags"]:
            assert _obj_ids(src[key]) == {obj1}, f"{key} leaked a forbidden source"

        # --- Per-type tag endpoint honors the flag + RLS too ---
        status, data = api(
            "GET",
            f"objtag?obj_id={obj1}&includeSuperObjs=true",
            token=super_admin_token,
        )
        assert status == 200, data
        assert _obj_ids(data["data"]) == {obj1, obj2}

        status, data = api(
            "GET",
            f"objtag?obj_id={obj1}&includeSuperObjs=true",
            token=view_only_token,
        )
        assert status == 200, data
        assert _obj_ids(data["data"]) == {obj1}
    finally:
        teardown()
