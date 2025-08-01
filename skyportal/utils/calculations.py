import astroplan
import astropy_healpix as ahp
import numpy as np
import pandas as pd
from astropy import units as u
from astropy.coordinates import SkyCoord
from astropy.time import Time
from scipy.optimize import fsolve

# Rotation matrix for the conversion : x_galactic = R * x_equatorial (J2000)
# http://adsabs.harvard.edu/abs/1989A&A...218..325M
RGE = np.array(
    [
        [-0.054875539, -0.873437105, -0.483834992],
        [+0.494109454, -0.444829594, +0.746982249],
        [-0.867666136, -0.198076390, +0.455983795],
    ]
)


def radec_str2deg(_ra_str, _dec_str):
    """
    Convert R.A. and Decl. from string to degrees

    Parameters
    ----------
    _ra_str : str
        Right Ascension in the format 'hh:mm:ss.sss'
    _dec_str : str
        Declination in the format 'dd:mm:ss.sss'

    Returns
    -------
    ra : float
        Right Ascension in degrees
    dec : float
        Declination in degrees
    """
    c = SkyCoord(_ra_str, _dec_str, unit=(u.hourangle, u.deg))
    return c.ra.deg, c.dec.deg


def great_circle_distance(ra1_deg, dec1_deg, ra2_deg, dec2_deg):
    """
        Distance between two points on the sphere
    :param ra1_deg:
    :param dec1_deg:
    :param ra2_deg:
    :param dec2_deg:
    :return: distance in degrees
    """
    # this is orders of magnitude faster than astropy.coordinates.Skycoord.separation
    DEGRA = np.pi / 180.0
    ra1, dec1, ra2, dec2 = (
        ra1_deg * DEGRA,
        dec1_deg * DEGRA,
        ra2_deg * DEGRA,
        dec2_deg * DEGRA,
    )
    delta_ra = np.abs(ra2 - ra1)
    distance = np.arctan2(
        np.sqrt(
            (np.cos(dec2) * np.sin(delta_ra)) ** 2
            + (
                np.cos(dec1) * np.sin(dec2)
                - np.sin(dec1) * np.cos(dec2) * np.cos(delta_ra)
            )
            ** 2
        ),
        np.sin(dec1) * np.sin(dec2) + np.cos(dec1) * np.cos(dec2) * np.cos(delta_ra),
    )

    return distance * 180.0 / np.pi


# Vectorize the function
great_circle_distance_vec = np.vectorize(great_circle_distance)


def get_observer(telescope: dict):
    """Return an `astroplan.Observer` representing an observer at this
    facility, accounting for the latitude, longitude, and elevation."""

    return astroplan.Observer(
        longitude=telescope["lon"] * u.deg,
        latitude=telescope["lat"] * u.deg,
        elevation=telescope["elevation"] * u.m,
    )


def get_target(fields: list[dict]):
    """Return an `astroplan.FixedTarget` representing the target of this
    observation.

    Parameters
    ----------
    fields : list of dict
        The fields to get the target from.

    Returns
    -------
    target : `astroplan.FixedTarget`
        The target of the observation.
    """
    ra = np.array([field["ra"] for field in fields])
    dec = np.array([field["dec"] for field in fields])
    field_ids = np.array([field["field_id"] for field in fields])
    return astroplan.FixedTarget(
        SkyCoord(ra=ra * u.deg, dec=dec * u.deg), name=field_ids
    )


def get_altitude(
    time: np.ndarray, target: astroplan.FixedTarget, observer: astroplan.Observer
):
    """Return the altitude of the object at a given time.

    Parameters
    ----------
    time : `astropy.time.Time`
        The time or times at which to calculate the altitude

    Returns
    -------
    alt : `astropy.coordinates.AltAz`
        The altitude of the Obj at the requested times
    """
    time = np.atleast_1d(time)
    return observer.altaz(time, target, grid_times_targets=True).alt


def get_altitude_from_airmass(airmass: float):
    """Return the altitude of the object at a given time.

    Parameters
    ----------
    airmass: float
        The airmass values for which to calculate the altitude

    Returns
    -------
    altitude : float
        The altitudes corresponding to the airmass values in degrees
    """

    def f(a):
        return a + 244 / (165 + 47 * a**1.1) - np.degrees(np.arcsin(1 / airmass))

    estimation = np.degrees(np.arcsin(1 / airmass))
    altitude = fsolve(f, estimation)

    return altitude[0]


