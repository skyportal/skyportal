"""
Patch the JSON module used by requests (likely simplejson) to
ignore the allow_nan keyword argument (we always want it to be set to
True)
"""


def remove_allow_nan_kwarg(f):
    def wrapped(*args, **kwargs):
        kwargs.pop("allow_nan", None)
        return f(*args, **kwargs)

    return wrapped


def patch_requests():
    from requests.compat import json as requests_json

    requests_json.dumps = remove_allow_nan_kwarg(requests_json.dumps)
