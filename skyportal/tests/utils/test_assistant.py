"""What the assistant is asked, and how a tool result is cut down to fit."""

import json

from skyportal.utils.assistant import (
    answer_text,
    build_messages,
    condense,
    describe_context,
    describe_user,
    is_enabled,
    system_prompt,
)


def _message(text, system=False):
    return {"text": text, "system": system}


def test_conversation_becomes_alternating_roles():
    messages = build_messages(
        [
            _message("what is this?"),
            _message("An X-ray Flash.", system=True),
            _message("how bright?"),
        ],
        40,
    )
    assert [m["role"] for m in messages] == ["system", "user", "assistant", "user"]
    assert messages[1]["content"] == "what is this?"


def test_long_conversations_keep_the_newest():
    messages = build_messages([_message(f"m{i}") for i in range(10)], 3)
    assert len(messages) == 4
    assert messages[-1]["content"] == "m9"


def test_prompt_names_the_page_the_question_came_from():
    assert "GCN event 7" in system_prompt("gcn_event", 7)
    assert "source ZTF21abc" in system_prompt("source", "ZTF21abc")
    assert describe_context("comet", 3) == "comet 3"


def test_prompt_names_the_person_asking():
    prompt = system_prompt(
        user={"username": "ann", "first_name": "Ann", "last_name": "Smith"}
    )
    assert "Ann Smith (@ann)" in prompt
    assert describe_user({"username": "ann"}) == "ann"
    assert describe_user({"username": "ann", "first_name": "Ann"}) == "Ann (@ann)"


def test_prompt_says_nothing_when_the_person_is_unknown():
    assert "The person asking is" not in system_prompt()
    assert describe_user(None) is None
    assert describe_user({"username": None, "first_name": None}) is None


def test_prompt_says_nothing_when_there_is_no_page():
    assert "looking at" not in system_prompt()
    assert describe_context("source", None) is None
    assert describe_context(None, "ZTF21abc") is None


def test_disabled_until_a_base_url_is_configured():
    assert not is_enabled({"app.assistant": {}})
    assert not is_enabled({"app.assistant": None})
    assert is_enabled({"app.assistant": {"base_url": "http://host/v1"}})


def test_short_results_are_left_alone():
    assert condense('{"a": 1}') == '{"a": 1}'


def test_the_bulky_field_is_dropped_and_named():
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
    assert all(set(item) == {"id", "text"} for item in result["items"])
    assert "of 50 not shown" in result["note"]


def test_non_json_is_truncated_with_its_length():
    result = condense("z" * 9000, budget=100)
    assert result.startswith("z" * 100)
    assert "9000 characters in total" in result


def test_the_answer_is_the_content_a_model_returns():
    assert answer_text({"content": "r = 22.73 at T+12.6 h"}) == "r = 22.73 at T+12.6 h"
    assert answer_text({"content": "  spaced  "}) == "spaced"


def test_a_reasoning_model_answers_from_reasoning_content():
    """Some models leave `content` empty and put their text elsewhere."""
    assert (
        answer_text({"content": "", "reasoning_content": "the burst faded"})
        == "the burst faded"
    )
    assert answer_text({"reasoning_content": "the burst faded"}) == "the burst faded"


def test_content_wins_when_a_model_returns_both():
    assert answer_text({"content": "final", "reasoning_content": "thinking"}) == "final"


def test_an_empty_reply_is_empty():
    assert answer_text({}) == ""
    assert answer_text({"content": None, "reasoning_content": None}) == ""


def test_the_last_turn_sent_is_a_question():
    """An OpenAI-compatible server refuses a list ending in assistant turns, so a
    previous failure's apology must not be the last thing the model sees."""
    conversation = [
        {"text": "what is this source?", "system": False},
        {"text": "Something went wrong while looking that up.", "system": True},
        {"text": "Something went wrong while looking that up.", "system": True},
    ]
    messages = build_messages(conversation, 40)
    assert messages[-1]["role"] == "user"
    assert messages[-1]["content"] == "what is this source?"


def test_an_answered_exchange_still_ends_on_the_new_question():
    conversation = [
        {"text": "first question", "system": False},
        {"text": "first answer", "system": True},
        {"text": "second question", "system": False},
    ]
    messages = build_messages(conversation, 40)
    assert [m["role"] for m in messages] == ["system", "user", "assistant", "user"]
