"""Integration tests for meta-object (SuperObj) read-aggregation.

A SuperObj links several per-survey Objs as one astrophysical object. With the
aggregation flag set, a source's per-source data products — photometry,
classifications, annotations, comments, and tags — are returned as one union
across the linked Objs, each entry keeping its ``obj_id`` for provenance, while
row-level security still holds: a user who can read only one underlying source
must not see any of the others' entries.
"""

import base64
import io
import uuid

import sqlalchemy as sa
from PIL import Image
from skyportal_py.classifications import ClassificationPost
from skyportal_py.photometry import PhotometryPost
from skyportal_py.taxonomies import TaxonomyPost
from skyportal_py.thumbnails import ThumbnailPost
from tdtax import __version__, taxonomy

from skyportal.models import DBSession, Obj, SuperObj
from skyportal.tests import client


def _post_thumbnail(token, obj_id, ttype, survey):
    buf = io.BytesIO()
    Image.new("RGB", (16, 16), (10, 20, 30)).save(buf, format="PNG")
    return (
        client(token)
        .post_thumbnail(
            ThumbnailPost(
                obj_id=obj_id,
                data=base64.b64encode(buf.getvalue()).decode("utf-8"),
                ttype=ttype,
                survey=survey,
            )
        )
        .id
    )


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
    return {e.obj_id for e in entries}


def _post_taxonomy(token, group_ids):
    return (
        client(token)
        .post_taxonomy(
            TaxonomyPost(
                name="test taxonomy" + str(uuid.uuid4()),
                hierarchy=taxonomy,
                group_ids=group_ids,
                provenance=f"tdtax_{__version__}",
                version=__version__,
                is_latest=True,
            )
        )
        .taxonomy_id
    )


def _post_classification(token, obj_id, taxonomy_id, group_ids, classification):
    return (
        client(token)
        .post_classification(
            ClassificationPost(
                obj_id=obj_id,
                classification=classification,
                taxonomy_id=taxonomy_id,
                probability=1.0,
                group_ids=group_ids,
            )
        )
        .classification_id
    )


def _post_photometry(token, obj_id, instrument_id, group_ids, mjd):
    return (
        client(token)
        .post_photometry(
            PhotometryPost(
                obj_id=obj_id,
                mjd=mjd,
                instrument_id=instrument_id,
                flux=12.24,
                fluxerr=0.031,
                zp=25.0,
                magsys="ab",
                filter="ztfg",
                group_ids=group_ids,
            )
        )
        .ids[0]
    )


