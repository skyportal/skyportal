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

Positional parameters are path parameters. Their annotations drive both
coercion (`BaseHandler.prepare`) and the `in: path` entries of the spec, so
they need no docstring block; use `Annotated[T, Field(description=...)]` to
document one:

    async def get(self, obj_id: str, filter_id: int | None = None):
"""

import inspect
import re
import types
import typing
from functools import cache

from pydantic import BaseModel, TypeAdapter

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
    `@permissions` / `@auth_or_token`.
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


def path_parameters_of(method):
    """Positional parameters of a handler method, in URL-capture order.

    `inspect.signature` follows `__wrapped__`, so this sees through
    `@permissions` / `@auth_or_token`.
    """
    return [
        param
        for param in list(inspect.signature(method).parameters.values())[1:]
        if param.kind
        in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD)
    ]


@cache
def path_adapters_for(handler_cls, method_name):
    """`(index, name, TypeAdapter)` per annotated path parameter of a handler
    method, for coercing tornado's captured strings in `BaseHandler.prepare`.

    Cached on the handler class: signatures are fixed at import time.
    """
    method = getattr(handler_cls, method_name, None)
    if method is None:
        return ()
    return tuple(
        (index, param.name, TypeAdapter(param.annotation))
        for index, param in enumerate(path_parameters_of(method))
        if param.annotation is not inspect.Parameter.empty
    )


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


def path_parameters_from(method, path):
    """Render the `{name}` placeholders of `path` as OpenAPI `parameters`
    entries, typed from the matching positional parameters of `method`.

    Driving this off the rendered path (rather than the signature alone) keeps
    the documented parameters and the URL template in lockstep: a path cannot
    gain a placeholder that goes undocumented, or document one it lacks.
    """
    annotations = {
        param.name: param.annotation
        for param in path_parameters_of(method)
        if param.annotation is not inspect.Parameter.empty
    }
    parameters = []
    for name in re.findall(r"\{(\w+)\}", path):
        parameter = {"in": "path", "name": name, "required": True}
        annotation = annotations.get(name)
        schema = (
            _to_openapi_30(TypeAdapter(annotation).json_schema())
            if annotation is not None
            else {"type": "string"}
        )
        schema.pop("title", None)
        # `T | None` marks an optional trailing capture, which is expressed as
        # a separate (shorter) path rather than a nullable path parameter.
        schema.pop("nullable", None)
        description = schema.pop("description", None)
        if description:
            parameter["description"] = description
        parameter["schema"] = schema
        parameters.append(parameter)
    return parameters


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
