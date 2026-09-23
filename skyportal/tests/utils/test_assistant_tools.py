"""Which tools the assistant is allowed to see.

A tool that writes is offered only on the page whose subject it writes to. The
assistant reads circulars, comments and annotations, all written by other
people, so a model talked into a write by that text must have nothing to call.
"""

from skyportal.handlers.mcp import TOOLS
from skyportal.utils.assistant import FILTER_WRITE_TOOLS, offered_tools

READ = {"name": "get_alert_schema", "annotations": {"readOnlyHint": True}}
WRITE = {"name": "post_filter", "annotations": {"readOnlyHint": False}}
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
    assert names([READ, WRITE], "filter") == {"get_alert_schema", "post_filter"}


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
