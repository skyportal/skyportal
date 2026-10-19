from types import SimpleNamespace

from skyportal.handlers.api.deployment import with_changes

GITLOG = [
    {"sha": "ddddddd1", "description": "d"},
    {"sha": "ccccccc1", "description": "c"},
    {"sha": "bbbbbbb1", "description": "b"},
    {"sha": "aaaaaaa1", "description": "a"},
]


def deployment(id, sha):
    return SimpleNamespace(id=id, version="1.0", commit={"sha": sha}, created_at=None)


def test_changes_since_previous_deployment():
    deployments = [deployment(2, "ddddddd"), deployment(1, "bbbbbbb")]
    latest, first = with_changes(deployments, GITLOG)
    assert [c["sha"] for c in latest["changes"]] == ["ddddddd1", "ccccccc1"]
    assert latest["n_changes"] == 2
    assert not latest["rollback"]
    assert first["changes"] is None


def test_rollback_has_no_changes():
    deployments = [deployment(2, "aaaaaaa"), deployment(1, "ccccccc")]
    rollback, _ = with_changes(deployments, GITLOG)
    assert rollback["rollback"]
    assert rollback["changes"] == []


def test_unknown_commit():
    deployments = [deployment(2, "eeeeeee"), deployment(1, "ccccccc")]
    latest, _ = with_changes(deployments, GITLOG)
    assert latest["changes"] is None
    assert not latest["rollback"]
