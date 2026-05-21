"""Utility decorators for skyportal Tornado handlers."""

from functools import wraps


def validate_path_params(**param_types):
    """Coerce (and validate) named path parameters on a Tornado handler method.

    Each keyword argument is one of:
      - ``name=type`` — required: coerce the path value to ``type`` (e.g. ``int``).
      - ``name=(type, default)`` — optional: if the value is ``None`` or empty,
        substitute ``default``; otherwise coerce to ``type``.

    On coercion failure (``TypeError`` or ``ValueError``), the wrapped method is
    skipped and ``self.error(f"Invalid {name}: {value}")`` is returned, matching
    the boilerplate this decorator replaces.

    Example::

        @auth_or_token
        @validate_path_params(filter_id=int, obj_id=str)
        async def get(self, filter_id, obj_id):
            ...
    """
    parsed = {}
    for name, spec in param_types.items():
        if isinstance(spec, tuple):
            type_, default = spec
            parsed[name] = (type_, default, True)
        else:
            parsed[name] = (spec, None, False)

    def decorator(method):
        param_names = method.__code__.co_varnames[: method.__code__.co_argcount]
        # Drop "self"
        if param_names and param_names[0] == "self":
            param_names = param_names[1:]

        @wraps(method)
        def wrapper(self, *args, **kwargs):
            args = list(args)
            for i, pname in enumerate(param_names[: len(args)]):
                if pname not in parsed:
                    continue
                type_, default, has_default = parsed[pname]
                value = args[i]
                if value is None or value == "":
                    if has_default:
                        args[i] = default
                    continue
                try:
                    args[i] = type_(value)
                except (TypeError, ValueError):
                    return self.error(f"Invalid {pname}: {value}")

            for pname, value in list(kwargs.items()):
                if pname not in parsed:
                    continue
                type_, default, has_default = parsed[pname]
                if value is None or value == "":
                    if has_default:
                        kwargs[pname] = default
                    continue
                try:
                    kwargs[pname] = type_(value)
                except (TypeError, ValueError):
                    return self.error(f"Invalid {pname}: {value}")

            return method(self, *args, **kwargs)

        return wrapper

    return decorator
