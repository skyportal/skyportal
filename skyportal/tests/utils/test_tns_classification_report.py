import datetime
import types

import pytest

from skyportal.utils.tns import tns_classification_id, tns_spectrum_type_id
from skyportal.utils.tns_submission import (
    build_tns_classification_report,
    spectrum_ascii,
)

SHARING_SERVICE = types.SimpleNamespace(tns_source_group_id=48)


def _spectrum(**overrides):
    spectrum = types.SimpleNamespace(
        observed_at=datetime.datetime(2026, 3, 4, 5, 6, 7),
        instrument=types.SimpleNamespace(name="SEDM"),
        altdata={"EXPTIME": 2250},
        type="source",
        wavelengths=[4000.0, 4002.5],
        fluxes=[1.5e-16, 1.6e-16],
        errors=None,
        observers=[types.SimpleNamespace(first_name="Ada", last_name="Lovelace")],
        reducers=[types.SimpleNamespace(first_name="Grace", last_name="Hopper")],
    )
    for key, value in overrides.items():
        setattr(spectrum, key, value)
    return spectrum


def _report(**overrides):
    kwargs = {
        "iau_name": "2026abc",
        "classification": "Ia",
        "classifiers": "A. Lovelace",
        "spectrum": _spectrum(),
        "stored_spectrum_name": "tns_2026abc.ascii",
        "sharing_service": SHARING_SERVICE,
    }
    kwargs.update(overrides)
    return build_tns_classification_report(**kwargs)


def test_the_report_is_keyed_by_iau_name_not_an_internal_name():
    entry = _report()["classification_report"]["0"]
    assert entry["name"] == "2026abc"
    assert entry["objtypeid"] == 3
    assert entry["classifier"] == "A. Lovelace"
    assert entry["groupid"] == 48


def test_the_spectrum_entry_names_the_uploaded_file():
    spectra = _report()["classification_report"]["0"]["spectra"]["spectra-group"]
    assert spectra["0"]["ascii_file"] == "tns_2026abc.ascii"
    assert spectra["0"]["fits_file"] == ""


def test_the_spectrum_entry_carries_its_instrument_and_observation():
    entry = _report()["classification_report"]["0"]["spectra"]["spectra-group"]["0"]
    assert entry["instrumentid"] == 149
    assert entry["obsdate"] == "2026-03-04 05:06:07"
    assert entry["exptime"] == 2250
    assert entry["spectypeid"] == 1
    assert entry["observer"] == "Ada Lovelace"
    assert entry["reducer"] == "Grace Hopper"


def test_a_spectrum_naming_no_one_credits_the_instrument_default_observer():
    sedm = types.SimpleNamespace(name="SEDM", default_observer="SEDmRobot")
    report = _report(spectrum=_spectrum(observers=[], reducers=[], instrument=sedm))
    entry = report["classification_report"]["0"]["spectra"]["spectra-group"]["0"]
    assert entry["observer"] == "SEDmRobot"
    # TNS accepts a missing reducer, so only the observer takes the default
    assert entry["reducer"] == ""


def test_a_linked_observer_wins_over_the_instrument_default():
    sedm = types.SimpleNamespace(name="SEDM", default_observer="SEDmRobot")
    report = _report(spectrum=_spectrum(instrument=sedm))
    entry = report["classification_report"]["0"]["spectra"]["spectra-group"]["0"]
    assert entry["observer"] == "Ada Lovelace"


def test_an_unknown_instrument_reports_as_other_rather_than_failing():
    entry = _report(spectrum=_spectrum(instrument=types.SimpleNamespace(name="NoSuch")))
    spectra = entry["classification_report"]["0"]["spectra"]["spectra-group"]
    assert spectra["0"]["instrumentid"] == 0


def test_an_unmapped_classification_is_refused():
    with pytest.raises(ValueError, match="no TNS object type id"):
        _report(classification="Not A Real Class")


def test_optional_fields_default_to_empty_rather_than_null():
    entry = _report()["classification_report"]["0"]
    assert entry["redshift"] == ""
    assert entry["remarks"] == ""
    entry = _report(redshift=0.034, remarks="from SNID")["classification_report"]["0"]
    assert entry["redshift"] == 0.034
    assert entry["remarks"] == "from SNID"


def test_classification_ids_ignore_case_and_surrounding_space():
    assert tns_classification_id("Ia-91bg") == 103
    assert tns_classification_id("  ia-91BG ") == 103
    assert tns_classification_id("Tidal Disruption Event") == 120
    assert tns_classification_id("nonsense") is None
    assert tns_classification_id(None) is None


def test_host_spectra_report_as_the_tns_host_type():
    assert tns_spectrum_type_id("host") == 2
    assert tns_spectrum_type_id("host_center") == 2
    assert tns_spectrum_type_id("source") == 1
    assert tns_spectrum_type_id("something else") == 1


def test_the_ascii_file_has_two_columns_without_errors_and_three_with():
    assert spectrum_ascii(_spectrum()).splitlines() == [
        "4000.0000 1.5e-16",
        "4002.5000 1.6e-16",
    ]
    with_errors = _spectrum(errors=[1e-18, 2e-18])
    assert spectrum_ascii(with_errors).splitlines() == [
        "4000.0000 1.5e-16 1e-18",
        "4002.5000 1.6e-16 2e-18",
    ]