def get_airmass(fields: list, time: np.ndarray, below_horizon=np.inf, **kwargs):
    """Return the airmass of the field at a given time. Uses the Pickering
    (2002) interpolation of the Rayleigh (molecular atmosphere) airmass.

    The Pickering interpolation tends toward 38.7494 as the altitude
    approaches zero.

    Parameters
    ----------
    fields : list of dict
        The fields to calculate the airmass for. Each field is a dict
        with keys 'ra','dec' and 'field_id'.
    time : `astropy.time.Time` or list of astropy.time.Time`
        The time or times at which to calculate the airmass
    below_horizon : scalar, Numeric
        Airmass value to assign when an object is below the horizon.
        An object is "below the horizon" when its altitude is less than
        zero degrees.
    observer : `astroplan.Observer`
        The observer for which to calculate the airmass. If not
        provided, provide a telescope instead.
    telescope: dict
        The telescope for which to calculate the airmass. If not
        provided, provide an observer instead.

    Returns
    -------
    airmass : ndarray
        The airmass of the Obj at the requested times
    """

    if "observer" in kwargs:
        observer = kwargs["observer"]
    elif "telescope" in kwargs:
        observer = get_observer(kwargs["telescope"])

    # the output shape should be targets x times
    output_shape = (len(fields), len(time))
    time = np.atleast_1d(time)
    target = get_target(fields)
    altitude = get_altitude(time, target, observer).to("degree").value
    above = altitude > 0

    # use Pickering (2002) interpolation to calculate the airmass
    # The Pickering interpolation tends toward 38.7494 as the altitude
    # approaches zero.
    sinarg = np.zeros_like(altitude)
    airmass = np.ones_like(altitude) * np.inf
    sinarg[above] = altitude[above] + 244 / (165 + 47 * altitude[above] ** 1.1)
    airmass[above] = 1.0 / np.sin(np.deg2rad(sinarg[above]))

    # set objects below the horizon to an airmass of infinity
    airmass[~above] = below_horizon
    airmass = airmass.reshape(output_shape)

    return airmass


def fix_sun_time_calculation_error(
    function, time, which="nearest", horizon=0 * u.degree, n_grid_points=150
):
    # Fix an Astroplan issue where sunset or sunrise calculation sometimes fails when the time is near
    try:
        result = None
        for i in range(60):
            result = function(
                time + (i * u.minute),
                which=which,
                horizon=horizon,
                n_grid_points=n_grid_points,
            )
            if result and not result.masked:
                break
        if result and not result.masked:
            return result
    except Exception:
        pass

    raise RuntimeError(
        f"{function.__name__} calculation failed because of astroplan behavior"
    )


