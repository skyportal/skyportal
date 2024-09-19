import os
from os.path import join as pjoin

from . import __version__

from tornado.routing import URLSpec
from apispec import APISpec
from apispec.ext.marshmallow import MarshmallowPlugin
from .models import schema

HTTP_METHODS = ("head", "get", "post", "put", "patch", "delete", "options")

api_description = pjoin(os.path.dirname(__file__), 'api_description.md')


def spec_from_handlers(handlers, exclude_internal=True, metadata=None):
    """Generate an OpenAPI spec from Tornado handlers.

    The docstrings of the various http methods of the Tornado handlers
    (`get`, `put`, etc.), should contain OpenAPI yaml after three
    dashed.  E.g.:

    ```yaml
    ---
    summary: Get a source
    description: Retrieve a source
    parameters:
      - in: path
        name: obj_id
        required: false
        schema:
          type: integer
          required: false
    responses:
      200:
        content:
          application/json:
            schema:
              oneOf:
                - SingleSource
                - Error
    ```

    The yaml snippet may contain two top-level keywords, `single` and
    `multiple`, that can be used to disambiguate the OpenAPI spec for
    a single URL that is meant to return both single and multiple
    objects.  E.g., `/api/sources/{obj_id}` may return multiple
    objects if `{obj_id}` is left unspecified.  If these keywords
    are not specified, the OpenAPI snippet is used as is.

    Schemas are automatically resolved to matching Marshmallow objects
    in the `spec` module.  E.g., in the above example we use
    `SingleSource` and `Error`, which refer to `spec.SingleSource` and
    `spec.Error`.  All schemas in `schema` are added to the OpenAPI definition.

    """
    meta = {
        'title': 'SkyPortal',
        'version': __version__,
        'openapi_version': '3.0.2',
        'info': {
            'description': open(api_description).read(),
            'x-logo': {
                'url': 'https://raw.githubusercontent.com/skyportal/skyportal/main/static/images/skyportal_logo.png',
                'backgroundColor': '#FFFFFF',
                'altText': 'SkyPortal logo',
                'href': 'https://skyportal.io/docs',
            },
        },
    }
    if metadata is not None:
        meta.update(metadata)

    openapi_spec = APISpec(
        **meta,
        plugins=[MarshmallowPlugin()],
    )

    token_scheme = {
        "type": "apiKey",
        "in": "header",
        "name": "Authorization",
        "description": "Header should be in the format 'token abcd-efgh-0000-1234'",
    }
    openapi_spec.components.security_scheme("token", token_scheme)

    schema.register_components(openapi_spec)
    from apispec import yaml_utils
    import inspect
    import re

    handlers = [
        handler
        for handler in handlers
        if not isinstance(handler, URLSpec) and len(handler) == 2
    ]
    if exclude_internal:
        handlers = [
            (route, handler_cls)
            for (route, handler_cls) in handlers
            if '/internal/' not in route
        ]
    for endpoint, handler in handlers:
        for http_method in HTTP_METHODS:
            method = getattr(handler, http_method)
            if method.__doc__ is None:
                continue

            path_template = endpoint
            path_template = re.sub(r'\(.*?\)\??', '/{}', path_template)
            path_template = re.sub(r'(/)+', '/', path_template)
            path_parameters = path_template.count('{}')

            spec = yaml_utils.load_yaml_from_docstring(method.__doc__)
            parameters = list(inspect.signature(method).parameters.keys())[1:]
            # remove parameters called "ignored_args"
            parameters = [param for param in parameters if param != 'ignored_args']
            parameters = [f"{{{param}}}" for param in parameters]
            parameters = parameters + (path_parameters - len(parameters)) * [
                '',
            ]

            if parameters[-1:] == [''] and path_template.endswith('/{}'):
                path_template = path_template[:-3]

            multiple_spec = spec.pop('multiple', {})
            single_spec = spec.pop('single', {})
            other_spec = spec

            for subspec in [single_spec, other_spec]:
                if subspec:
                    path = path_template.format(*parameters)
                    openapi_spec.path(path=path, operations={http_method: subspec})

            if multiple_spec:
                multiple_path_template = path_template.rsplit('/', 1)[0]
                multiple_path = multiple_path_template.format(*parameters[:-1])
                openapi_spec.path(
                    path=multiple_path, operations={http_method: multiple_spec}
                )

    return openapi_spec
