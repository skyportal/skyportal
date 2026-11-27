import gzip
import io
import re
import threading
import time
from contextlib import contextmanager
from tempfile import SpooledTemporaryFile
from urllib.parse import urlsplit

import numpy as np
import requests
from astropy.io import fits

MAX_FITS_BYTES = 96 * 1024 * 1024
_FITS_SLOTS = threading.BoundedSemaphore(2)
_PATHS = {
    "lamost": (
        ("www.lamost.org", r"/dr12/v2\.0/spectrum/fits/\d+"),
        ("www.lamost.org", r"/openapi/dr12/v2\.0/mrs/spectrum/fits"),
    ),
    "boss": (
        (
            "dr20.sdss.org",
            r"/sas/dr20/(?:spectro/boss/redux/v6_2_1/spectra/daily/full/|prior-surveys/)[\w/.-]+\.fits",
        ),
    ),
    "apogee": (
        (
            "dr20.sdss.org",
            r"/sas/dr20/spectro/apogee/redux/1\.3/visit/[\w/+.\-]+\.fits",
        ),
    ),
    "desi": (
        (
            "data.desi.lbl.gov",
            r"/public/dr1/spectro/redux/iron/exposures/\d{8}/\d{8}/cframe-[brz]\d-\d{8}\.fits\.gz",
        ),
    ),
}


def trusted_fits_url(url, kind):
    parts = urlsplit(url)
    if parts.scheme != "https" or parts.fragment or ".." in parts.path:
        return False
    if kind == "desi":
        if parts.query not in ("", "download=1"):
            return False
    elif kind == "lamost" and parts.path.startswith("/openapi/"):
        if not re.fullmatch(r"obsid=\d+", parts.query):
            return False
    elif parts.query:
        return False
    return any(
        parts.netloc == host and re.fullmatch(path, parts.path)
        for host, path in _PATHS.get(kind, ())
    )


def retrieve_fits(url, kind):
    if not trusted_fits_url(url, kind):
        raise ValueError("Unrecognized archive FITS locator")
    started = time.monotonic()
    data = io.BytesIO()
    with requests.get(
        url, stream=True, timeout=(5, 25), allow_redirects=False
    ) as response:
        if response.status_code != 200:
            raise ValueError(f"Archive returned HTTP {response.status_code}")
        for chunk in response.iter_content(256 * 1024):
            if data.tell() + len(chunk) > MAX_FITS_BYTES:
                raise ValueError("Archive FITS exceeds the download limit")
            if time.monotonic() - started > 45:
                raise ValueError("Archive FITS exceeded the download deadline")
            data.write(chunk)
    data.seek(0)
    return data


def points(wavelength, flux, good, label):
    wavelength, flux, good = (np.asarray(x).ravel() for x in (wavelength, flux, good))
    good &= (wavelength > 0) & np.isfinite(wavelength) & np.isfinite(flux)
    wavelength, flux = wavelength[good], flux[good]
    order = np.argsort(wavelength)
    if not len(order):
        return None
    return {
        "label": label,
        "wavelengths": wavelength[order].tolist(),
        "fluxes": flux[order].tolist(),
    }


def read_spectrum(hdus, kind, locator, url):
    if kind == "lamost":
        for ext in locator["extensions"]:
            data = hdus[ext].data
            good = data["IVAR"] > 0
            if "ANDMASK" in data.columns.names:
                good &= data["ANDMASK"] == 0
            yield points(data["WAVELENGTH"], data["FLUX"], good, ext)
    elif kind == "boss":
        data = hdus["COADD"].data
        yield points(
            10 ** data["LOGLAM"],
            data["FLUX"],
            (data["IVAR"] > 0) & (data["AND_MASK"] == 0),
            "Optical",
        )
    elif kind == "apogee":
        for chip in range(3):
            yield points(
                hdus["WAVELENGTH"].data[chip],
                hdus["FLUX"].data[chip],
                (hdus["MASK"].data[chip] == 0) & (hdus["ERROR"].data[chip] > 0),
                f"Chip {chip + 1}",
            )
    elif kind == "desi":
        target_id = int(locator["target_id"])
        target_rows = np.flatnonzero(hdus["FIBERMAP"].data["TARGETID"] == target_id)
        if len(target_rows) != 1:
            raise ValueError("DESI exposure does not uniquely identify the target")
        (index,) = target_rows
        yield points(
            hdus["WAVELENGTH"].data,
            hdus["FLUX"].data[index],
            (hdus["IVAR"].data[index] > 0) & (hdus["MASK"].data[index] == 0),
            urlsplit(url).path.rsplit("/", 1)[-1][7].upper(),
        )


@contextmanager
def open_archive_fits(data):
    if data.getbuffer()[:2] != b"\x1f\x8b":
        with fits.open(data, memmap=False) as hdus:
            yield hdus
        return
    with (
        gzip.GzipFile(fileobj=data) as compressed,
        SpooledTemporaryFile(max_size=8 * 1024 * 1024) as expanded,
    ):
        while chunk := compressed.read(256 * 1024):
            if expanded.tell() + len(chunk) > 2 * MAX_FITS_BYTES:
                raise ValueError("Expanded archive FITS exceeds the size limit")
            expanded.write(chunk)
        expanded.seek(0)
        with fits.open(expanded, memmap=False) as hdus:
            yield hdus


def fetch_spectrum(locator):
    kind = locator["format"]
    urls = locator["urls"] if kind == "desi" else [locator["url"]]
    if not _FITS_SLOTS.acquire(blocking=False):
        raise ValueError("Archive downloads are busy. Try again shortly.")
    try:
        data = []
        unavailable = 0
        for url in urls:
            try:
                with open_archive_fits(retrieve_fits(url, kind)) as hdus:
                    spectra = [
                        trace
                        for trace in read_spectrum(hdus, kind, locator, url)
                        if trace
                    ]
                    data.extend(spectra)
                    unavailable += not bool(spectra)
            except (EOFError, OSError, ValueError, KeyError, requests.RequestException):
                unavailable += 1
        if not data:
            raise ValueError("No usable spectrum could be loaded for this observation.")
        return {"traces": data, "unavailable": unavailable}
    finally:
        _FITS_SLOTS.release()
