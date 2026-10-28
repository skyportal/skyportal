"""Unit tests for the bulk TNS refresh: splitting a batch into queue tasks,
pacing the requests, and the dispatch helper's contract with the microservice.
"""

import types

import pytest

from skyportal.utils.tns import (
    expand_bulk_tns_task,
    get_tns_bulk,
    tns_request_delay,
)


def test_a_batch_becomes_one_task_per_object():
    tasks = expand_bulk_tns_task(
        {"obj_ids": ["ZTF26aaa", "ZTF26bbb"], "radius": 3.0, "user_id": 7}
    )
    assert tasks == [
        {"obj_id": "ZTF26aaa", "radius": 3.0, "user_id": 7},
        {"obj_id": "ZTF26bbb", "radius": 3.0, "user_id": 7},
    ]


def test_the_batch_key_does_not_survive_into_a_task():
    """Each task takes the single-object path through the queue."""
    for task in expand_bulk_tns_task({"obj_ids": ["ZTF26aaa"], "user_id": 1}):
        assert "obj_ids" not in task


@pytest.mark.parametrize("obj_ids", [[], None, "ZTF26aaa", 3])
def test_a_batch_without_a_list_of_objects_is_refused(obj_ids):
    with pytest.raises(ValueError, match="non-empty list"):
        expand_bulk_tns_task({"obj_ids": obj_ids, "user_id": 1})


def test_requests_are_spaced_by_the_configured_interval():
    assert tns_request_delay(100.0, 100.0, 3) == 3.0
    assert tns_request_delay(100.0, 101.5, 3) == 1.5


def test_an_elapsed_interval_waits_no_longer():
    """A queue slower than the limit runs at its own pace."""
    assert tns_request_delay(100.0, 103.0, 3) == 0.0
    assert tns_request_delay(100.0, 160.0, 3) == 0.0


def test_the_first_request_of_a_run_is_not_delayed():
    assert tns_request_delay(0.0, 5000.0, 3) == 0.0


def test_the_dispatch_sends_one_request_for_the_whole_batch(monkeypatch):
    calls = []

    def fake_post(url, json=None, timeout=None):
        calls.append(json)
        return types.SimpleNamespace(
            status_code=200, json=lambda: {"data": {"queue_length": 2}}
        )

    monkeypatch.setattr("skyportal.utils.tns.requests.post", fake_post)
    assert get_tns_bulk(["ZTF26aaa", "ZTF26bbb"], radius=2.0, user_id=7) == 2
    assert len(calls) == 1
    assert calls[0] == {
        "obj_ids": ["ZTF26aaa", "ZTF26bbb"],
        "radius": 2.0,
        "user_id": 7,
    }


def test_a_refused_batch_raises_rather_than_reporting_success(monkeypatch):
    monkeypatch.setattr(
        "skyportal.utils.tns.requests.post",
        lambda *args, **kwargs: types.SimpleNamespace(status_code=400, content=b"nope"),
    )
    with pytest.raises(ValueError, match="refused 1 objects"):
        get_tns_bulk(["ZTF26aaa"], user_id=7)


def test_an_empty_batch_never_reaches_the_queue(monkeypatch):
    monkeypatch.setattr(
        "skyportal.utils.tns.requests.post",
        lambda *args, **kwargs: pytest.fail("no request should be sent"),
    )
    with pytest.raises(ValueError, match="obj_ids"):
        get_tns_bulk([], user_id=7)
