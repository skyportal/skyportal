"""What a filter pipeline may reference, beyond the packet that arrived.

BOOM enriches the alert document after ingestion, and its Avro schema
describes only the packet, so these fields exist and are undiscoverable --
and a pipeline referencing a path nobody published matches nothing, which
looks exactly like a night with no candidates.
"""

from skyportal.broker_apis._enrichment import (
    VILLAR_FIELDS,
    supplement_schema,
    supplemental_fields,
)


def _names(schema):
    return [f["name"] for f in schema["fields"]]


def test_the_enrichment_fields_are_added():
    schema = supplement_schema({"fields": [{"name": "candidate"}]})
    assert "cross_matches" in _names(schema)
    assert "villar_fit" in _names(schema)
    # and the packet's own fields survive
    assert "candidate" in _names(schema)


def test_every_villar_parameter_and_band_is_offered():
    villar = next(f for f in supplemental_fields() if f["name"] == "villar_fit")
    record = next(t for t in villar["type"] if isinstance(t, dict))
    leaves = {f["name"] for f in record["fields"]}
    assert leaves == set(VILLAR_FIELDS)
    # 7 parameters in each of two bands, plus the fit statistic
    assert len(leaves) == 15
    assert "reduced_chi2" in leaves
    assert {"tau_rise_ZTF_r", "tau_rise_ZTF_g"} <= leaves


def test_a_field_the_broker_declares_is_left_alone():
    # The point of the stopgap: once BOOM advertises these, it contributes
    # nothing and can be deleted without a flag day.
    declared = {"fields": [{"name": "villar_fit", "type": "broker's own"}]}
    schema = supplement_schema(declared)
    villar = [f for f in schema["fields"] if f["name"] == "villar_fit"]
    assert len(villar) == 1
    assert villar[0]["type"] == "broker's own"


def test_applying_it_twice_changes_nothing():
    once = supplement_schema({"fields": [{"name": "candidate"}]})
    assert _names(supplement_schema(once)) == _names(once)


def test_a_schema_it_cannot_read_is_returned_unchanged():
    # Better to hand back what the broker said than to invent a shape.
    assert supplement_schema(None) is None
    assert supplement_schema({"no_fields": True}) == {"no_fields": True}
    assert supplement_schema("a string") == "a string"
