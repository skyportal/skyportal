"""What the assistant records about the tools it ran, and the filter it offers.

The trace is shown under the answer, and the proposal is what the filter page
offers for saving, so both are read by a person deciding whether to trust it.
"""

from skyportal.utils.assistant import proposal, record_call, trim

PIPELINE = [{"$match": {"candidate.drb": {"$gt": 0.9}}}]


def previewed(pipeline=PIPELINE, summary='{"count": 42}', ok=True):
    return record_call(
        "run_broker_filter",
        {"broker_id": 1, "pipeline": pipeline, "start_jd": 1.0, "end_jd": 8.0},
        summary,
        ok,
    )


def test_a_call_records_what_ran_and_how_it_went():
    call = record_call("get_alert_schema", {"survey": "ZTF"}, '{"matched": 3}', True)
    assert call["name"] == "get_alert_schema"
    assert call["arguments"] == {"survey": "ZTF"}
    assert call["ok"] is True
    assert "matched" in call["summary"]


def test_a_failed_call_is_kept():
    # A tool that errored is the most useful entry in the trace, not the one to
    # drop: it explains an answer that stops short.
    call = record_call("post_filter", {}, "tool post_filter failed: 400", False)
    assert call["ok"] is False
    assert "failed" in call["summary"]


def test_a_long_argument_is_trimmed():
    trimmed = trim({"name": "x" * 900}, 400)
    assert len(trimmed["name"]) < 900


def test_the_pipeline_argument_is_kept_whole():
    # It is what the user is being asked to approve, so a truncated one would
    # be worse than none.
    big = [{"$match": {f"candidate.f{i}": i}} for i in range(200)]
    assert trim({"pipeline": big}, 400)["pipeline"] == big


def test_a_previewed_pipeline_is_offered():
    built = proposal([previewed()])
    assert built["pipeline"] == PIPELINE
    assert built["preview"]["start_jd"] == 1.0


def test_a_pipeline_that_was_never_previewed_is_not_offered():
    # The preview is the evidence that it matches anything; without one the
    # offer would invite saving a filter that passes nothing.
    assert (
        proposal([record_call("get_alert_schema", {"survey": "ZTF"}, "{}", True)])
        is None
    )


def test_a_failed_preview_is_not_offered():
    assert proposal([previewed(ok=False)]) is None


def test_the_last_preview_wins():
    first = [{"$match": {"candidate.drb": {"$gt": 0.5}}}]
    built = proposal([previewed(pipeline=first), previewed()])
    assert built["pipeline"] == PIPELINE


def test_a_saved_version_is_offered_with_its_filter():
    trace = [
        previewed(),
        record_call(
            "post_broker_filter_version",
            {"broker_id": 1, "filter_id": 7, "altdata": PIPELINE},
            '{"fid": "abc"}',
            True,
        ),
    ]
    built = proposal(trace)
    assert built["target"] == {"broker_id": 1, "filter_id": 7}


def test_no_tools_means_nothing_to_offer():
    assert proposal([]) is None
