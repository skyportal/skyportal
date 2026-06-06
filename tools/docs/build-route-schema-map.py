#!/usr/bin/env python
"""Generate static/js/types/routeSchemaMap.ts from openapi.json.

For every (path, method) pair in the OpenAPI spec, inspect the
``200`` ``application/json`` response schema and resolve it to a
concrete component schema name plus a ``list`` flag. Endpoints whose
data shape is still inline / unknown are intentionally skipped — they
will surface as the next gap to tighten for the RTK-Query typing pass.

Resolution rules (in order):

* Top-level ``$ref`` to ``#/components/schemas/SingleX`` → ``X`` (list=False).
* Top-level ``$ref`` to ``#/components/schemas/ArrayOfXs`` → ``X`` (list=True).
* ``allOf: [$ref Success, {type: object, properties: {data: ...}}]``:
    - ``data`` is ``$ref: #/components/schemas/X`` → ``X`` (list=False).
    - ``data`` is ``{type: array, items: {$ref: #/components/schemas/X}}`` →
      ``X`` (list=True).
    - Otherwise → skip.
* Anything else → skip.

Output is sorted alphabetically by ``"<METHOD> <path>"`` key for stable diffs.

In addition to the ``ROUTE_SCHEMA_MAP`` constant, the emitted module
exports a ``RouteData<P>`` helper type that resolves a route key to the
typed shape of its response ``data`` field (scalar vs array picked from
the entry's ``list`` flag), so call sites get exact response typing
straight from the spec.
"""

from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
OPENAPI_PATH = REPO_ROOT / "openapi.json"
OUTPUT_PATH = REPO_ROOT / "static" / "js" / "types" / "routeSchemaMap.ts"

REF_PREFIX = "#/components/schemas/"
HTTP_METHODS = ("get", "post", "put", "delete", "patch")


def _ref_name(ref: str) -> str | None:
    """Return the component schema name for ``ref`` or ``None``."""
    if not isinstance(ref, str) or not ref.startswith(REF_PREFIX):
        return None
    return ref[len(REF_PREFIX) :]


def _resolve_data_member(data: dict, schemas: dict) -> tuple[str, bool] | None:
    """Resolve the ``data`` member of a ``Success`` allOf payload."""
    if not isinstance(data, dict):
        return None

    ref_name = _ref_name(data.get("$ref", ""))
    if ref_name and ref_name in schemas:
        return ref_name, False

    if data.get("type") == "array":
        items = data.get("items") or {}
        item_ref = _ref_name(items.get("$ref", ""))
        if item_ref and item_ref in schemas:
            return item_ref, True

    return None


def resolve_schema(schema: dict, schemas: dict) -> tuple[str, bool] | None:
    """Resolve a response schema to ``(schema_name, is_list)`` or ``None``."""
    if not isinstance(schema, dict):
        return None

    # Top-level $ref.
    ref_name = _ref_name(schema.get("$ref", ""))
    if ref_name:
        if ref_name.startswith("Single"):
            stripped = ref_name[len("Single") :]
            if stripped in schemas:
                return stripped, False
            return None
        if ref_name.startswith("ArrayOf"):
            stripped = ref_name[len("ArrayOf") :]
            if stripped.endswith("s"):
                candidate = stripped[:-1]
                if candidate in schemas:
                    return candidate, True
            return None
        return None

    # allOf: [$ref Success, {type: object, properties: {data: ...}}]
    all_of = schema.get("allOf")
    if isinstance(all_of, list):
        has_success_ref = any(
            _ref_name(sub.get("$ref", "")) == "Success"
            for sub in all_of
            if isinstance(sub, dict)
        )
        if not has_success_ref:
            return None
        for sub in all_of:
            if not isinstance(sub, dict) or sub.get("type") != "object":
                continue
            props = sub.get("properties") or {}
            data = props.get("data")
            if data is None:
                continue
            resolved = _resolve_data_member(data, schemas)
            if resolved is not None:
                return resolved
        return None

    return None


def build_entries(spec: dict) -> list[tuple[str, str, bool]]:
    """Return a sorted list of ``(route_key, schema_name, is_list)`` tuples."""
    paths = spec.get("paths") or {}
    schemas = (spec.get("components") or {}).get("schemas") or {}

    entries: list[tuple[str, str, bool]] = []
    for path, methods in paths.items():
        if not isinstance(methods, dict):
            continue
        for method, operation in methods.items():
            if method.lower() not in HTTP_METHODS:
                continue
            if not isinstance(operation, dict):
                continue
            responses = operation.get("responses") or {}
            # OpenAPI keys can be string or int — be defensive.
            ok = responses.get("200")
            if ok is None:
                ok = responses.get(200)
            if not isinstance(ok, dict):
                continue
            content = ok.get("content") or {}
            app_json = content.get("application/json")
            if not isinstance(app_json, dict):
                continue
            schema = app_json.get("schema")
            resolved = resolve_schema(schema, schemas)
            if resolved is None:
                continue
            schema_name, is_list = resolved
            route_key = f"{method.upper()} {path}"
            entries.append((route_key, schema_name, is_list))

    entries.sort(key=lambda row: row[0])
    return entries


HEADER = """/**
 * Generated by tools/docs/build-route-schema-map.py — DO NOT EDIT.
 *
 * Maps "<METHOD> <path>" → { schema: keyof components["schemas"], list: boolean }
 * for the impending RTK-Query spec-typing pass. Endpoints whose data shape is
 * still inline/unknown are omitted (they'll surface as the next gap to tighten).
 */
import type { components } from "./api";

export type SchemaName = keyof components["schemas"];

export const ROUTE_SCHEMA_MAP = {
"""

FOOTER = """} satisfies Record<string, { schema: SchemaName; list: boolean }>;

type RouteKey = keyof typeof ROUTE_SCHEMA_MAP;

/**
 * Resolve a route key to the typed shape of its response `data` field.
 * The map's `list` flag picks scalar-vs-array automatically.
 *
 * @example
 *   const data: RouteData<"GET /api/allocation"> = ...; // Allocation[]
 */
export type RouteData<P extends RouteKey> =
  (typeof ROUTE_SCHEMA_MAP)[P]["list"] extends true
    ? components["schemas"][(typeof ROUTE_SCHEMA_MAP)[P]["schema"]][]
    : components["schemas"][(typeof ROUTE_SCHEMA_MAP)[P]["schema"]];
"""


def render(entries: list[tuple[str, str, bool]]) -> str:
    lines = [HEADER]
    for route_key, schema_name, is_list in entries:
        lines.append(
            f'  "{route_key}": {{ schema: "{schema_name}" as const,'
            f" list: {'true' if is_list else 'false'} }},\n"
        )
    lines.append(FOOTER)
    return "".join(lines)


def main() -> None:
    spec = json.loads(OPENAPI_PATH.read_text())
    entries = build_entries(spec)
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(render(entries))
    print(f"Wrote {len(entries)} entries to {OUTPUT_PATH.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
