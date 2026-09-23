"""What a filter pipeline may reference, beyond the packet that arrived.

BOOM enriches the alert document after ingestion, and its Avro schema
describes only the packet, so these fields exist and are undiscoverable --
and a pipeline referencing a path nobody published matches nothing, which
looks exactly like a night with no candidates.
"""

from skyportal.broker_apis._enrichment import (
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


def test_every_group_is_a_usable_avro_field():
    # Whatever the file lists -- a fit today, a classifier tomorrow -- has to
    # be something the builder can render and a pipeline can reference.
    fields = supplemental_fields()
    assert fields, "the supplement is empty; the builder would show nothing"
    for field in fields:
        assert field.get("name"), f"unnamed entry: {field}"
        assert field.get("type"), f"{field['name']} has no type"


def test_the_villar_fit_is_offered_per_parameter_and_band():
    # Seven parameters in each of two bands, plus reduced_chi2 and
    # peak_flux. Counted against production by the BOOM side.
    villar = next(f for f in supplemental_fields() if f["name"] == "villar_fit")
    record = next(t for t in villar["type"] if isinstance(t, dict))
    leaves = {f["name"] for f in record["fields"]}
    assert len(leaves) == 16
    assert {"reduced_chi2", "peak_flux"} <= leaves
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


def test_sso_history_entries_carry_their_own_geometry(monkeypatch=None):
    # An array of entries, not a single match: a window statistic needs one
    # value per point, and the geometry leaves are null on entries enriched
    # before SSO geometry shipped.
    from skyportal.handlers.mcp import _flatten_avro

    schema = supplement_schema(
        {
            "type": "record",
            "name": "alert",
            "fields": [{"name": "candidate", "type": "string"}],
        }
    )
    paths = dict(_flatten_avro(schema))
    assert paths["sso_history[].designation"] == "string"
    assert paths["sso_history[].phase_angle"] == "double?"
    assert paths["sso_history[].jd"] == "double"


def test_the_provider_serves_the_supplemented_schema(monkeypatch):
    # The integration point: what a caller of filter_modules receives, and so
    # what both the builder and get_alert_schema read.
    from skyportal.broker_apis import boom

    monkeypatch.setattr(
        boom, "_request", lambda *a, **k: {"fields": [{"name": "candidate"}]}
    )
    data = boom.BOOMBROKER.filter_modules(
        broker=None, session=None, elements="schema", survey="ZTF"
    )
    names = [f["name"] for f in data["schema"]["fields"]]
    assert "candidate" in names
    assert "villar_fit" in names
    assert "cross_matches" in names


def test_the_fields_survive_flattening_into_dotted_paths():
    # get_alert_schema flattens the schema before the model sees it; a record
    # the flattener cannot walk would be advertised as nothing.
    from skyportal.handlers.mcp import _flatten_avro

    schema = supplement_schema(
        {
            "type": "record",
            "name": "alert",
            "fields": [{"name": "candidate", "type": "string"}],
        }
    )
    paths = dict(_flatten_avro(schema))
    assert paths.get("villar_fit.reduced_chi2") == "double?"
    assert "villar_fit.tau_rise_ZTF_r" in paths
    assert any(p.startswith("cross_matches[]") for p in paths)
