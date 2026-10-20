"""Which tools the assistant is allowed to see.

A tool that writes is offered only on the page whose subject it writes to. The
assistant reads circulars, comments and annotations, all written by other
people, so a model talked into a write by that text must have nothing to call.
"""

from skyportal.handlers.mcp import TOOLS
from skyportal.utils.assistant import (
    FILTER_WRITE_TOOLS,
    offered_tools,
    targets_page_filter,
)

READ = {"name": "get_alert_schema", "annotations": {"readOnlyHint": True}}
WRITE = {"name": "post_broker_filter_version", "annotations": {"readOnlyHint": False}}
OTHER_WRITE = {"name": "post_source", "annotations": {"readOnlyHint": False}}


def names(tools, context_type=None):
    return {tool["name"] for tool in offered_tools(tools, context_type)}


def test_reading_tools_are_always_offered():
    assert names([READ]) == {"get_alert_schema"}
    assert names([READ], "filter") == {"get_alert_schema"}


def test_no_writing_tool_is_offered_off_a_filter_page():
    assert names([READ, WRITE]) == {"get_alert_schema"}
    assert names([READ, WRITE], "source") == {"get_alert_schema"}
    assert names([READ, WRITE], "gcn_event") == {"get_alert_schema"}


def test_filter_writing_tools_are_offered_on_a_filter_page():
    assert names([READ, WRITE], "filter") == {
        "get_alert_schema",
        "post_broker_filter_version",
    }


def test_a_filter_page_does_not_unlock_unrelated_writes():
    # Saving a source is a write the filter page has no business doing.
    assert names([OTHER_WRITE], "filter") == set()


def test_a_tool_with_no_annotations_is_treated_as_writing():
    assert names([{"name": "mystery"}]) == set()


def test_every_allowed_tool_exists_and_writes():
    # A name that drifts would silently stop being offered; one that is
    # read-only does not belong on the list at all.
    for name in FILTER_WRITE_TOOLS:
        assert name in TOOLS, name
        assert TOOLS[name]["annotations"]["readOnlyHint"] is False, name


def test_a_filter_page_cannot_create_filters_or_groups():
    for name in ("post_filter", "post_group"):
        tool = {"name": name, "annotations": {"readOnlyHint": False}}
        assert names([tool], "filter") == set()


def test_filter_writes_must_name_the_page_filter():
    assert targets_page_filter({"broker_id": 1, "filter_id": 1433}, "1/1433")
    assert not targets_page_filter({"broker_id": 1, "filter_id": 1434}, "1/1433")
    assert not targets_page_filter({"broker_id": 2, "filter_id": 1433}, "1/1433")
    assert not targets_page_filter({"filter_id": 1433}, "1/1433")
    assert not targets_page_filter({"broker_id": 1, "filter_id": 1433}, None)


def test_every_gated_tool_is_a_tool_that_exists():
    # A name that drifts is a tool silently never offered, which reads from the
    # chat panel as the assistant refusing to do something it can do.
    assert FILTER_WRITE_TOOLS <= set(TOOLS)
    assert all(
        not TOOLS[name]["annotations"]["readOnlyHint"] for name in FILTER_WRITE_TOOLS
    )
