"""Pure-logic tests for the openai_analysis_service triage helpers: the classifier
extraction, the prompt seeding, the tolerant JSON parse and the comment render.
The live LLM + API round trip is exercised in deployment, not here."""

import importlib.util
import pathlib

import pytest

_APP = pathlib.Path(__file__).parents[2] / "services/openai_analysis_service/app.py"
_spec = importlib.util.spec_from_file_location("openai_service_app", _APP)
app = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(app)


def _results():
    return {
        "classification": {
            "probabilities": {"SN_Ia": 0.7, "SN_CC": 0.3},
            "predicted": "SN_Ia",
            "prediction_set": ["SN_Ia"],
            "alpha": 0.1,
            "credibility": 0.6,
            "anomaly": {"energy_percentile": 97.3},
        },
        "triage": {"verdict": "needs_spectrum", "priority": 2},
        "context": {"host_sep": 0.3},
    }


def test_extract_flare_requires_probabilities():
    assert app.extract_flare(_results())["classification"]["predicted"] == "SN_Ia"
    assert app.extract_flare({"classification": {}}) is None
    assert app.extract_flare({"foo": 1}) is None
    assert app.extract_flare("not a dict") is None


def test_build_triage_prompt_seeds_numbers_and_marks_rule_authoritative():
    prompt = app.build_triage_prompt("PROMPT", "ZTFtest", app.extract_flare(_results()))
    assert "SN_Ia 0.700" in prompt  # sorted, formatted probabilities
    assert "90% set" in prompt
    assert "authoritative" in prompt  # the rule verdict is not to be overwritten


def test_parse_triage_response_tolerates_fences_and_junk():
    keys = {"summary", "evidence", "suggested_action", "caveats"}
    parsed = app.parse_triage_response(
        '```json\n{"summary":"s","evidence":"e","suggested_action":"a","caveats":"c"}\n```'
    )
    assert set(parsed) == keys
    assert app.parse_triage_response("not json") is None
    # partial objects keep only the present keys
    assert app.parse_triage_response('{"summary": "s"}') == {"summary": "s"}


def test_format_triage_comment_leads_with_rule_verdict():
    comment = app.format_triage_comment(
        {"summary": "s", "suggested_action": "a"}, app.extract_flare(_results())
    )
    assert comment.splitlines()[0] == "**FLARE triage**"
    assert "`needs_spectrum` (priority 2)" in comment
    assert "Summary: s" in comment and "Suggested action: a" in comment


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
