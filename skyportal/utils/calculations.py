import numpy as np


def radec_str2deg(_ra_str, _dec_str):
    """
    :param _ra_str: 'H:M:S'
    :param _dec_str: 'D:M:S'
    :return: ra, dec in deg
    """
    # convert to rad:
    _ra = list(map(float, _ra_str.split(":")))
    _ra = _ra[0] + _ra[1] / 60.0 + _ra[2] / 3600.0
    _dec = list(map(float, _dec_str.split(":")))
    _sign = -1 if _dec_str.strip()[0] == "-" else 1
    _dec = _sign * (abs(_dec[0]) + abs(_dec[1]) / 60.0 + abs(_dec[2]) / 3600.0)

    return _ra, _dec


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
