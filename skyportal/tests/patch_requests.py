"""
Patch the JSON module used by requests (simplejson) so non-finite floats in
request bodies encode (as ``NaN``/``Infinity``) instead of raising.

requests calls ``complexjson.dumps(body, allow_nan=False)``. Popping the kwarg
is not enough: unlike stdlib ``json``, simplejson's default also rejects NaN, so
we force ``allow_nan=True`` (its ``dumps`` then emits ``NaN``, as before the
requests/simplejson upgrade).
"""


def force_allow_nan(f):
    if getattr(f, "_allow_nan_forced", False):
        return f

    def wrapped(*args, **kwargs):
        kwargs["allow_nan"] = True
        return f(*args, **kwargs)

    wrapped._allow_nan_forced = True
    return wrapped


def patch_requests():
    from requests.compat import json as requests_json

    requests_json.dumps = force_allow_nan(requests_json.dumps)
