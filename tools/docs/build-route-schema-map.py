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
    - ``data`` is ``{type: object, properties: {<key>: {type: array,
      items: {$ref: X}}, ...pagination...}}`` with exactly one array-of-$ref
      child → ``X`` (list=True, wrapper=<key>).
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


# Pagination/listing keys that hint a properties dict is a wrapper payload.
_PAGINATION_HINTS = frozenset(
    {"totalMatches", "pageNumber", "numPerPage", "page", "sortBy", "sortOrder"}
)


def _resolve_data_member(
    data: dict, schemas: dict
) -> tuple[str, bool, str | None] | None:
    """Resolve the ``data`` member of a ``Success`` allOf payload."""
    if not isinstance(data, dict):
        return None

    ref_name = _ref_name(data.get("$ref", ""))
    if ref_name and ref_name in schemas:
        return ref_name, False, None

    if data.get("type") == "array":
        items = data.get("items") or {}
        item_ref = _ref_name(items.get("$ref", ""))
        if item_ref and item_ref in schemas:
            return item_ref, True, None

    return None


def _resolve_wrapped_data_member(
    data: dict, schemas: dict
) -> tuple[str, bool, str | None] | None:
    """Match the pagination/scalar wrapper data shape and pick the item child.

    Handles two variants:
    - array wrap: ``{<plural>: array of $ref, totalMatches, ...}`` → list=True
    - scalar wrap: ``{<key>: $ref, totalMatches, ...}`` → list=False
    """
    if not isinstance(data, dict) or data.get("type") != "object":
        return None
    props = data.get("properties")
    if not isinstance(props, dict):
        return None

    array_children: list[tuple[str, str]] = []
    ref_children: list[tuple[str, str]] = []
    for key, value in props.items():
        if not isinstance(value, dict):
            continue
        if value.get("type") == "array":
            items = value.get("items") or {}
            item_ref = _ref_name(items.get("$ref", ""))
            if item_ref and item_ref in schemas:
                array_children.append((key, item_ref))
            continue
        scalar_ref = _ref_name(value.get("$ref", ""))
        if scalar_ref and scalar_ref in schemas:
            ref_children.append((key, scalar_ref))

    is_list: bool
    if len(array_children) == 1 and not ref_children:
        wrapper_key, ref_name = array_children[0]
        is_list = True
    elif len(ref_children) == 1 and not array_children:
        wrapper_key, ref_name = ref_children[0]
        is_list = False
    else:
        # Zero or multi-item shapes (e.g. /api/groups) are intentionally skipped.
        return None

    other_keys = [k for k in props if k != wrapper_key]
    if other_keys and not any(k in _PAGINATION_HINTS for k in other_keys):
        # Looks like an unrelated object that just happens to have one
        # ref/array child; bail to stay conservative.
        return None

    # Peel a stray ArrayOf* item ref so the wrapper isn't array-of-array.
    if is_list and ref_name.startswith("ArrayOf"):
        stripped = ref_name[len("ArrayOf") :]
        if stripped.endswith("s"):
            candidate = stripped[:-1]
            if candidate in schemas:
                ref_name = candidate

    return ref_name, is_list, wrapper_key


def _resolve_arbitrary_ref_data_member(
    data: dict, schemas: dict
) -> tuple[str, bool, str | None] | None:
    """Handle ``data: {$ref: X}`` where X is not Single*/ArrayOf*.

    The direct-$ref branch in ``_resolve_data_member`` already covers this
    case, so this helper exists to keep the call structure parallel and
    document the intent. It is a thin alias.
    """
    return _resolve_data_member(data, schemas)


def resolve_schema(schema: dict, schemas: dict) -> tuple[str, bool, str | None] | None:
    """Resolve a response schema to ``(schema_name, is_list, wrapper)``."""
    if not isinstance(schema, dict):
        return None

    # Top-level $ref.
    ref_name = _ref_name(schema.get("$ref", ""))
    if ref_name:
        if ref_name.startswith("Single"):
            stripped = ref_name[len("Single") :]
            if stripped in schemas:
                return stripped, False, None
            return None
        if ref_name.startswith("ArrayOf"):
            stripped = ref_name[len("ArrayOf") :]
            if stripped.endswith("s"):
                candidate = stripped[:-1]
                if candidate in schemas:
                    return candidate, True, None
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
            # Order matters: try direct-ref / array-of-ref first (unchanged
            # behaviour), then the new pagination-wrapper rule.
            resolved = _resolve_data_member(data, schemas)
            if resolved is not None:
                return resolved
            resolved = _resolve_wrapped_data_member(data, schemas)
            if resolved is not None:
                return resolved
        return None

    return None


def build_entries(spec: dict) -> list[tuple[str, str, bool, str | None]]:
    """Return a sorted list of ``(route_key, schema, is_list, wrapper)`` tuples."""
    paths = spec.get("paths") or {}
    schemas = (spec.get("components") or {}).get("schemas") or {}

    entries: list[tuple[str, str, bool, str | None]] = []
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
            schema_name, is_list, wrapper = resolved
            route_key = f"{method.upper()} {path}"
            entries.append((route_key, schema_name, is_list, wrapper))

    entries.sort(key=lambda row: row[0])
    return entries


