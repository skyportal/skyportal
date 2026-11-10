from skyportal.handlers.api.internal.memory import FIELDS, probe
from skyportal.tests import api


def test_probe_schema():
    entry = probe()
    assert set(entry) == {"time", *FIELDS}
    assert entry["time"].endswith("+00:00")
    for field in FIELDS:
        assert entry[field] is None or isinstance(entry[field], int)
    assert entry["rss_bytes"] > 0


def test_memory_history(super_admin_token):
    status, data = api("GET", "internal/memory", token=super_admin_token)
    assert status == 200
    running = [p for p in data["data"]["processes"] if p["running"]]
    assert running
    for process in running:
        assert isinstance(process["forked_from_zygote"], bool)
        assert set(process["history"]) == {"time", *FIELDS}
        assert len({len(values) for values in process["history"].values()}) == 1


def test_memory_trim(super_admin_token):
    status, data = api("POST", "internal/memory", token=super_admin_token)
    assert status == 200
    processes = data["data"]["processes"]
    assert processes
    for process in processes:
        trim = process["trim"]
        assert trim["requested_at"] == data["data"]["requested_at"]
        assert set(trim["before"]) == set(trim["after"]) == {"time", *FIELDS}


def test_memory_requires_admin(view_only_token):
    status, _ = api("GET", "internal/memory", token=view_only_token)
    assert status == 403