def get_rise_set_time(target, altitude=30 * u.degree, **kwargs):
    """The rise and set times of the target at the given altitude as an astropy.time.Time.

    Parameters
    ----------
    target : `astroplan.FixedTarget`
        The target of the observation.
    altitude : `astropy.units.Quantity`
        The altitude at which to calculate the rise and set times.
    kwargs : dict
        Additional keyword arguments:

        observer : `astroplan.Observer`
            The observer for which to calculate the rise and set times.
        time : `astropy.time.Time`
            The time at which to calculate the rise and set times.
        night_only : bool
            If True, calculate the rise and set times when the target is visible during the night only.
        sun_altitude : `astropy.units.Quantity`
            The altitude of the sun below which it is considered to be the night.

    Returns
    -------
    rise_time : `astropy.time.Time`
        The rise time of the target at the given altitude.
    set_time : `astropy.time.Time`
        The set time of the target at the given altitude.
    """
    observer = kwargs.get("observer", kwargs.get("telescope"))
    if observer is None:
        raise ValueError("Missing telescope or observer information")

    time = kwargs.get("time", Time.now())

    # The altitude of the sun below which it is considered to be the night
    sun_altitude = kwargs.get("sun_altitude", -18 * u.degree)

    sunset = fix_sun_time_calculation_error(
        observer.sun_set_time, time=time, which="next", horizon=sun_altitude
    )
    sunrise = fix_sun_time_calculation_error(
        observer.sun_rise_time, time=time, which="next", horizon=sun_altitude
    )

    # If the sunset is after the sunrise, use the previous sunset
    recalc = sunset > sunrise
    if np.any(recalc):
        sunset[recalc] = fix_sun_time_calculation_error(
            observer.sun_set_time, time=time, which="previous", horizon=sun_altitude
        )[recalc]

    rise_time = observer.target_rise_time(
        sunset, target, which="next", horizon=altitude
    )
    set_time = observer.target_set_time(sunset, target, which="next", horizon=altitude)

    # Check if the rise or set times are None (masked)
    if rise_time.masked or set_time.masked:
        return None, None

    recalc = set_time < rise_time
    if np.any(recalc):
        rise_time[recalc] = observer.target_rise_time(
            sunset, target, which="previous", horizon=altitude
        )[recalc]

    if kwargs.get("night_only", False):
        # set the rise time to the sunset time if the rise time is during the day
        rise_time_during_day = rise_time < sunset
        if np.any(rise_time_during_day):
            rise_time = np.where(rise_time_during_day, sunset, rise_time)

        # set the set time to the sunrise time if the set time is during the day
        set_time_during_day = sunrise < set_time
        if np.any(set_time_during_day):
            set_time = np.where(set_time_during_day, sunrise, set_time)

        # set time to None if rise is after set time, meaning the target is not visible during the night
        no_time_during_night = set_time < rise_time
        if np.any(no_time_during_night):
            rise_time = np.where(no_time_during_night, None, rise_time)
            set_time = np.where(no_time_during_night, None, set_time)

    if isinstance(rise_time, np.ndarray) and rise_time.size == 1:
        rise_time = rise_time.item()
    if isinstance(set_time, np.ndarray) and set_time.size == 1:
        set_time = set_time.item()

    return rise_time, set_time


def get_next_valid_observing_time(
    start_time, end_time, telescope, target, airmass, observe_at_optimal_airmass=False
):
    """Return the next valid observing time for the given telescope and target at the given airmass limit.
    Use the nearest time or the time with the optimal airmass.

    Parameters
    ----------
    start_time : astropy.time.Time
        The start time from which to calculate the next valid observing time.
    end_time : astropy.time.Time
        The end time until which to calculate the next valid observing time.
    telescope : `skyportal.models.Telescope`
        The telescope for which to calculate the next valid observing time.
    target : `astroplan.FixedTarget`
        The target of the observation.
    airmass : float
        The airmass limit for the observation.
    observe_at_optimal_airmass : bool
        If True, use the date at the best airmass limit else use the nearest date.

    Returns
    -------
    next_observing_date : `astropy.time.Time`
        The next valid observing date for the given telescope and target at the given airmass limit.
    """
    observing_time = Time.now() if start_time < Time.now() else start_time
    altitude_limit = get_altitude_from_airmass(airmass)

    if telescope.observer is None:
        raise ValueError("Missing some telescope information")

    valid_rise_time, valid_set_time = None, None
    for _ in range(14):  # Try 7 days, checking every 12 hours
        # Retrieve the rise and set time of the target within the nighttime observing window
        valid_rise_time, valid_set_time = get_rise_set_time(
            target=target,
            altitude=altitude_limit * u.degree,
            observer=telescope.observer,
            time=observing_time,
            night_only=True,
        )

        if valid_rise_time and valid_set_time and observing_time < valid_set_time:
            break
        else:
            # if the target is not visible, use the next 12 hours as the new observing time
            observing_time += 12 * u.hour
            if end_time < observing_time:
                break

    if not valid_rise_time or not valid_set_time:
        raise ValueError(
            "No valid observing time found in the range (limited to 7 days)"
        )

    if observe_at_optimal_airmass:
        # Retrieve the real rise and set time to calculate the optimal airmass time
        rise_time, set_time = get_rise_set_time(
            target=target,
            altitude=altitude_limit * u.degree,
            observer=telescope.observer,
            time=observing_time,
            night_only=False,
        )
        optimal_airmass_time = Time((rise_time.unix + set_time.unix) / 2, format="unix")
        if valid_rise_time < optimal_airmass_time < valid_set_time:
            valid_rise_time = optimal_airmass_time

    if valid_rise_time < start_time:
        return start_time

    return valid_rise_time


