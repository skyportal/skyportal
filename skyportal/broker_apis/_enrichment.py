"""Fields BOOM writes onto an alert that its Avro schema does not describe.

A filter pipeline runs against the Mongo document, not the packet that
arrived, and BOOM enriches that document after ingestion. Those fields are in
no schema, so a path that exists is undiscoverable -- and a pipeline that
references one nobody published matches nothing, which looks exactly like a
night with no candidates.

The groups live in data rather than here: enrichment grows -- other fits,
other classifiers -- and adding one should be an edit to the file, not to
this module. Nothing in this code knows what a Villar fit is.

The notes are the other half. A path being discoverable is not the same as
its meaning being guessable: a rise rate in magnitudes per day is negative
while the source brightens, and `acai_b` scores an alert as bogus, so the
cut that reads correctly selects fading sources and artefacts. `doc` is a
field of Avro, so a note travels to the filter builder and the MCP alike.

A stopgap. BOOM owns the enrichment and should advertise it; when it does,
every group here arrives from the broker instead. `supplement_schema` stands
aside for any field the broker declares, and `annotate_schema` leaves a field
the broker documents alone, so that switchover needs no coordination and
removing this needs no flag day.
"""

__all__ = ["annotate_schema", "supplement_schema", "supplemental_fields"]

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


@functools.lru_cache(maxsize=1)
def field_notes():
    """Dotted path -> what a pipeline author needs to know about that field.

    A `*` stands for one path segment, which is how a per-band field is
    written: photstats holds one record per filter, all with the same meaning.
    """
    if not SUPPLEMENT_FILE.exists():
        return {}
    return json.loads(SUPPLEMENT_FILE.read_text()).get("notes") or {}


def _note_for(path, notes):
    if path in notes:
        return notes[path]
    parts = path.split(".")
    for pattern, note in notes.items():
        candidate = pattern.split(".")
        if len(candidate) == len(parts) and all(
            expected in ("*", actual) for expected, actual in zip(candidate, parts)
        ):
            return note
    return None


def annotate_schema(schema, notes=None, prefix=""):
    """Write the notes onto the fields they describe, in place.

    Avro allows `doc` on any field, and a field that already carries one is
    left as the broker wrote it.
    """
    notes = field_notes() if notes is None else notes
    if not notes or not isinstance(schema, dict):
        return schema
    for field in schema.get("fields") or []:
        if not isinstance(field, dict) or not field.get("name"):
            continue
        path = f"{prefix}.{field['name']}" if prefix else field["name"]
        if not field.get("doc"):
            note = _note_for(path, notes)
            if note:
                field["doc"] = note
        for branch in _records(field.get("type")):
            annotate_schema(branch, notes, path)
    return schema


def _records(kind):
    """The record definitions reachable from one field's type."""
    if isinstance(kind, list):
        for branch in kind:
            yield from _records(branch)
    elif isinstance(kind, dict):
        if kind.get("type") == "array":
            yield from _records(kind.get("items"))
        elif kind.get("type") == "map":
            yield from _records(kind.get("values"))
        elif kind.get("fields"):
            yield kind
