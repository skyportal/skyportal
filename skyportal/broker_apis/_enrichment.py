"""Fields BOOM writes onto an alert that its Avro schema does not describe.

A filter pipeline runs against the Mongo document, not the packet that
arrived, and BOOM enriches that document after ingestion. Those fields are in
no schema, so a path that exists is undiscoverable -- and a pipeline that
references one nobody published matches nothing, which looks exactly like a
night with no candidates.

The groups live in data rather than here: enrichment grows -- other fits,
other classifiers -- and adding one should be an edit to the file, not to
this module. Nothing in this code knows what a Villar fit is.

A stopgap. BOOM owns the enrichment and should advertise it; when it does,
every group here arrives from the broker instead. `supplement_schema` stands
aside for any field the broker declares, so that switchover needs no
coordination and removing this needs no flag day.
"""

__all__ = ["supplement_schema", "supplemental_fields"]

import functools
import json
import pathlib

SUPPLEMENT_FILE = (
    pathlib.Path(__file__).parents[2] / "data" / "boom_alert_supplement.json"
)


@functools.lru_cache(maxsize=1)
def supplemental_fields():
    """Avro field entries for what BOOM adds to an alert after ingestion."""
    if not SUPPLEMENT_FILE.exists():
        return []
    return json.loads(SUPPLEMENT_FILE.read_text()).get("fields") or []


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