def next_sunrise(observer, time=None):
    """The astropy timestamp of the next sunrise after `time` at this site.
    If time=None, uses the current time."""
    if observer is None:
        return None
    if time is None:
        time = Time.now()
    return observer.sun_rise_time(time, which="next")


def deg2hms(x):
    """Transform degrees to *hours:minutes:seconds* strings.

    Parameters
    ----------
    x : float
        The degree value c [0, 360) to be written as a sexagesimal string.

    Returns
    -------
    out : str
        The input angle written as a sexagesimal string, in the
        form, hours:minutes:seconds.

    """
    if not 0.0 <= x < 360.0:
        raise ValueError("Bad RA value in degrees")
    _h = np.floor(x * 12.0 / 180.0)
    _m = np.floor((x * 12.0 / 180.0 - _h) * 60.0)
    _s = ((x * 12.0 / 180.0 - _h) * 60.0 - _m) * 60.0
    hms = f"{_h:02.0f}:{_m:02.0f}:{_s:07.4f}"
    return hms


def deg2dms(x):
    """Transform degrees to *degrees:arcminutes:arcseconds* strings.

    Parameters
    ----------
    x : float
        The degree value c [-90, 90] to be converted.

    Returns
    -------
    out : str
        The input angle as a string, written as degrees:minutes:seconds.

    """
    if not -90.0 <= x <= 90.0:
        raise ValueError("Bad Dec value in degrees")
    _d = np.floor(abs(x)) * np.sign(x)
    _m = np.floor(np.abs(x - _d) * 60.0)
    _s = np.abs(np.abs(x - _d) * 60.0 - _m) * 60.0
    dms = f"{_d:02.0f}:{_m:02.0f}:{_s:06.3f}"
    return dms


def radec2lb(ra, dec):
    """
        Convert $R.A.$ and $Decl.$ into Galactic coordinates $l$ and $b$
    ra [deg]
    dec [deg]

    return l [deg], b [deg]
    """
    ra_rad, dec_rad = np.deg2rad(ra), np.deg2rad(dec)
    u = np.array(
        [
            np.cos(ra_rad) * np.cos(dec_rad),
            np.sin(ra_rad) * np.cos(dec_rad),
            np.sin(dec_rad),
        ]
    )

    ug = np.dot(RGE, u)

    x, y, z = ug
    galactic_l = np.arctan2(y, x)
    galactic_b = np.arctan2(z, (x * x + y * y) ** 0.5)
    return np.rad2deg(galactic_l), np.rad2deg(galactic_b)


def hms_to_deg(input):
    """
    Convert hours, minutes, seconds to decimal degrees.

    Parameters
    ----------
    h : float
        Hours
    m : float
        Minutes
    s : float
        Seconds

    Returns
    -------
    float
        Decimal degrees
    """
    h, m, s = input.split(" ")
    h, m, s = float(h), float(m), float(s)
    return 15 * (h + m / 60 + s / 3600)  # Multiply by 15 to convert hours to degrees


def dms_to_deg(input):
    """
    Convert degrees, arcminutes, arcseconds to decimal degrees.

    Parameters
    ----------
    d : float
        Degrees
    m : float
        Arcminutes
    s : float
        Arcseconds

    Returns
    -------
    float
        Decimal degrees
    """
    d, m, s = input.split(" ")
    d, m, s = float(d), float(m), float(s)
    sign = 1 if d >= 0 else -1
    return sign * (abs(d) + m / 60 + s / 3600)


def radec_to_healpix(row: dict | pd.Series) -> int:
    """
    Convert R.A. and Decl. to HEALPix index.

    Parameters
    ----------
    row : dict or pd.Series
        Dictionary or pandas Series containing "ra" and "dec" keys or columns.

    Returns
    -------
    int
        HEALPix index
    """
    return ahp.lonlat_to_healpix(row["ra"] * u.deg, row["dec"] * u.deg, 2**29)
