import astroplan
import numpy as np
from astropy import units as u
from astropy.coordinates import SkyCoord
from astropy.time import Time


def radec_str2deg(_ra_str, _dec_str):
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


def get_observer(telescope: dict):
    """Return an `astroplan.Observer` representing an observer at this
    facility, accounting for the latitude, longitude, and elevation."""

    return astroplan.Observer(
        longitude=telescope['lon'] * u.deg,
        latitude=telescope['lat'] * u.deg,
        elevation=telescope['elevation'] * u.m,
    )


def get_target(fields: list[dict]):
    """Return an `astroplan.FixedTarget` representing the target of this
    observation."""
    ra = np.array([field['ra'] for field in fields])
    dec = np.array([field['dec'] for field in fields])
    field_ids = np.array([field['field_id'] for field in fields])
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

    if 'observer' in kwargs:
        observer = kwargs['observer']
    elif 'telescope' in kwargs:
        observer = observer(kwargs['telescope'])

    # the output shape should be targets x times
    output_shape = (len(fields), len(time))
    time = np.atleast_1d(time)
    target = get_target(fields)
    altitude = get_altitude(time, target, observer).to('degree').value
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


def get_rise_set_time(fields, altitude=30 * u.degree, **kwargs):
    """The set time of the field as an astropy.time.Time."""
    if 'observer' in kwargs:
        observer = kwargs['observer']
    elif 'telescope' in kwargs:
        observer = get_observer(kwargs['telescope'])

    if 'time' in kwargs:
        time = kwargs['time']
    else:
        time = Time.now()

    sunrise = observer.sun_rise_time(time, which='next')
    sunset = observer.sun_set_time(time, which='next')

    targets = get_target(fields)

    rise_time = observer.target_rise_time(
        sunset, targets, which='next', horizon=altitude
    )
    set_time = observer.target_set_time(sunset, targets, which='next', horizon=altitude)

    # if next rise time is after next sunrise, the target rises before
    # sunset. show the previous rise so that the target is shown to be
    # "already up" when the run begins (a beginning of night target).

    recalc = rise_time > sunrise

    if np.any(recalc):
        # recalculate the rise time only for those targets that need it
        rise_time[recalc] = observer.target_rise_time(
            sunset, targets, which='previous', horizon=altitude
        )[recalc]

    return rise_time, set_time


def next_sunrise(observer, time=None):
    """The astropy timestamp of the next sunrise after `time` at this site.
    If time=None, uses the current time."""
    if observer is None:
        return None
    if time is None:
        time = Time.now()
    return observer.sun_rise_time(time, which='next')


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
