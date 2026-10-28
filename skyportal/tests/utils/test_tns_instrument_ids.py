"""Unit tests for resolving an instrument to the id TNS reports it under."""

import types

from skyportal.utils.tns import (
    TNS_OTHER_INSTRUMENT_ID,
    tns_instrument_id,
    tns_instrument_id_for_name,
)


def _instrument(name, tns_id=None):
    return types.SimpleNamespace(name=name, tns_id=tns_id)


def test_the_mapping_names_the_palomar_spectrographs():
    assert tns_instrument_id(_instrument("NGPS")) == 285
    assert tns_instrument_id(_instrument("DBSP")) == 1
    assert tns_instrument_id(_instrument("TSPEC")) == 109


def test_an_instruments_own_id_wins_over_the_mapping():
    """An instance can name an instrument TNS knows but the mapping does not."""
    assert tns_instrument_id(_instrument("SEDM", tns_id=777)) == 777
    assert tns_instrument_id(_instrument("NoSuch", tns_id=42)) == 42


def test_an_unknown_instrument_falls_back_to_other():
    assert tns_instrument_id(_instrument("NoSuch")) == TNS_OTHER_INSTRUMENT_ID
    assert tns_instrument_id(_instrument(None)) == TNS_OTHER_INSTRUMENT_ID


def test_a_mapping_entry_with_several_ids_reports_the_first():
    assert tns_instrument_id(_instrument("ATLAS")) == 159
    assert tns_instrument_id(_instrument("PS1")) == 155


def test_the_name_lookup_ignores_case_and_missing_names():
    assert tns_instrument_id_for_name("sedm") == 149
    assert tns_instrument_id_for_name("SEDM") == 149
    assert tns_instrument_id_for_name(None) == TNS_OTHER_INSTRUMENT_ID
    assert tns_instrument_id_for_name("") == TNS_OTHER_INSTRUMENT_ID
