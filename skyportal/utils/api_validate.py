"""Pydantic-based request validation for API handlers.

Annotate a keyword-only handler parameter with a pydantic model (and
optionally the return type with a response model); `spec_from_handlers` reads
these hints to document the endpoint. At runtime the handler validates
explicitly with `BaseHandler.parse_body`, which 400s with field-level errors:

    class MyBody(BaseModel):
        name: str

    @permissions(["..."])
    async def post(self, obj_id: str, *, body: MyBody = None) -> MyResponse:
        body = self.parse_body(MyBody)
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


def body_model_from(method):
    """Pydantic model annotating a keyword-only parameter of `method`, or None.

    `inspect.signature` follows `__wrapped__`, so this sees through
    `@permissions` and the path-parameter validation wrapper.
    """
    for param in inspect.signature(method).parameters.values():
        if param.kind is inspect.Parameter.KEYWORD_ONLY:
            model = model_from_annotation(param.annotation)
            if model is not None:
                return model
    return None


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
