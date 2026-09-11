import json
import pathlib
import uuid

import pytest

from skyportal.models import Annotation, DBSession
from skyportal.utils.neofixer import (
    ANNOTATION_ORIGIN,
    annotate_matching_objects,
    annotation_data,
    build_target_index,
    designation_key,
    fetch_targets,
)

# A handful of real targets, covering a comet, a NEOCP object with no
# designation yet, and radar and NHATS targets.
FIXTURE = pathlib.Path(__file__).parents[1] / "data" / "neofixer_targets.json"


def _payload(targets):
    return {"result": {"objects": targets}}


def _unique_target(**overrides):
    """A target under a designation no other test run can have used.

    The database keeps objects between runs, so a shared designation would let
    a leftover object match too and make the counts non-deterministic.
    """
    tag = uuid.uuid4().hex[:6].upper()
    return {
        **TARGET,
        "packed": f"K26D{tag}",
        "provisional": f"2026 ZZ{tag}",
        **overrides,
    }


TARGET = {
    "packed": "K26D01M",
    "provisional": "2026 DM1",
    "number": None,
    "score": 10.46,
    "priority": "critical",
    "urgency": 100,
    "vmag": 21.05,
    "moid": 0.0532,
    "radar": None,
    "comet": None,
    "time": "2026-09-06T23:30:00.000Z",
}


def test_designation_key_ignores_spacing_and_case():
    assert designation_key("2026 DM1") == designation_key("2026dm1")
    assert designation_key(None) is None
    assert designation_key("") is None


def test_index_covers_every_designation_a_target_carries():
    index = build_target_index(_payload({"K26D01M": TARGET}))
    # SkyPortal stores whatever the broker supplied, so both forms must resolve.
    assert index[designation_key("2026 DM1")] is TARGET
    assert index[designation_key("K26D01M")] is TARGET


def test_index_covers_numbered_objects():
    numbered = {**TARGET, "provisional": "1999 RQ36", "number": 101955}
    index = build_target_index(_payload({"K99R36Q": numbered}))
    assert index[designation_key("101955")] is numbered
    assert index[designation_key("(101955)")] is numbered
    assert index[designation_key("1999 RQ36")] is numbered


def test_annotation_data_keeps_the_ranking_and_drops_empties():
    data = annotation_data(TARGET)
    assert data["score"] == 10.46
    assert data["priority"] == "critical"
    # NEOFixer sends null for flags that do not apply; they are not facts.
    assert "radar" not in data and "comet" not in data
    # Nor the fields that belong on NEOFixer's own site.
    assert "packed" not in data and "ra deg" not in data


def test_annotates_a_tracked_object_and_updates_in_place(
    public_source, public_group, super_admin_user
):
    target = _unique_target()
    public_source.is_roid = True
    public_source.mpc_name = target["provisional"]
    DBSession().commit()

    session = DBSession()
    counts = annotate_matching_objects(
        session,
        _payload({target["packed"]: target}),
        super_admin_user.id,
        [public_group.id],
    )
    session.commit()
    assert counts["matched"] == 1 and counts["created"] == 1

    annotation = session.scalar(
        Annotation.select(super_admin_user).where(
            Annotation.obj_id == public_source.id,
            Annotation.origin == ANNOTATION_ORIGIN,
        )
    )
    assert annotation.data["priority"] == "critical"

    # A later list must revise the score rather than pile up annotations.
    counts = annotate_matching_objects(
        session,
        _payload({target["packed"]: {**target, "score": 2.0, "priority": "low"}}),
        super_admin_user.id,
        [public_group.id],
    )
    session.commit()
    assert counts["updated"] == 1 and counts["created"] == 0

    rows = session.scalars(
        Annotation.select(super_admin_user).where(
            Annotation.obj_id == public_source.id,
            Annotation.origin == ANNOTATION_ORIGIN,
        )
    ).all()
    assert len(rows) == 1
    assert rows[0].data["priority"] == "low"


def test_objects_neofixer_does_not_rank_are_left_alone(
    public_source, public_group, super_admin_user
):
    public_source.is_roid = True
    public_source.mpc_name = _unique_target()["provisional"]
    DBSession().commit()

    session = DBSession()
    counts = annotate_matching_objects(
        session,
        _payload({t["packed"]: t for t in [_unique_target()]}),
        super_admin_user.id,
        [public_group.id],
    )
    session.commit()
    assert counts["matched"] == 0 and counts["created"] == 0


@pytest.fixture
def sample_payload():
    with open(FIXTURE) as f:
        return json.load(f)


def test_fetch_targets_passes_the_site_and_returns_the_payload(
    monkeypatch, sample_payload
):
    """The API is never called in tests; this pins the request we would make."""
    calls = {}

    class Response:
        def raise_for_status(self):
            calls["raised"] = True

        def json(self):
            return sample_payload

    def fake_get(url, params=None, timeout=None):
        calls.update(url=url, params=params, timeout=timeout)
        return Response()

    monkeypatch.setattr("skyportal.utils.neofixer.requests.get", fake_get)
    payload = fetch_targets("https://example.test/targets/", 500, timeout=30)

    assert calls["url"] == "https://example.test/targets/"
    assert calls["params"] == {"site": 500}
    assert calls["timeout"] == 30 and calls["raised"]
    assert payload["result"]["num"] == len(payload["result"]["objects"])


def test_real_payload_indexes_every_target(sample_payload):
    index = build_target_index(sample_payload)
    targets = sample_payload["result"]["objects"]
    for packed, target in targets.items():
        assert index[designation_key(packed)] is target
        if target.get("provisional"):
            assert index[designation_key(target["provisional"])] is target
        # Comet fragments carry a non-numeric "number" such as "73Pbt".
        if target.get("number"):
            assert index[designation_key(target["number"])] is target


def test_real_payload_annotates_the_fields_an_observer_ranks_on(sample_payload):
    for target in sample_payload["result"]["objects"].values():
        data = annotation_data(target)
        assert "score" in data and "priority" in data
        assert not any(value is None for value in data.values())


def test_annotating_from_the_real_payload(
    public_source, public_group, super_admin_user, sample_payload
):
    target = sample_payload["result"]["objects"]["K07U01X"]
    public_source.is_roid = True
    public_source.mpc_name = target["provisional"]
    DBSession().commit()

    session = DBSession()
    annotate_matching_objects(
        session, sample_payload, super_admin_user.id, [public_group.id]
    )
    session.commit()

    annotation = session.scalar(
        Annotation.select(super_admin_user).where(
            Annotation.obj_id == public_source.id,
            Annotation.origin == ANNOTATION_ORIGIN,
        )
    )
    assert annotation.data["score"] == target["score"]
    assert annotation.data["priority"] == target["priority"]


def test_objects_that_are_not_solar_system_are_skipped(
    public_source, public_group, super_admin_user
):
    """A matching designation is not enough; the object must be a moving one."""
    target = _unique_target()
    public_source.is_roid = False
    public_source.mpc_name = target["provisional"]
    DBSession().commit()

    session = DBSession()
    counts = annotate_matching_objects(
        session,
        _payload({target["packed"]: target}),
        super_admin_user.id,
        [public_group.id],
    )
    session.commit()
    assert counts["matched"] == 0

    assert (
        session.scalar(
            Annotation.select(super_admin_user).where(
                Annotation.obj_id == public_source.id,
                Annotation.origin == ANNOTATION_ORIGIN,
            )
        )
        is None
    )