HEADER = """/**
 * Generated by tools/docs/build-route-schema-map.py — DO NOT EDIT.
 *
 * Maps "<METHOD> <path>" → { schema: keyof components["schemas"], list: boolean,
 * wrapper?: string } for the impending RTK-Query spec-typing pass. The optional
 * `wrapper` field is emitted for pagination-wrapper payloads where the response
 * `data` is `{ [wrapper]: <item>[], totalMatches?, pageNumber?, ... }` — see the
 * generator's `_resolve_wrapped_data_member` rule. Endpoints whose data shape is
 * still inline/unknown are omitted (they'll surface as the next gap to tighten).
 */
import type { components, paths } from "./api";

export type SchemaName = keyof components["schemas"];

export const ROUTE_SCHEMA_MAP = {
"""

FOOTER = """} satisfies Record<string, { schema: SchemaName; list: boolean; wrapper?: string }>;

type RouteKey = keyof typeof ROUTE_SCHEMA_MAP;
type RouteEntry<P extends RouteKey> = (typeof ROUTE_SCHEMA_MAP)[P];

/**
 * Best-effort optional pagination metadata that ships alongside a wrapper key.
 * Real responses vary (some routes also return `geojson`, `sortBy`, `sortOrder`,
 * `field_ids`, `probability`, ...) — consumers needing those must use `?.`
 * access, since they're not encoded here.
 */
type PaginationBonusFields = {
  totalMatches?: number;
  pageNumber?: number;
  numPerPage?: number;
  page?: number;
};

/**
 * Resolve a route key to the typed shape of its response `data` field.
 * - Wrapper routes (`wrapper` set) → `{ [W]: Schema[] | Schema } & PaginationBonusFields`,
 *   where the map's `list` flag picks array-vs-scalar for the wrapped value.
 * - Otherwise the map's `list` flag picks scalar-vs-array automatically.
 *
 * Caveat: PaginationBonusFields makes `totalMatches`/`pageNumber`/`numPerPage`/`page`
 * optional. Routes that historically declared these as required will need `?.`
 * access (or non-null assertions where the value is known to be present).
 */
type MappedRouteData<P extends RouteKey> =
  RouteEntry<P> extends { wrapper: infer W extends string; schema: infer S extends SchemaName }
    ? { [K in W]: RouteEntry<P>["list"] extends true
        ? components["schemas"][S][]
        : components["schemas"][S] } & PaginationBonusFields
    : RouteEntry<P>["list"] extends true
      ? components["schemas"][RouteEntry<P>["schema"]][]
      : components["schemas"][RouteEntry<P>["schema"]];

/**
 * Generated fallback for endpoints not in the curated map (inline / augmented
 * response shapes). Derives the response `data` type straight from the
 * openapi-typescript output in `api.ts`, so it stays in sync on regen — no
 * hand-written types. An endpoint typing as `never`/`unknown` here means its 200
 * response isn't fully documented in the spec (a real gap to fix in the backend
 * docstring, not to paper over on the client).
 */
type HttpMethod = "get" | "post" | "put" | "patch" | "delete";

type RouteKeysOf<P extends keyof paths & string> = {
  [M in Extract<keyof paths[P], HttpMethod> & string]: `${Uppercase<M>} ${P}`;
}[Extract<keyof paths[P], HttpMethod> & string];

/** Union of every documented `"<METHOD> <path>"` key. */
type DocumentedRouteKey = {
  [P in keyof paths & string]: RouteKeysOf<P>;
}[keyof paths & string];

type ResponseBody<S extends string> =
  S extends `${infer M} ${infer P}`
    ? P extends keyof paths
      ? Lowercase<M> extends keyof paths[P]
        ? paths[P][Lowercase<M>] extends {
            responses: { 200: { content: { "application/json": infer B } } };
          }
          ? B
          : never
        : never
      : never
    : never;

type ApiRouteData<S extends string> =
  ResponseBody<S> extends { data?: infer D } ? D : ResponseBody<S>;

/**
 * Resolve a route key to the typed shape of its response `data` field.
 * - Curated map (named-schema responses) → clean `Schema` / `Schema[]` / wrapper.
 * - Everything else documented → generated type derived from `api.ts`.
 *
 * @example
 *   const data: RouteData<"GET /api/allocation"> = ...; // Allocation[]
 *   const created: RouteData<"POST /api/analysis_service"> = ...; // { id?: number }
 */
export type RouteData<P extends RouteKey | DocumentedRouteKey> =
  P extends RouteKey ? MappedRouteData<P> : ApiRouteData<P>;
"""


def render(entries: list[tuple[str, str, bool, str | None]]) -> str:
    lines = [HEADER]
    for route_key, schema_name, is_list, wrapper in entries:
        list_literal = "true" if is_list else "false"
        if wrapper is not None:
            lines.append(
                f'  "{route_key}": {{ schema: "{schema_name}" as const,'
                f' list: {list_literal}, wrapper: "{wrapper}" as const }},\n'
            )
        else:
            lines.append(
                f'  "{route_key}": {{ schema: "{schema_name}" as const,'
                f" list: {list_literal} }},\n"
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
