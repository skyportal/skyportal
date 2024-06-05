import datetime

import numpy as np
from astroquery.jplhorizons import Horizons
from astropy.coordinates import SkyCoord
from astropy.time import Time
from tqdm import tqdm


def _get_object_positions(
    obj_name: str, start_date: str, end_date: str, time_step: str = "10m"
):
    obj = Horizons(
        id=obj_name,
        epochs={"start": start_date, "stop": end_date, "step": time_step},
    )
    try:
        eph = obj.ephemerides()
        pos = SkyCoord(eph["RA"], eph["DEC"], unit="deg")
        times = Time(np.asarray(eph["datetime_jd"]), format="jd", scale="utc")
        ra, dec, ra_error, dec_error, times = (
            np.asarray(pos.ra),
            np.asarray(pos.dec),
            np.asarray(eph['RA_3sigma'] / (3600 * 3)),
            np.asarray(eph['DEC_3sigma'] / (3600 * 3)),
            times,
        )
        del obj, eph, pos
    except Exception as e:
        print(f"(error: {str(e)})")
        ra, dec, ra_error, dec_error, times = (
            np.asarray([]),
            np.asarray([]),
            np.asarray([]),
            np.asarray([]),
            np.asarray([]),
        )

    return ra, dec, ra_error, dec_error, times


def get_object_positions(
    obj_name: str,
    start_date: datetime.datetime,
    end_date: datetime.datetime,
    time_step: str = "10m",
    verbose: bool = False,
):
    # here we make sure to batch the requests in start_date -> end_date windows
    # less than 1 year long to avoid timeouts
    date_diff = end_date - start_date
    if date_diff.days > 365:
        # split into smaller windows
        date_windows = []
        for i in range(date_diff.days // 365 + 1):
            date_windows.append(
                (
                    start_date + datetime.timedelta(days=i * 365),
                    start_date + datetime.timedelta(days=(i + 1) * 365),
                )
            )
    else:
        date_windows = [(start_date, end_date)]

    ra, dec, ra_error, dec_error, times = [], [], [], [], []
    for date_window in tqdm(
        date_windows,
        desc=f"Fetching {obj_name} positions (batched per year if needed)",
        disable=not verbose,
    ):
        ra_, dec_, ra_error_, dec_error_, times_ = _get_object_positions(
            obj_name=obj_name,
            start_date=date_window[0].strftime("%Y-%m-%d"),
            end_date=date_window[1].strftime("%Y-%m-%d"),
            time_step=time_step,
        )
        ra.extend(list(ra_))
        dec.extend(list(dec_))
        ra_error.extend(list(ra_error_))
        dec_error.extend(list(dec_error_))
        times.extend(list(times_))

    return {
        "ra": ra,
        "dec": dec,
        "ra_err": ra_error,
        "dec_err": dec_error,
        "mjd": [t.mjd for t in times],
    }
