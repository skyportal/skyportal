"""Fields BOOM writes onto an alert that its Avro schema does not describe.

A filter pipeline runs against the Mongo document, not the packet that
arrived, and BOOM enriches that document after ingestion: catalogue
cross-matches, and a Villar fit per alert. Neither is in the schema
`filter_modules` returns, so a path that exists matches nothing a caller can
discover -- and an empty preview looks the same as an empty sky.

This is a stopgap. BOOM owns the enrichment and should advertise it, at which
point every field here arrives from the broker and this module goes away;
`supplement_schema` already stands aside for any field the broker declares
itself, so that switchover needs no coordination.
"""

__all__ = ["VILLAR_FIELDS", "supplement_schema", "supplemental_fields"]

import functools
import json
import pathlib

SUPPLEMENT_FILE = (
    pathlib.Path(__file__).parents[2] / "data" / "boom_alert_supplement.json"
)

# villar_pso::PARAM_NAMES and ::FILTERS. A fit that is skipped writes NaN to
# every one of these rather than leaving them out, so they are never absent
# and a comparison against a skipped fit is simply false.
VILLAR_PARAMS = ("A", "beta", "gamma", "t_0", "tau_rise", "tau_fall", "extra_sigma")
VILLAR_FILTERS = ("ZTF_r", "ZTF_g")
VILLAR_FIELDS = ["reduced_chi2"] + [
    f"{param}_{filt}" for filt in VILLAR_FILTERS for param in VILLAR_PARAMS
]


def _villar_entry():
    """The Villar fit as one nullable record, matching the cross-match shape."""
    return {
        "name": "villar_fit",
        "doc": "Villar (2019) fit, computed by BOOM; NaN where the fit was skipped.",
        "type": [
            "null",
            {
                "type": "record",
                "name": "VillarFit",
                "fields": [
                    {"name": name, "type": ["null", "double"]} for name in VILLAR_FIELDS
                ],
            },
        ],
    }


@functools.lru_cache(maxsize=1)
def supplemental_fields():
    """Avro field entries for what BOOM adds to an alert after ingestion."""
    fields = []
    if SUPPLEMENT_FILE.exists():
        fields.extend(json.loads(SUPPLEMENT_FILE.read_text()).get("fields") or [])
    fields.append(_villar_entry())
    return fields


def supplement_schema(schema):
    """Add the enrichment fields the broker did not describe.

    A field the broker already declares is left alone, so this contributes
    nothing once BOOM advertises its own.
    """
    if not isinstance(schema, dict) or not isinstance(schema.get("fields"), list):
        return schema
    declared = {f.get("name") for f in schema["fields"] if isinstance(f, dict)}
    added = [f for f in supplemental_fields() if f["name"] not in declared]
    if not added:
        return schema
    return {**schema, "fields": [*schema["fields"], *added]}
