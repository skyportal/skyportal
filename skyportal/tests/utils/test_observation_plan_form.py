"""The observation-plan form branches on which scheduler was chosen.

gwemopt and M4OPT take different settings, and rjsf renders a `oneOf`
dependency only when exactly one branch matches -- so both the branching and
its exclusivity are pinned here.
"""

from unittest import mock

import jsonschema
import pytest

from skyportal import models
from skyportal.facility_apis import observation_plan as facility
from skyportal.utils import m4opt_plan

GWEMOPT_ONLY = ("filter_strategy", "schedule_type", "schedule_strategy")


def build_schema():
    """The real form schema, with the two queries it makes stubbed out."""
    instrument = mock.MagicMock()
    instrument.name = "ZTF"
    instrument.id = 1

    session = mock.MagicMock()
    # galaxy catalog names
    session.query.return_value.distinct.return_value.all.return_value = []
    # instruments with reference filters
    session.query.return_value.filter.return_value.count.return_value = 0
    with mock.patch.object(models, "DBSession", return_value=session):
        return facility.MMAAPI.custom_json_schema(instrument, None)


@pytest.fixture()
def without_m4opt(monkeypatch):
    monkeypatch.setattr(m4opt_plan, "_config", lambda: {"enabled": False})
    return build_schema()


@pytest.fixture()
def with_m4opt(monkeypatch):
    monkeypatch.setattr(
        m4opt_plan,
        "_config",
        lambda: {"enabled": True, "missions": {"ZTF": "ztf"}},
    )
    return build_schema()


def test_form_is_untouched_where_m4opt_is_not_configured(without_m4opt):
    """Every existing deployment must see exactly the form it saw before."""
    assert "scheduler" not in without_m4opt["properties"]
    assert all(key in without_m4opt["properties"] for key in GWEMOPT_ONLY)
    assert all(key in without_m4opt["required"] for key in GWEMOPT_ONLY)
    assert "scheduler" not in without_m4opt["dependencies"]


def test_gwemopt_settings_move_into_their_own_branch(with_m4opt):
    assert "scheduler" in with_m4opt["properties"]
    # Left at the top level they would show for M4OPT too, and be ignored.
    assert not any(key in with_m4opt["properties"] for key in GWEMOPT_ONLY)
    # And left in `required` they would make an M4OPT request invalid.
    assert not any(key in with_m4opt["required"] for key in GWEMOPT_ONLY)


def test_each_scheduler_gets_its_own_settings(with_m4opt):
    branches = {
        branch["properties"]["scheduler"]["enum"][0]: branch
        for branch in with_m4opt["dependencies"]["scheduler"]["oneOf"]
    }
    assert set(branches) == {"gwemopt", "m4opt"}
    assert all(key in branches["gwemopt"]["properties"] for key in GWEMOPT_ONLY)
    assert {"visits", "max_fields"} <= set(branches["m4opt"]["properties"])
    assert not any(key in branches["m4opt"]["properties"] for key in GWEMOPT_ONLY)


@pytest.mark.parametrize("choice", ["gwemopt", "m4opt"])
def test_exactly_one_branch_matches_each_choice(with_m4opt, choice):
    """Two matching branches make `oneOf` fail and the form render nothing."""
    matching = [
        branch
        for branch in with_m4opt["dependencies"]["scheduler"]["oneOf"]
        if choice in branch["properties"]["scheduler"]["enum"]
    ]
    assert len(matching) == 1


def test_the_schema_is_valid(with_m4opt, without_m4opt):
    jsonschema.Draft7Validator.check_schema(with_m4opt)
    jsonschema.Draft7Validator.check_schema(without_m4opt)


@pytest.mark.parametrize(
    ("choice", "extra"),
    [
        (
            "gwemopt",
            {
                "schedule_type": "greedy",
                "schedule_strategy": "tiling",
                "filter_strategy": "block",
            },
        ),
        ("m4opt", {"visits": 2, "max_fields": 50}),
    ],
)
def test_a_request_of_each_shape_validates(with_m4opt, choice, extra):
    payload = {
        key: value["default"]
        for key, value in with_m4opt["properties"].items()
        if "default" in value
    }
    # The mocked instrument gives nonsense date defaults; the dates are not
    # what this is testing.
    payload["start_date"] = "2026-09-05 00:00:00"
    payload["end_date"] = "2026-09-06 00:00:00"
    jsonschema.validate({**payload, "scheduler": choice, **extra}, with_m4opt)


def test_a_request_carrying_the_other_scheduler_settings_is_rejected(with_m4opt):
    """m4opt has no schedule_type, so offering one is a mistake worth catching."""
    branch = next(
        b
        for b in with_m4opt["dependencies"]["scheduler"]["oneOf"]
        if "m4opt" in b["properties"]["scheduler"]["enum"]
    )
    assert "schedule_type" not in branch["properties"]
