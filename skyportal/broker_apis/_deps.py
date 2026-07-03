"""Optional per-broker transport dependencies.

Most brokers talk plain REST and need only ``requests`` (a core dep). A few need
a heavier client for their transport (Kafka, BigQuery/Pub-Sub); those ship as
pyproject *extras* so a deployment installs only what its enabled brokers use.
``require()`` turns a missing client into an actionable install hint instead of a
bare ImportError. Imports stay lazy (in-function) so core never pulls these in.
"""

import importlib

# Importable module (dotted) -> the pyproject optional-dependency extra that ships
# it (`pip install 'skyportal[<extra>]'`).
_EXTRA_FOR_MODULE = {
    "google.cloud.bigquery": "pittgoogle",
    "google.cloud.pubsub_v1": "pittgoogle",
    "google.oauth2.service_account": "pittgoogle",
}


def require(module, extra=None):
    """Import and return ``module`` (dotted path), raising a friendly install hint
    keyed to the pip extra that provides it if it is missing."""
    extra = extra or _EXTRA_FOR_MODULE.get(module, "brokers-all")
    try:
        return importlib.import_module(module)
    except ImportError as e:
        raise ImportError(
            f"This broker needs the '{module}' package; install it with "
            f"`pip install 'skyportal[{extra}]'`."
        ) from e
