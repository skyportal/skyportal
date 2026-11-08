import re
from datetime import UTC, datetime, timedelta

import astropy.units as u
import numpy as np
from astropy.coordinates import SkyCoord
from astropy.io import fits
from astropy.time import Time

JWST_COLUMNS = [
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

HST_COLUMNS = [
    "sci_data_set_name",
    "sci_instrume",
    "sci_pep_id",
    "sci_ra",
    "sci_dec",
    "sci_start_time",
    "sci_stop_time",
    "sci_status",
]

HST_PRODUCTS = ("x1dsum", "sx1", "x1d")
INSTRUMENT_TNS_IDS = {"NIRSPEC": 186, "MIRI": 188, "STIS": 83}
F_LAMBDA = u.erg / u.s / u.cm**2 / u.AA

OBSERVATION_DATASET = re.compile(r"^jw\d{5}-o\d{3}_")
NUMBER = re.compile(r"[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?")

DO_NOT_USE = 1


def _window(look_back_days):
    now = datetime.now(UTC)
    return (
        f"{now - timedelta(days=look_back_days):%Y-%m-%d}",
        f"{now + timedelta(days=1):%Y-%m-%d}",
    )


def _rows(table, columns):
    for row in table or []:
        yield {
            column: None if np.ma.is_masked(row[column]) else row[column]
            for column in columns
        }


def recent_jwst_datasets(missions, look_back_days, exp_types):
    since, until = _window(look_back_days)
    datasets = {}
    for criteria in (
        {"date_obs": f">{since}"},
        {"publicReleaseDate": f"{since}..{until}"},
    ):
        table = missions.query_criteria(
            productLevel="3",
            exp_type=",".join(exp_types),
            select_cols=JWST_COLUMNS,
            **criteria,
        )
        for row in _rows(table, JWST_COLUMNS):
            name = str(row["fileSetName"])
            if OBSERVATION_DATASET.match(name):
                ra, dec = dataset_position(row)
                datasets[name] = {
                    "mission": "jwst",
                    "name": name,
                    "instrument": str(row["instrume"]).upper(),
                    "program": str(row["program"]),
                    "ra": ra,
                    "dec": dec,
                    "mjd": row["expmid"],
                    "public": row["access"] == "PUBLIC",
                }
    return list(datasets.values())


def recent_hst_datasets(missions, look_back_days, instruments):
    since, until = _window(look_back_days)
    datasets = {}
    for criteria in (
        {"sci_start_time": f">{since}"},
        {"sci_release_date": f"{since}..{until}"},
    ):
        table = missions.query_criteria(
            sci_instrume=",".join(instruments),
            sci_obs_type="SPECTRUM",
            sci_aec="S",
            select_cols=HST_COLUMNS,
            **criteria,
        )
        for row in _rows(table, HST_COLUMNS):
            name = str(row["sci_data_set_name"])
            start, stop = Time([row["sci_start_time"], row["sci_stop_time"]]).mjd
            datasets[name] = {
                "mission": "hst",
                "name": name,
                "instrument": str(row["sci_instrume"]).strip().upper(),
                "program": str(row["sci_pep_id"]),
                "ra": float(row["sci_ra"]),
                "dec": float(row["sci_dec"]),
                "mjd": (start + stop) / 2,
                "public": row["sci_status"] == "PUBLIC",
            }
    return list(datasets.values())


def spectrum_products(products, dataset):
    if dataset["mission"] == "jwst":
        return [p for p in products if str(p["filename"]).endswith("_x1d.fits")]
    by_name = {str(p["filename"]): p for p in products}
    for suffix in HST_PRODUCTS:
        product = by_name.get(f"{dataset['name'].lower()}_{suffix}.fits")
        if product is not None:
            return [product]
    return []


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


def read_jwst_x1d(path, ra, dec, radius_arcsec, default_mjd=None):
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


def read_hst_x1d(path, mjd):
    wavelengths, fluxes, errors = [], [], []
    with fits.open(path) as hdul:
        header = hdul[0].header
        for hdu in hdul:
            if hdu.name != "SCI" or not isinstance(hdu, fits.BinTableHDU):
                continue
            columns = hdu.columns
            if u.Unit(columns["FLUX"].unit, parse_strict="silent") != F_LAMBDA:
                continue
            data = hdu.data
            wavelength = np.asarray(data["WAVELENGTH"], dtype=float).ravel()
            flux = np.asarray(data["FLUX"], dtype=float).ravel()
            error = np.asarray(data["ERROR"], dtype=float).ravel()
            good = (
                np.isfinite(wavelength)
                & (wavelength > 0)
                & np.isfinite(flux)
                & np.isfinite(error)
            )
            if "DQ_WGT" in columns.names:
                good &= np.asarray(data["DQ_WGT"], dtype=float).ravel() > 0
            elif "DQ" in columns.names and "SDQFLAGS" in hdu.header:
                good &= (
                    np.asarray(data["DQ"]).astype(int).ravel()
                    & int(hdu.header["SDQFLAGS"])
                ) == 0
            wavelengths.append(wavelength[good])
            fluxes.append(flux[good])
            errors.append(error[good])
    if not wavelengths or sum(len(w) for w in wavelengths) < 2:
        return []
    wavelengths = np.concatenate(wavelengths)
    order = np.argsort(wavelengths)
    return [
        {
            "wavelengths": wavelengths[order].tolist(),
            "fluxes": np.concatenate(fluxes)[order].tolist(),
            "errors": np.concatenate(errors)[order].tolist(),
            "units": "erg/s/cm/cm/AA",
            "observed_at": Time(mjd, format="mjd").datetime,
            "label": "/".join(
                str(header[key])
                for key in ("OPT_ELEM", "CENWAVE")
                if header.get(key) not in (None, "")
            ),
        }
    ]