def _seed_obj(token, obj_id, group_id, taxonomy_id, label):
    """Add one classification, annotation, comment, and tag to obj_id, each
    scoped to group_id. label distinguishes this obj's entries."""
    _post_classification(token, obj_id, taxonomy_id, [group_id], "RRab")

    sp = client(token)
    sp.post_annotation(
        obj_id,
        f"origin_{label}",
        {f"key_{label}": label},
        group_ids=[group_id],
    )

    sp.post_comment(obj_id, f"comment_{label}", group_ids=[group_id])

    objtagoption_id = sp.post_obj_tag_option(f"Tag{label}{uuid.uuid4().hex[:8]}").id
    sp.post_obj_tag(obj_id, objtagoption_id, group_ids=[group_id])


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

    sp = client(super_admin_token)

    # Embedded source response: flag on, but no SuperObj -> own entries only.
    src = sp.fetch_source(obj1, include_super_objs=True, include_comments=True)
    for key in ["classifications", "annotations", "comments", "tags"]:
        assert _obj_ids(getattr(src, key)) == {obj1}, (
            f"{key} changed for a non-meta source"
        )

    # Per-type endpoints: flag on is likewise a no-op.
    classes = sp.fetch_classifications(obj1, include_super_objs=True)
    assert _obj_ids(classes) == {obj1}

    tags = sp.fetch_obj_tags(obj_id=obj1, include_super_objs=True)
    assert _obj_ids(tags) == {obj1}

    points = sp.fetch_photometry(obj1, include_super_objs_photometry=True)
    assert {p.obj_id for p in points} == {obj1}


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
        # --- Flag off: only the source's own photometry ---
        points = client(super_admin_token).fetch_photometry(obj1)
        assert {p.obj_id for p in points} == {obj1}

        # --- Flag on, admin: union across both linked Objs, with provenance ---
        points = client(super_admin_token).fetch_photometry(
            obj1, include_super_objs_photometry=True
        )
        assert {p.obj_id for p in points} == {obj1, obj2}

        # --- Flag on, RLS: a group1-only user must NOT see group2's points ---
        points = client(view_only_token).fetch_photometry(
            obj1, include_super_objs_photometry=True
        )
        assert {p.obj_id for p in points} == {obj1}
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
        classes = client(super_admin_token).fetch_source(obj1).classifications
        assert {c.classification for c in classes} == {"RRab"}
        assert all(c.obj_id == obj1 for c in classes)

        # --- Flag on, admin: union across both linked Objs, with provenance ---
        classes = (
            client(super_admin_token)
            .fetch_source(obj1, include_super_objs=True)
            .classifications
        )
        assert {c.classification for c in classes} == {"RRab", "RRc"}
        by_class = {c.classification: c.obj_id for c in classes}
        assert by_class["RRab"] == obj1
        assert by_class["RRc"] == obj2  # provenance: traceable to source B

        # --- Flag on, RLS: a group1-only user must NOT see group2's class. ---
        classes = (
            client(view_only_token)
            .fetch_source(obj1, include_super_objs=True)
            .classifications
        )
        assert {c.classification for c in classes} == {"RRab"}
        assert all(c.obj_id == obj1 for c in classes)

        # --- Per-type endpoint honors the same flag (admin: union) ---
        classes = client(super_admin_token).fetch_classifications(
            obj1, include_super_objs=True
        )
        assert {c.classification for c in classes} == {"RRab", "RRc"}

        # --- Per-type endpoint, RLS: group1-only user sees only its own ---
        classes = client(view_only_token).fetch_classifications(
            obj1, include_super_objs=True
        )
        assert {c.classification for c in classes} == {"RRab"}
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
        src = client(super_admin_token).fetch_source(obj1, include_comments=True)
        for key in ["classifications", "annotations", "comments", "tags"]:
            assert _obj_ids(getattr(src, key)) == {obj1}, (
                f"{key} should be obj1-only when off"
            )

        # --- Flag on, admin: every type is the union across both linked Objs ---
        src = client(super_admin_token).fetch_source(
            obj1, include_super_objs=True, include_comments=True
        )
        for key in ["classifications", "annotations", "comments", "tags"]:
            assert _obj_ids(getattr(src, key)) == {obj1, obj2}, (
                f"{key} union missing a source"
            )

        # --- Flag on, RLS: a group1-only user sees only the group1 source ---
        src = client(view_only_token).fetch_source(
            obj1, include_super_objs=True, include_comments=True
        )
        for key in ["classifications", "annotations", "comments", "tags"]:
            assert _obj_ids(getattr(src, key)) == {obj1}, (
                f"{key} leaked a forbidden source"
            )

        # --- Per-type tag endpoint honors the flag + RLS too ---
        tags = client(super_admin_token).fetch_obj_tags(
            obj_id=obj1, include_super_objs=True
        )
        assert _obj_ids(tags) == {obj1, obj2}

        tags = client(view_only_token).fetch_obj_tags(
            obj_id=obj1, include_super_objs=True
        )
        assert _obj_ids(tags) == {obj1}
    finally:
        teardown()


def test_super_obj_thumbnail_aggregation(
    super_admin_token,
    public_source,
    public_source_group2,
):
    """A meta-object linking two per-survey Objs aggregates their alert-cutout
    thumbnails into the source response, each tagged with its survey so the
    frontend can label per-survey tiles. Access is via ``Thumbnail.select(user)``,
    so only cutouts of readable objs are returned."""
    obj1 = public_source.id
    obj2 = public_source_group2.id

    _post_thumbnail(super_admin_token, obj1, "new", "ZTF")
    _post_thumbnail(super_admin_token, obj2, "new", "LSST")

    def new_pairs(source):
        return {(t.survey, t.obj_id) for t in source.thumbnails if t.type == "new"}

    super_obj_id, teardown = _link_super_obj([obj1, obj2])
    try:
        # Flag off: only the source's own cutout (survey-tagged), not the link's.
        source = client(super_admin_token).fetch_source(obj1, include_thumbnails=True)
        pairs = new_pairs(source)
        assert ("ZTF", obj1) in pairs
        assert not any(oid == obj2 for _, oid in pairs)

        # Flag on: both surveys' cutouts, each carrying its survey label.
        source = client(super_admin_token).fetch_source(
            obj1, include_thumbnails=True, include_super_objs=True
        )
        assert {("ZTF", obj1), ("LSST", obj2)} <= new_pairs(source)
    finally:
        teardown()
