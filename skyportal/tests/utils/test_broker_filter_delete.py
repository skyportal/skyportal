"""Unit tests for ``delete_filter_on_broker``: dropping a filter here must drop
it on the broker too, without ever blocking the deletion.
"""

from types import SimpleNamespace

from skyportal.handlers.api.filter import delete_filter_on_broker


def _broker(calls, implements=True, raises=False):
    def delete_filter(broker, session, **kwargs):
        if raises:
            raise RuntimeError("boom is down")
        calls.append(kwargs)

    return SimpleNamespace(
        name="BOOM",
        broker_class=SimpleNamespace(
            implements=lambda: {"delete_filter": implements},
            delete_filter=delete_filter,
        ),
    )


def _filter(altdata):
    return SimpleNamespace(id=1, altdata=altdata)


def test_deletes_the_broker_side_filter():
    calls = []
    delete_filter_on_broker(
        _broker(calls), _filter({"boom": {"filter_id": "abc"}}), None
    )
    assert calls == [{"boom_filter_id": "abc"}]


def test_no_broker_is_a_no_op():
    delete_filter_on_broker(None, _filter({"boom": {"filter_id": "abc"}}), None)


def test_filter_without_a_broker_side_id_is_a_no_op():
    calls = []
    delete_filter_on_broker(_broker(calls), _filter(None), None)
    delete_filter_on_broker(_broker(calls), _filter({}), None)
    delete_filter_on_broker(_broker(calls), _filter({"boom": {}}), None)
    assert calls == []


def test_provider_without_delete_support_is_a_no_op():
    calls = []
    delete_filter_on_broker(
        _broker(calls, implements=False), _filter({"boom": {"filter_id": "abc"}}), None
    )
    assert calls == []


def test_an_unreachable_broker_does_not_block_the_deletion():
    delete_filter_on_broker(
        _broker([], raises=True), _filter({"boom": {"filter_id": "abc"}}), None
    )
