from . import __version__

from tornado.routing import URLSpec
from apispec import APISpec
from apispec.ext.marshmallow import MarshmallowPlugin
from . import schema


def spec_from_handlers(handlers):
    """Generate an OpenAPI spec from Tornado handlers.

    The docstrings of the various http methods of the Tornado handlers
    (`get`, `put`, etc.), should contain OpenAPI yaml after three
    dashed.  E.g.:

    ```yaml
    ---
    description: Retrieve a source
    parameters:
      - in: path
        name: source_id
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
    objects.  E.g., `/api/sources/{source_id}` may return multiple
    objects if `{source_id}` is left unspecified.  If these keywords
    are not specified, the OpenAPI snippet is used as is.

    Schemas are automatically resolved to matching Marshmallow objects
    in the `spec` module.  E.g., in the above example we use
    `SingleSource` and `Error`, which refer to `spec.SingleSource` and
    `spec.Error`.  All schemas in `schema` are added to the OpenAPI definition.

    """
    openapi_spec = APISpec(
        title='SkyPortal',
        version=__version__,
        openapi_version='3.0.2',
        info=dict(
            description='SkyPortal API'
        ),
        plugins=[
            MarshmallowPlugin(),
        ]
    )

    token_scheme = {
        "type": "apiKey", "in": "header", "name": "Authorization",
        "description": "Header should be in the format 'token abcd-efgh-0000-1234'"
    }
    openapi_spec.components.security_scheme("token", token_scheme)

    schema.register_components(openapi_spec)
    from apispec import yaml_utils
    import inspect
    import re

    HTTP_METHODS = ("get", "put", "post", "delete", "options", "head", "patch")
    handlers = [handler for handler in handlers if not
                isinstance(handler, URLSpec) and len(handler) == 2]
    for (endpoint, handler) in handlers:
        for http_method in HTTP_METHODS:
            method = getattr(handler, http_method)
            if method.__doc__ is None:
                continue

            path_template = endpoint
            path_template = re.sub('\(.*?\)\??', '/{}', path_template)
            path_template = re.sub('(/)+', '/', path_template)
            path_parameters = path_template.count('{}')

            spec = yaml_utils.load_yaml_from_docstring(method.__doc__)
            parameters = list(inspect.signature(method).parameters.keys())[1:]
            parameters = parameters + (path_parameters - len(parameters)) * ['',]

            if parameters[-1:] == [''] and path_template.endswith('/{}'):
                path_template = path_template[:-3]

            multiple_spec = spec.pop('multiple', {})
            single_spec = spec.pop('single', {})
            other_spec = spec

            for subspec in [single_spec, other_spec]:
                if subspec:
                    path = path_template.format(*parameters)
                    openapi_spec.path(
                        path=path,
                        operations={
                            http_method: subspec
                        }
                    )

            if multiple_spec:
                multiple_path_template = path_template.rsplit('/', 1)[0]
                multiple_path = multiple_path_template.format(
                    *parameters[:-1]
                )
                openapi_spec.path(
                    path=multiple_path,
                    operations={
                        http_method: multiple_spec
                    }
                )

    return openapi_spec
