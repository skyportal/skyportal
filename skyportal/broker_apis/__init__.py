from importlib import import_module

# Class name -> module, listed in implementation order, to keep the matching db
# enum stable. Append new providers at the end.
_BROKERS = {
    "GENERICBROKER": "generic",
    "LASAIRBROKER": "lasair",
    "BABAMULBROKER": "babamul",
    "BOOMBROKER": "boom",
    "FINKBROKER": "fink",
    "ALERCEBROKER": "alerce",
    "ANTARESBROKER": "antares",
    "PITTGOOGLEBROKER": "pittgoogle",
    "AMPELBROKER": "ampel",
}

_MODULES = {**_BROKERS, "BrokerAPI": "interface"}

BROKER_CLASSNAMES = tuple(_BROKERS)


def __getattr__(name):
    if name == "BROKERS":
        return tuple(__getattr__(classname) for classname in _BROKERS)
    if name not in _MODULES:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    return getattr(import_module(f".{_MODULES[name]}", __name__), name)


def __dir__():
    return sorted([*globals(), *_MODULES, "BROKERS"])
