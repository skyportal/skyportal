"""Reading every sncosmo bandpass file takes seconds, so the image build caches
their effective wavelengths with `python -m skyportal.utils.bandpass_wavelengths`."""

import hashlib
import json
import os

import astropy.utils.data
import sncosmo
from sncosmo.builtins import get_rootdir

from baselayer.log import make_log

from ..enum_types import existing_bandpasses_names
from .cache import cache_folder

log = make_log("bandpass_wavelengths")

CACHE_FILE = os.path.join(cache_folder, "bandpass_wavelengths.json")


def data_signature():
    digest = hashlib.sha256(sncosmo.__version__.encode())
    folder = os.path.join(get_rootdir(), "bandpasses")
    paths = sorted(
        os.path.join(root, name) for root, _, files in os.walk(folder) for name in files
    )
    for path in paths:
        digest.update(
            f"{os.path.relpath(path, folder)}:{os.path.getsize(path)}\n".encode()
        )
    return digest.hexdigest()


def load():
    try:
        with open(CACHE_FILE) as f:
            cached = json.load(f)
        if cached["signature"] != data_signature():
            return {}
        return {
            name: float(wavelength)
            for name, wavelength in cached["wavelengths"].items()
            if name in existing_bandpasses_names
        }
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return {}


def save(wavelengths):
    entries = {
        name: wavelength
        for name, wavelength in wavelengths.items()
        if name in existing_bandpasses_names and wavelength is not None
    }
    try:
        os.makedirs(cache_folder, exist_ok=True)
        tmp = f"{CACHE_FILE}.{os.getpid()}"
        with open(tmp, "w") as f:
            json.dump({"signature": data_signature(), "wavelengths": entries}, f)
        os.replace(tmp, CACHE_FILE)
    except OSError as e:
        log(f"Could not save {CACHE_FILE}: {e}")


if __name__ == "__main__":
    wavelengths = {}
    with astropy.utils.data.conf.set_temp("remote_timeout", 2):
        for name in existing_bandpasses_names:
            try:
                wavelengths[name] = float(sncosmo.get_bandpass(name).wave_eff)
            except Exception as e:
                log(f"Skipping bandpass {name}: {e}")
    save(wavelengths)
    log(f"Saved the effective wavelengths of {len(wavelengths)} bandpasses")
