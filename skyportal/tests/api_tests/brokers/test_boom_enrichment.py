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
    assert "sso_history" in _names(schema)
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


def test_a_field_the_broker_declares_is_left_alone():
    # The point of the stopgap: once BOOM advertises these, it contributes
    # nothing and can be deleted without a flag day.
    declared = {"fields": [{"name": "sso_history", "type": "broker's own"}]}
    schema = supplement_schema(declared)
    history = [f for f in schema["fields"] if f["name"] == "sso_history"]
    assert len(history) == 1
    assert history[0]["type"] == "broker's own"


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
    assert "sso_history" in names
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
    assert paths.get("sso_history[].jd") == "double"
    assert any(p.startswith("cross_matches[]") for p in paths)


def test_nan_possible_rides_along_on_the_field():
    # Avro has no way to say "present but NaN", and it is the property that
    # separates "this alert had no fit" from "this alert failed the cut".
    # Avro permits unknown attributes, so it travels as one rather than being
    # lost in prose the builder never renders.
    from skyportal.handlers.mcp import NAN_NOTE, _flatten_avro

    notes = {}
    schema = {
        "type": "record",
        "name": "alert",
        "fields": [{"name": "fit", "type": ["null", "double"], "nan_possible": True}],
    }
    assert dict(_flatten_avro(schema, notes=notes))["fit"] == "double?"
    assert NAN_NOTE in notes["fit"]


def test_a_note_says_which_way_a_rise_rate_points():
    # The sign is the whole content of the field: a rate in magnitudes per day
    # is negative while the source brightens, so "rising" reads backwards and
    # the obvious cut selects the sources that are fading.
    from skyportal.broker_apis._enrichment import annotate_schema
    from skyportal.handlers.mcp import _flatten_avro, _note_owner

    schema = {
        "type": "record",
        "name": "alert",
        "fields": [
            {
                "name": "properties",
                "type": {
                    "type": "record",
                    "name": "Properties",
                    "fields": [
                        {
                            "name": "photstats",
                            "type": {
                                "type": "record",
                                "name": "PhotStats",
                                "fields": [
                                    {
                                        "name": "r",
                                        "type": {
                                            "type": "record",
                                            "name": "Band",
                                            "fields": [
                                                {
                                                    "name": "rising",
                                                    "type": {
                                                        "type": "record",
                                                        "name": "Rise",
                                                        "fields": [
                                                            {
                                                                "name": "rate",
                                                                "type": "double",
                                                            }
                                                        ],
                                                    },
                                                }
                                            ],
                                        },
                                    }
                                ],
                            },
                        }
                    ],
                },
            }
        ],
    }
    notes = {}
    _flatten_avro(annotate_schema(schema), notes=notes)
    owner = _note_owner("properties.photstats.r.rising.rate", notes)
    assert "NEGATIVE" in notes[owner]


def test_a_note_says_acai_b_scores_an_artefact():
    # Read as a supernova class it selects junk: 82% of the alerts scoring
    # over 0.5 on a night of ZTF have drb < 0.3.
    from skyportal.broker_apis._enrichment import annotate_schema

    field = {"name": "acai_b", "type": "float"}
    schema = {
        "type": "record",
        "name": "alert",
        "fields": [
            {
                "name": "classifications",
                "type": {
                    "type": "record",
                    "name": "Classifications",
                    "fields": [field],
                },
            }
        ],
    }
    annotate_schema(schema)
    assert "BOGUS" in field["doc"]


def test_the_broker_keeps_its_own_wording():
    # A note is a stopgap for what BOOM has not documented, so it stands aside
    # the moment BOOM does, the way supplement_schema does for a field.
    from skyportal.broker_apis._enrichment import annotate_schema

    field = {"name": "acai_b", "type": "float", "doc": "BOOM says this."}
    annotate_schema(
        {
            "type": "record",
            "name": "alert",
            "fields": [
                {
                    "name": "classifications",
                    "type": {
                        "type": "record",
                        "name": "Classifications",
                        "fields": [field],
                    },
                }
            ],
        }
    )
    assert field["doc"] == "BOOM says this."


def test_a_note_reaches_the_model_through_the_flattener():
    # The information existed in the schema all along and was dropped one step
    # before the only reader who needed it.
    from skyportal.handlers.mcp import _flatten_avro

    notes = {}
    schema = supplement_schema(
        {"type": "record", "name": "alert", "fields": [{"name": "c", "type": "string"}]}
    )
    _flatten_avro(schema, notes=notes)
    assert "solar-system object" in notes["sso_history"]


def test_a_rise_and_a_decline_do_not_share_a_sign():
    # They are two fields of one Avro record, so a note written onto the `rate`
    # they have in common tells the reader the decline brightens.
    from skyportal.broker_apis._enrichment import annotate_schema
    from skyportal.handlers.mcp import _flatten_avro, _note_owner

    fit = {
        "type": "record",
        "name": "Fit",
        "fields": [{"name": "rate", "type": "double"}],
    }
    schema = {
        "type": "record",
        "name": "alert",
        "fields": [
            {
                "name": "properties",
                "type": {
                    "type": "record",
                    "name": "Properties",
                    "fields": [
                        {
                            "name": "photstats",
                            "type": {
                                "type": "record",
                                "name": "PhotStats",
                                "fields": [
                                    {
                                        "name": "r",
                                        "type": {
                                            "type": "record",
                                            "name": "Band",
                                            "fields": [
                                                {"name": "rising", "type": fit},
                                                {"name": "fading", "type": fit},
                                            ],
                                        },
                                    }
                                ],
                            },
                        }
                    ],
                },
            }
        ],
    }
    notes = {}
    _flatten_avro(annotate_schema(schema), notes=notes)
    rising = notes[_note_owner("properties.photstats.r.rising.rate", notes)]
    fading = notes[_note_owner("properties.photstats.r.fading.rate", notes)]
    assert "NEGATIVE" in rising and "POSITIVE" not in rising
    assert "POSITIVE" in fading and "NEGATIVE" not in fading
