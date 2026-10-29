"""The observing script the Wendelstein API builds for a request."""

import re
import types

import pytest

from skyportal.app_server import skyportal_handlers
from skyportal.facility_apis.wendelstein import (
    WENDELSTEINAPI,
    filters_for_arm,
    generate_script,
    validate_request,
)
from skyportal.handlers.api import FollowupRequestScriptHandler

FILTERS = [
    "2massh",
    "2massj",
    "sdssg",
    "sdssi",
    "sdssr",
    "sdssu",
    "sdssz",
    "2massks",
]


def _instrument(name="Wendelstein 3KK", filters=None):
    return types.SimpleNamespace(
        name=name,
        to_dict=lambda: {"filters": FILTERS if filters is None else filters},
    )


def _request(payload, ra=68.051625, dec=-5.377664):
    obj = types.SimpleNamespace(id="TDE2025aarm", ra=ra, dec=dec)
    return types.SimpleNamespace(id=1, obj_id="TDE2025aarm", obj=obj, payload=payload)


def _payload(**overrides):
    payload = {
        "dither_size": 275,
        "autofocus": True,
        "program_id": "3823",
        "priority": 1,
        "start_date": "2025-10-30T00:00:00",
        "end_date": "2025-10-31T00:00:00",
        "sequences": [
            {
                "blue_filter": "sdssu",
                "blue_exposure_time": 150,
                "red_filter": "sdssi",
                "red_exposure_time": 150,
                "nir_filter": "2massks",
                "nir_exposure_time": 60,
                "readout_mode": "r4",
                "exposure_count": 7,
            }
        ],
    }
    payload.update(overrides)
    return payload


def _commands(script):
    return [line for line in script.splitlines() if line and not line.startswith("#")]


def test_script_reproduces_the_telescope_example():
    # The three-sequence script an observer ran on TDE2025aarm, which is the
    # only worked example of the command language we have.
    payload = _payload(
        object_name="TDE2025aarm",
        sequences=[
            {
                "blue_filter": "sdssu",
                "blue_exposure_time": 150,
                "red_filter": "sdssi",
                "red_exposure_time": 150,
                "nir_filter": "2massks",
                "nir_exposure_time": 60,
                "readout_mode": "r4",
                "exposure_count": 7,
            },
            {
                "blue_filter": "sdssg",
                "blue_exposure_time": 180,
                "red_filter": "sdssz",
                "red_exposure_time": 180,
                "nir_filter": "2massh",
                "nir_exposure_time": 75,
                "readout_mode": "r4",
                "exposure_count": 5,
            },
            {
                "blue_filter": "sdssr",
                "blue_exposure_time": 180,
                "red_filter": "sdssz",
                "red_exposure_time": 180,
                "nir_filter": "2massj",
                "nir_exposure_time": 180,
                "readout_mode": "r4",
                "exposure_count": 5,
            },
        ],
    )
    assert _commands(generate_script(_request(payload), _instrument())) == [
        "2mdithersize 275",
        "2mf bu ri nK",
        "2mradec 04:32:12.39 -05:22:39.59",
        "2mh calcz",
        "2mautofocus",
        "2mobj TDE2025aarm 3823",
        "2mt n60 r150 b150",
        "2mh best",
        "2mo r4 7",
        "2mf bg rz nH",
        "2mt n75 r180 b180",
        "2mh best",
        "2mo r4 5",
        "2mf br rz nJ",
        "2mt 180",
        "2mh best",
        "2mo r4 5",
    ]


def test_exposure_times_collapse_only_when_every_arm_agrees():
    script = generate_script(
        _request(
            _payload(
                sequences=[
                    {
                        "blue_filter": "sdssr",
                        "blue_exposure_time": 180,
                        "red_filter": "sdssz",
                        "red_exposure_time": 180,
                        "nir_filter": "2massj",
                        "nir_exposure_time": 180,
                    }
                ]
            )
        ),
        _instrument(),
    )
    assert "2mt 180" in _commands(script)


def test_one_arm_alone_still_names_its_time():
    script = generate_script(
        _request(
            _payload(
                sequences=[{"red_filter": "sdssz", "red_exposure_time": 90}],
            )
        ),
        _instrument(),
    )
    commands = _commands(script)
    assert "2mf rz" in commands
    # A single arm agrees with itself, so the time collapses to the bare form.
    assert "2mt 90" in commands


