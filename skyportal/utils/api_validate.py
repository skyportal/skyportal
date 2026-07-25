"""Pydantic-based request validation for API handlers.

Annotate a keyword-only handler parameter named `body` or `query` with a
pydantic model (and optionally the return type with a response model);
`spec_from_handlers` reads these hints to document the endpoint. At runtime
the handler validates explicitly with `BaseHandler.parse_body` /
`BaseHandler.parse_query`, which 400 with field-level errors:

    class MyBody(BaseModel):
        name: str

    @permissions(["..."])
    async def post(self, obj_id: str, *, body: MyBody = None) -> MyResponse:
        body = self.parse_body(MyBody)

    @auth_or_token
    async def get(self, *, query: MyQuery = None):
        query = self.parse_query(MyQuery)
"""

import inspect
import types
import typing

from pydantic import BaseModel

REF_TEMPLATE = "#/components/schemas/{model}"


def model_from_annotation(annotation):
    """Extract a pydantic model class from an annotation, unwrapping `X | None`."""
    if inspect.isclass(annotation) and issubclass(annotation, BaseModel):
        return annotation
    if typing.get_origin(annotation) in (typing.Union, types.UnionType):
        for arg in typing.get_args(annotation):
            if inspect.isclass(arg) and issubclass(arg, BaseModel):
                return arg
    return None


def _keyword_only_model(method, name):
    """Pydantic model annotating the keyword-only parameter `name`, or None.

    `inspect.signature` follows `__wrapped__`, so this sees through
    `@permissions` and the path-parameter validation wrapper.
    """
    param = inspect.signature(method).parameters.get(name)
    if param is not None and param.kind is inspect.Parameter.KEYWORD_ONLY:
        return model_from_annotation(param.annotation)
    return None


def body_model_from(method):
    """Pydantic request-body model of `method` (its `body` parameter), or None."""
    return _keyword_only_model(method, "body")


def query_model_from(method):
    """Pydantic query-parameter model of `method` (its `query` parameter), or None."""
    return _keyword_only_model(method, "query")


def _is_list_annotation(annotation):
    """True if an annotation is a list type, unwrapping `X | None`."""
    if typing.get_origin(annotation) in (typing.Union, types.UnionType):
        return any(_is_list_annotation(arg) for arg in typing.get_args(annotation))
    return annotation is list or typing.get_origin(annotation) is list


def query_dict_from(query_arguments, model):
    """Decode tornado query arguments (name → list of bytes) for `model`.

    Repeated parameters keep the last value (tornado semantics); values for
    list-typed fields are split on commas (the API-wide convention).
    """
    list_fields = {
        name
        for name, field in model.model_fields.items()
        if _is_list_annotation(field.annotation)
    }
    args = {}
    for name, values in query_arguments.items():
        value = values[-1].decode("utf-8", "replace")
        args[name] = value.split(",") if name in list_fields and value else value
    return args


def query_parameters_from(model):
    """Render a pydantic query model's fields as OpenAPI `parameters` entries.

    Query models must be flat (scalars, lists, Literals) — nested models
    would leave dangling `$defs` references.
    """
    schema = _to_openapi_30(model.model_json_schema(ref_template=REF_TEMPLATE))
    required = schema.get("required", [])
    parameters = []
    for name, prop in schema.get("properties", {}).items():
        prop.pop("title", None)
        if prop.get("default", ...) is None:
            del prop["default"]
        parameter = {"in": "query", "name": name, "required": name in required}
        description = prop.pop("description", None)
        if description:
            parameter["description"] = description
        parameter["schema"] = prop
        parameters.append(parameter)
    return parameters


def response_model_from(method):
    """Pydantic model in the return annotation of `method`, or None."""
    return model_from_annotation(inspect.signature(method).return_annotation)


def format_validation_errors(exc):
    """Render a pydantic ValidationError as a compact one-line message."""
    return "; ".join(
        f"{'.'.join(str(loc) for loc in error['loc']) or 'body'}: {error['msg']}"
        for error in exc.errors()
    )


def _to_openapi_30(node):
    """Convert pydantic's JSON Schema (2020-12) to OpenAPI 3.0: replace
    `anyOf: [X, {type: null}]` with `X` + `nullable: true`."""
    if isinstance(node, list):
        return [_to_openapi_30(item) for item in node]
    if not isinstance(node, dict):
        return node
    node = {key: _to_openapi_30(value) for key, value in node.items()}
    any_of = node.get("anyOf")
    if any_of and {"type": "null"} in any_of:
        rest = [subschema for subschema in any_of if subschema != {"type": "null"}]
        del node["anyOf"]
        if len(rest) == 1:
            node.update(rest[0])
        else:
            node["anyOf"] = rest
        node["nullable"] = True
    return node


def register_pydantic_schema(spec, model):
    """Register a pydantic model (and any nested models) as OpenAPI components
    on an APISpec; return a `$ref` to the model's component."""
    schema = model.model_json_schema(ref_template=REF_TEMPLATE)
    for name, subschema in schema.pop("$defs", {}).items():
        _register_component(spec, name, _to_openapi_30(subschema))
    _register_component(spec, model.__name__, _to_openapi_30(schema))
    return {"$ref": REF_TEMPLATE.format(model=model.__name__)}


def _register_component(spec, name, schema):
    if name not in spec.components.schemas:
        spec.components.schema(name, component=schema)
