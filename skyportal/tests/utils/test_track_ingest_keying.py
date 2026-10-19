"""What a moving object's Obj is keyed on.

A positional survey renames a mover almost every visit, so the key can never be
the object id. A known object has a designation; an undiscovered one has only
the track the linker built.
"""

from skyportal.utils.sso_ingest import (
    extract_track_id,
    sso_key_for,
    track_to_obj_id,
)

TRACK_BLOCK = {"properties": {"track": {"id": "BT000001", "n_detections": 7}}}
DESIGNATED = {"properties": {"sso": {"designation": "187965"}}}


def test_a_track_id_is_read_from_the_alert():
    assert extract_track_id(TRACK_BLOCK) == "BT000001"


def test_a_track_id_is_read_from_filter_annotations():
    # The same two places a designation can arrive, since which one carries it
    # is a broker-side decision.
    assert extract_track_id(None, {7: {"track_id": "BT000002"}}) == "BT000002"


def test_no_track_anywhere_reads_as_none():
    assert extract_track_id({"properties": {}}, {7: {"other": 1}}) is None


def test_a_track_obj_id_is_distinct_from_a_designation():
    # trk_ and sso_ must not collide: a track id and a designation are different
    # namespaces and could otherwise name the same Obj.
    assert track_to_obj_id("BT000001") == "trk_BT000001"
    assert track_to_obj_id("187965") != "sso_187965"


def test_a_designation_wins_over_a_track_id():
    # Once the MPC has named it, that is the identity to keep; a track later
    # matched to one folds in rather than leaving a duplicate.
    both = {"properties": {"sso": {"designation": "187965"}, "track": {"id": "BT9"}}}
    obj_id, kind, key = sso_key_for(both)
    assert (obj_id, kind, key) == ("sso_187965", "designation", "187965")


def test_a_track_alone_keys_on_the_track():
    assert sso_key_for(TRACK_BLOCK) == ("trk_BT000001", "track", "BT000001")


def test_a_designation_alone_keys_on_the_designation():
    assert sso_key_for(DESIGNATED) == ("sso_187965", "designation", "187965")


def test_neither_keys_on_nothing():
    assert sso_key_for({"properties": {}}) == (None, None, None)


def test_a_track_id_survives_the_url_safe_slug():
    # Obj ids appear in URL paths, so the id has to come through unmangled.
    assert track_to_obj_id("BT000123") == "trk_BT000123"
