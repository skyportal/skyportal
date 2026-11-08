import re
from datetime import UTC, datetime, timedelta

import astropy.units as u
import numpy as np
from astropy.coordinates import SkyCoord
from astropy.io import fits
from astropy.time import Time

COLUMNS = [
    "fileSetName",
    "instrume",
    "exp_type",
    "access",
    "program",
    "targ_ra",
    "targ_dec",
    "s_region",
    "expmid",
]

OBSERVATION_DATASET = re.compile(r"^jw\d{5}-o\d{3}_")
NUMBER = re.compile(r"[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?")

DO_NOT_USE = 1


def recent_datasets(missions, look_back_days, exp_types):
    now = datetime.now(UTC)
    since = f"{now - timedelta(days=look_back_days):%Y-%m-%d}"
    until = f"{now + timedelta(days=1):%Y-%m-%d}"
    datasets = {}
    for criteria in (
        {"date_obs": f">{since}"},
        {"publicReleaseDate": f"{since}..{until}"},
    ):
        table = missions.query_criteria(
            productLevel="3",
            exp_type=",".join(exp_types),
            select_cols=COLUMNS,
            **criteria,
        )
        for row in table or []:
            name = str(row["fileSetName"])
            if OBSERVATION_DATASET.match(name):
                datasets[name] = {
                    column: None if np.ma.is_masked(row[column]) else row[column]
                    for column in COLUMNS
                }
    return list(datasets.values())


def dataset_position(dataset):
    region = str(dataset["s_region"])
    if region.upper().startswith("POLYGON"):
        values = np.array(NUMBER.findall(region), dtype=float)
        if values.size >= 6 and values.size % 2 == 0:
            ra, dec = np.radians(values[0::2]), np.radians(values[1::2])
            x = np.mean(np.cos(dec) * np.cos(ra))
            y = np.mean(np.cos(dec) * np.sin(ra))
            z = np.mean(np.sin(dec))
            return (
                float(np.degrees(np.arctan2(y, x)) % 360),
                float(np.degrees(np.arctan2(z, np.hypot(x, y)))),
            )
    return float(dataset["targ_ra"]), float(dataset["targ_dec"])


def _label(header):
    if header.get("GRATING"):
        return f"{header['GRATING']}/{header.get('FILTER', '')}".rstrip("/")
    if header.get("CHANNEL"):
        return f"ch{header['CHANNEL']}-{str(header.get('BAND', '')).lower()}"
    return header.get("FILTER")


def read_x1d(path, ra, dec, radius_arcsec, default_mjd=None):
    spectra = []
    with fits.open(path) as hdul:
        header = hdul[0].header
        mjd = header.get("EXPMID", default_mjd)
        if mjd is None:
            return spectra
        observed_at = Time(float(mjd), format="mjd").datetime
        for hdu in hdul:
            if hdu.name != "EXTRACT1D":
                continue
            slit_ra, slit_dec = hdu.header.get("SLIT_RA"), hdu.header.get("SLIT_DEC")
            if slit_ra is not None and slit_dec is not None:
                separation = SkyCoord(ra, dec, unit="deg").separation(
                    SkyCoord(slit_ra, slit_dec, unit="deg")
                )
                if separation.arcsec > radius_arcsec:
                    continue
            columns = hdu.columns
            if u.Unit(columns["FLUX"].unit) != u.Jy:
                continue
            data = hdu.data
            wavelengths = (
                np.asarray(data["WAVELENGTH"], dtype=float)
                * u.Unit(columns["WAVELENGTH"].unit)
            ).to_value(u.AA)
            fluxes = np.asarray(data["FLUX"], dtype=float)
            errors = np.asarray(data["FLUX_ERROR"], dtype=float)
            good = np.isfinite(wavelengths) & np.isfinite(fluxes) & np.isfinite(errors)
            if "DQ" in columns.names:
                good &= (np.asarray(data["DQ"]).astype(int) & DO_NOT_USE) == 0
            if good.sum() < 2:
                continue
            order = np.argsort(wavelengths[good])
            spectra.append(
                {
                    "wavelengths": wavelengths[good][order].tolist(),
                    "fluxes": fluxes[good][order].tolist(),
                    "errors": errors[good][order].tolist(),
                    "units": "Jy",
                    "observed_at": observed_at,
                    "label": _label(header),
                }
            )
    return spectra
