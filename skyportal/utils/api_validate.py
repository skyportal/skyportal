"""Pydantic-based request validation for API handlers.

Annotate a keyword-only handler parameter with a pydantic model and decorate
the method with `validate_api`: the JSON body is validated and injected at
call time, and `spec_from_handlers` uses the same models to document the
endpoint, so docs and behavior cannot drift.

    class MyBody(BaseModel):
        name: str

    @permissions(["..."])  # validate_api goes below so auth runs first
    @validate_api(response=MyResponse)
    async def post(self, some_path_arg, *, body: MyBody):
        ...
"""

import functools
import inspect
import types
import typing

from pydantic import BaseModel, ValidationError

REF_TEMPLATE = "#/components/schemas/{model}"


def _model_from_annotation(annotation):
    """Extract a pydantic model class from an annotation, unwrapping `X | None`."""
    if inspect.isclass(annotation) and issubclass(annotation, BaseModel):
        return annotation
    if typing.get_origin(annotation) in (typing.Union, types.UnionType):
        for arg in typing.get_args(annotation):
            if inspect.isclass(arg) and issubclass(arg, BaseModel):
                return arg
    return None


def _find_body_param(func):
    """Return (name, model) for the first parameter annotated with a pydantic
    model, or (None, None)."""
    hints = typing.get_type_hints(func)
    for name in inspect.signature(func).parameters:
        model = _model_from_annotation(hints.get(name))
        if model is not None:
            return name, model
    return None, None


def _format_errors(exc):
    return "; ".join(
        f"{'.'.join(str(loc) for loc in error['loc']) or 'body'}: {error['msg']}"
        for error in exc.errors()
    )


def validate_api(method=None, *, response=None):
    """Validate the JSON request body against the pydantic model found in the
    method's type annotations, injecting the parsed model as a keyword
    argument. `response` optionally documents the `data` payload of the 200
    response in the OpenAPI spec.

    Apply below `@permissions`/`@auth_or_token` so authentication runs first.
    """

    def decorator(func):
        body_param, body_model = _find_body_param(func)

        def parse_body(handler):
            try:
                return body_model.model_validate(handler.get_json()), None
            except ValidationError as e:
                return None, handler.error(
                    f"Invalid/missing parameters: {_format_errors(e)}"
                )

        if inspect.iscoroutinefunction(func):

            @functools.wraps(func)
            async def wrapper(self, *args, **kwargs):
                if body_model is not None:
                    kwargs[body_param], error = parse_body(self)
                    if error is not None:
                        return error
                return await func(self, *args, **kwargs)

        else:

            @functools.wraps(func)
            def wrapper(self, *args, **kwargs):
                if body_model is not None:
                    kwargs[body_param], error = parse_body(self)
                    if error is not None:
                        return error
                return func(self, *args, **kwargs)

        wrapper.__body_schema__ = body_model
        wrapper.__response_schema__ = response
        return wrapper

    if method is not None:
        return decorator(method)
    return decorator


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