def test_object_line_omits_an_absent_program_id():
    script = generate_script(_request(_payload(program_id=None)), _instrument())
    assert "2mobj TDE2025aarm" in _commands(script)
    assert not any(line.startswith("2mobj TDE2025aarm ") for line in _commands(script))


def test_object_name_defaults_to_the_obj_id():
    script = generate_script(_request(_payload()), _instrument())
    assert "2mobj TDE2025aarm 3823" in _commands(script)


def test_autofocus_can_be_turned_off():
    script = generate_script(_request(_payload(autofocus=False)), _instrument())
    assert "2mautofocus" not in _commands(script)


def test_the_note_to_the_observer_rides_as_comments():
    script = generate_script(
        _request(_payload(comment="please execute anytime\n40 minutes")), _instrument()
    )
    assert "# please execute anytime" in script
    assert "# 40 minutes" in script


def test_coordinates_are_sexagesimal_to_two_decimals():
    script = generate_script(_request(_payload()), _instrument())
    radec = next(line for line in _commands(script) if line.startswith("2mradec"))
    assert re.fullmatch(
        r"2mradec \d{2}:\d{2}:\d{2}\.\d{2} [+-]\d{2}:\d{2}:\d{2}\.\d{2}", radec
    )


def test_filters_are_grouped_by_arm():
    instrument = _instrument()
    assert filters_for_arm(instrument, "blue") == ["sdssg", "sdssr", "sdssu"]
    assert filters_for_arm(instrument, "red") == ["sdssi", "sdssz"]
    assert filters_for_arm(instrument, "nir") == ["2massh", "2massj", "2massks"]


def test_a_filter_in_the_wrong_arm_is_refused():
    with pytest.raises(ValueError, match="not in the blue arm"):
        validate_request(
            _request(
                _payload(sequences=[{"blue_filter": "sdssz", "blue_exposure_time": 60}])
            ),
            _instrument(),
        )


def test_a_filter_the_instrument_lacks_is_refused():
    with pytest.raises(ValueError, match="is not on"):
        validate_request(
            _request(
                _payload(sequences=[{"blue_filter": "sdssu", "blue_exposure_time": 60}])
            ),
            _instrument(filters=["sdssg", "sdssr"]),
        )


def test_a_filter_without_an_exposure_time_is_refused():
    with pytest.raises(ValueError, match="without an exposure time"):
        validate_request(
            _request(_payload(sequences=[{"blue_filter": "sdssu"}])), _instrument()
        )


def test_a_sequence_with_no_filter_is_refused():
    with pytest.raises(ValueError, match="at least one filter"):
        validate_request(
            _request(_payload(sequences=[{"exposure_count": 3}])), _instrument()
        )


def test_an_empty_sequence_list_is_refused():
    with pytest.raises(ValueError, match="At least one sequence"):
        validate_request(_request(_payload(sequences=[])), _instrument())


def test_a_missing_parameter_is_named():
    payload = _payload()
    del payload["dither_size"]
    with pytest.raises(ValueError, match="dither_size required"):
        validate_request(_request(payload), _instrument())


def test_another_instrument_at_the_telescope_is_refused_for_now():
    # SEDMv2 moves to Wendelstein, and its command set is not implemented here.
    with pytest.raises(ValueError, match="not SEDMv2"):
        validate_request(_request(_payload()), _instrument(name="SEDMv2"))


def test_the_form_offers_each_arm_the_filters_it_has():
    schema = WENDELSTEINAPI.custom_json_schema(_instrument(), None)
    sequence = schema["properties"]["sequences"]["items"]["properties"]
    assert sequence["blue_filter"]["enum"] == [None, "sdssg", "sdssr", "sdssu"]
    assert sequence["red_filter"]["enum"] == [None, "sdssi", "sdssz"]
    assert sequence["nir_filter"]["enum"] == [None, "2massh", "2massj", "2massks"]


def test_the_form_drops_an_arm_the_instrument_does_not_have():
    schema = WENDELSTEINAPI.custom_json_schema(
        _instrument(filters=["sdssg", "sdssr"]), None
    )
    sequence = schema["properties"]["sequences"]["items"]["properties"]
    assert "blue_filter" in sequence
    assert "red_filter" not in sequence
    assert "nir_filter" not in sequence


def test_the_script_route_reaches_its_handler():
    for pattern, handler, *_ in skyportal_handlers:
        if re.fullmatch(pattern, "/api/followup_request/12/script"):
            assert handler is FollowupRequestScriptHandler
            break
    else:
        raise AssertionError("no route serves a follow-up request's script")
