from importlib import import_module

# Class name -> module, listed in implementation order, to keep matching enum in db stable
_APIS = {
    "MMAAPI": "observation_plan",
    "GENERICAPI": "generic",
    "SLACKAPI": "slack",
    "ATLASAPI": "atlas",
    "COLIBRIAPI": "colibri",
    "GROWTHINDIAMMAAPI": "growth_india",
    "KAITAPI": "kait",
    "SEDMAPI": "sedm",
    "SEDMV2API": "sedmv2",
    "IOOAPI": "lt",
    "IOIAPI": "lt",
    "SPRATAPI": "lt",
    "SINISTROAPI": "lco",
    "SPECTRALAPI": "lco",
    "FLOYDSAPI": "lco",
    "MUSCATAPI": "lco",
    "NICERAPI": "nicer",
    "PS1API": "ps1",
    "SOARGHTSAPI": "soar",
    "SOARGHTSIMAGERAPI": "soar",
    "SOARTSPECAPI": "soar",
    "UVOTXRTAPI": "swift",
    "UVOTXRTMMAAPI": "swift",
    "TAROTAPI": "tarot",
    "TESSAPI": "tess",
    "TRTAPI": "trt",
    "WINTERAPI": "winter",
    "SPRINGAPI": "winter",
    "ZTFAPI": "ztf",
    "ZTFMMAAPI": "ztf",
    "GEMINIAPI": "gemini",
    "BINOSPECAPI": "mmt.binospec",
    "MMIRSAPI": "mmt.mmirs",
    "TTTAPI": "ttt",
    "NEWFIRMAPI": "blanco",
    "RUBINMMAAPI": "rubin",
    "NGPSAPI": "ngps",
}

# Listeners, listed in implementation order, to keep matching enum in db stable
_LISTENERS = {"SEDMListener": "sedm"}

_GENERIC_INTERFACES = {
    "FollowUpAPI": "interface",
    "Listener": "interface",
    "GenericRequest": "observation_plan",
}

_MODULES = {**_APIS, **_LISTENERS, **_GENERIC_INTERFACES}

API_CLASSNAMES = tuple(_APIS)
LISTENER_CLASSNAMES = tuple(_LISTENERS)


def __getattr__(name):
    if name == "APIS":
        return tuple(__getattr__(classname) for classname in _APIS)
    if name == "LISTENERS":
        return tuple(__getattr__(classname) for classname in _LISTENERS)
    if name not in _MODULES:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    return getattr(import_module(f".{_MODULES[name]}", __name__), name)


def __dir__():
    return sorted([*globals(), *_MODULES, "APIS", "LISTENERS"])
