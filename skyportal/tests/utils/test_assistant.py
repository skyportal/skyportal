"""What the assistant is asked, and what stops it answering itself."""

import json

from skyportal.utils.assistant import (
    assistant_channel,
    build_messages,
    condense,
    describe_resource,
    is_addressed_to_assistant,
    is_enabled,
    system_prompt,
)


def _comment(text, system=False, channel="assistant", author="ann"):
    return {"text": text, "system": system, "channel": channel, "author": author}


def test_thread_becomes_alternating_roles():
    messages = build_messages(
        "gcn_event",
        7,
        [_comment("what is this?"), _comment("An X-ray Flash.", system=True)],
        40,
    )
    assert [m["role"] for m in messages] == ["system", "user", "assistant"]
    assert messages[1]["content"] == "ann: what is this?"


def test_long_threads_keep_the_newest():
    comments = [_comment(f"m{i}") for i in range(10)]
    messages = build_messages("sources", "ZTF21abc", comments, 3)
    # system prompt plus the last three
    assert len(messages) == 4
    assert messages[-1]["content"].endswith("m9")


def test_prompt_names_the_resource():
    assert "GCN event 7" in system_prompt("gcn_event", 7)
    assert "source ZTF21abc" in system_prompt("sources", "ZTF21abc")
    # An unknown type still produces a usable phrase.
    assert describe_resource("comet", 3) == "comet 3"


def test_its_own_replies_do_not_retrigger_it():
    assert is_addressed_to_assistant(_comment("hi"), "assistant")
    assert not is_addressed_to_assistant(_comment("hi", system=True), "assistant")


def test_other_channels_are_left_alone():
    assert not is_addressed_to_assistant(_comment("hi", channel=None), "assistant")
    assert not is_addressed_to_assistant(
        _comment("hi", channel="Photometry"), "assistant"
    )


def test_disabled_until_a_base_url_is_configured():
    assert not is_enabled({"app.assistant": {}})
    assert not is_enabled({"app.assistant": None})
    assert is_enabled({"app.assistant": {"base_url": "http://host/v1"}})


def test_channel_name_defaults():
    assert assistant_channel({"app.assistant": {}}) == "assistant"
    assert assistant_channel({"app.assistant": {"channel": "ai"}}) == "ai"


def test_short_results_are_left_alone():
    assert condense('{"a": 1}') == '{"a": 1}'


def test_the_bulky_field_is_dropped_and_named():
    # A GCN event's healpix tiles run to megabytes; the rest of the record is
    # what the assistant needs.
    payload = json.dumps(
        {
            "dateobs": "2023-03-07T15:44:07",
            "tags": ["GRB"],
            "localizations": "x" * 20000,
        }
    )
    result = json.loads(condense(payload, budget=2000))
    assert result["dateobs"] == "2023-03-07T15:44:07"
    assert result["tags"] == ["GRB"]
    assert "localizations" not in result
    assert "localizations" in result["_dropped"]


def test_long_lists_keep_whole_items():
    payload = json.dumps([{"id": i, "text": "y" * 200} for i in range(50)])
    result = json.loads(condense(payload, budget=2000))
    # every item that survived is intact, and the count is stated
    assert all(set(item) == {"id", "text"} for item in result["items"])
    assert "of 50 not shown" in result["note"]


def test_non_json_is_truncated_with_its_length():
    result = condense("z" * 9000, budget=100)
    assert result.startswith("z" * 100)
    assert "9000 characters in total" in result
