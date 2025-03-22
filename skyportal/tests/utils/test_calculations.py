import numpy as np
from astropy import units as u
from astropy.time import Time

from skyportal.utils.calculations import (
    deg2dms,
    deg2hms,
    dms_to_deg,
    get_airmass,
    get_altitude,
    get_altitude_from_airmass,
    get_next_valid_observing_time,
    get_observer,
    get_rise_set_time,
    get_target,
    great_circle_distance,
    great_circle_distance_vec,
    hms_to_deg,
    next_sunrise,
    radec2lb,
    radec_str2deg,
    radec_to_healpix,
)


def test_radec_str2deg():
    ra_str, dec_str = "15:25:39.30", "+17:40:50.39"
    ra, dec = radec_str2deg(ra_str, dec_str)
    assert np.isclose(ra, 231.413765)
    assert np.isclose(dec, 17.680664)


def test_deg2hms():
    assert deg2hms(231.413765) == "15:25:39.3036"


def test_deg2dms():
    assert deg2dms(17.680664) == "17:40:50.390"


def test_hms_to_deg():
    assert np.isclose(hms_to_deg("15 25 39.3036"), 231.413765)


def test_dms_to_deg():
    assert np.isclose(dms_to_deg("+17 40 50.390"), 17.680664)


def test_radec_to_healpix():
    row = {"ra": 231.413765, "dec": 17.680664}
    assert radec_to_healpix(row) == 1204148902702861198


def test_radec2lb():
    ra, dec = 231.413765, 17.680664
    l, b = radec2lb(ra, dec)
    assert np.isclose(l, 26.261747)
    assert np.isclose(b, 53.283117)


def test_great_circle_distance():
    ra1, dec1 = 30, 45
    ra2, dec2 = 31, 44
    assert np.isclose(great_circle_distance(ra1, dec1, ra2, dec2), 1.228279093463769)


def test_great_circle_distance_vec():
    ra1, dec1 = [30, 31], [45, 44]
    ra2, dec2 = [31, 32], [44, 43]
    assert np.allclose(
        great_circle_distance_vec(ra1, dec1, ra2, dec2), [1.22827909, 1.23535914]
    )


def test_get_observer():
    telescope = {"lon": 30, "lat": 45, "elevation": 100}
    observer = get_observer(telescope)
    assert np.isclose(observer.location.lon.deg, 30)
    assert np.isclose(observer.location.lat.deg, 45)
    assert np.isclose(observer.location.height.value, 100)


def test_get_target():
    fields = [
        {"ra": 30, "dec": 45, "field_id": 1},
        {"ra": 31, "dec": 44, "field_id": 2},
    ]
    target = get_target(fields)
    assert np.allclose(target.ra.deg, [30, 31])
    assert np.allclose(target.dec.deg, [45, 44])
    assert np.allclose(target.name, [1, 2])


def test_get_altitude():
    fields = [
        {"ra": 30, "dec": 45, "field_id": 1},
        {"ra": 145, "dec": 45, "field_id": 2},
    ]
    target = get_target(fields)
    observer = get_observer({"lon": 30, "lat": 45, "elevation": 100})
    # check at 2024-01-01 00:00:00
    time = Time("2024-01-01 00:00:00")
    altitude = get_altitude(time, target, observer)
    assert np.isclose(altitude.deg[0], 24.60195713)
    assert np.isclose(altitude.deg[1], 79.22992432)


def test_get_airmass():
    fields = [
        {"ra": 30, "dec": 45, "field_id": 1},
        {"ra": 145, "dec": 45, "field_id": 2},
    ]
    observer = get_observer({"lon": 30, "lat": 45, "elevation": 100})
    # check at 2024-01-01 00:00:00
    time = Time(["2024-01-01 00:00:00"])
    airmass = get_airmass(fields, time, observer=observer)
    assert np.isclose(airmass[0, 0], 2.3894099051129727)
    assert np.isclose(airmass[1, 0], 1.0177921215801056)


def test_get_altitude_from_airmass():
    fields = [
        {"ra": 30, "dec": 45, "field_id": 1},
        {"ra": 145, "dec": 45, "field_id": 2},
    ]
    time = Time(["2024-01-01 00:00:00"])
    target = get_target(fields)
    observer = get_observer({"lon": 30, "lat": 45, "elevation": 100})
    altitude = get_altitude(time, target, observer)
    assert np.isclose(altitude.deg[0], 24.60195713)
    assert np.isclose(altitude.deg[1], 79.22992432)

    airmass = get_airmass(fields, time, observer=observer)
    assert np.isclose(airmass[0, 0], 2.3894099051129727)
    assert np.isclose(airmass[1, 0], 1.0177921215801056)

    assert np.isclose(get_altitude_from_airmass(airmass[0, 0]), 24.60195713)
    assert np.isclose(get_altitude_from_airmass(airmass[1, 0]), 79.22992432)


def test_get_rise_set_time():
    fields = [
        {"ra": 30, "dec": 45, "field_id": 1},
        {"ra": 145, "dec": 45, "field_id": 2},
    ]
    target = get_target(fields)
    observer = get_observer({"lon": 30, "lat": 45, "elevation": 100})
    # check at 2024-01-01 00:00:00
    time = Time("2024-01-01 00:00:00")
    rise_time, set_time = get_rise_set_time(target, observer=observer, time=time)
    assert np.isclose(rise_time[0].unix, 1704107913.0)
    assert np.isclose(rise_time[1].unix, 1704049332.37)
    assert np.isclose(set_time[0].unix, 1704151053.54)
    assert np.isclose(set_time[1].unix, 1704178526.59)

    target = get_target([{"ra": 30, "dec": 45, "field_id": 1}])
    altitude = get_altitude_from_airmass(3.0)
    assert np.isclose(altitude, 19.29494943)
    rise_time, set_time = get_rise_set_time(
        target, altitude=altitude * u.deg, observer=observer, time=time
    )
    assert np.isclose(
        rise_time.unix, Time("2024-01-01 09:59:14").unix, atol=1, rtol=1e-10
    )  # tolerance is 1 second
    assert np.isclose(
        set_time.unix, Time("2024-01-02 00:36:51").unix, atol=1, rtol=1e-10
    )  # tolerance is 1 second

    altitude = get_altitude_from_airmass(2.0)
    assert np.isclose(altitude, 29.88587059)
    rise_time, set_time = get_rise_set_time(
        target, altitude=altitude * u.deg, observer=observer, time=time
    )
    assert np.isclose(
        rise_time.unix, Time("2024-01-01 11:17:45").unix, atol=1, rtol=1e-10
    )  # tolerance is 1 second
    assert np.isclose(
        set_time.unix, Time("2024-01-01 23:18:21").unix, atol=1, rtol=1e-10
    )  # tolerance is 1 second


def test_get_next_observing_date():
    fields = [
        {"ra": 30, "dec": 45, "field_id": 1},
    ]
    target = get_target(fields)
    telescope = {"lon": 30, "lat": 45, "elevation": 100}
    observer = get_observer(telescope)
    time = Time.now()

    altitude = get_altitude_from_airmass(3.0)
    assert np.isclose(altitude, 19.29494943)

    rise_time, set_time = get_rise_set_time(
        target, altitude=altitude * u.deg, observer=observer, time=time
    )

    next_valid_observing_time = get_next_valid_observing_time(
        start_time=time,
        telescope=telescope,
        target=target,
        airmass=3.0,
        observe_at_optimal_airmass=False,
    )
    if rise_time > time:
        assert np.isclose(
            next_valid_observing_time.unix, rise_time.unix, atol=1, rtol=1e-10
        )  # tolerance is 1 second
        assert np.isclose(
            get_airmass(
                fields, np.array([next_valid_observing_time]), observer=observer
            ),
            3.00,
            atol=1e-2,
        )
    else:
        assert np.isclose(
            next_valid_observing_time.unix, time.unix, atol=1, rtol=1e-10
        )  # tolerance is 1 second

    next_valid_observing_time = get_next_valid_observing_time(
        start_time=time,
        telescope=telescope,
        target=target,
        airmass=3.0,
        observe_at_optimal_airmass=True,
    )
    optimal_time = Time((rise_time.unix + set_time.unix) / 2, format="unix")
    if optimal_time > time:
        assert np.isclose(
            next_valid_observing_time.unix, optimal_time.unix, atol=1, rtol=1e-10
        )  # tolerance is 1 second
        assert (
            get_airmass(
                fields, np.array([next_valid_observing_time]), observer=observer
            )
            < 3.00
        )
    else:
        assert np.isclose(
            next_valid_observing_time.unix, time.unix, atol=1, rtol=1e-10
        )  # tolerance is 1 second


def test_next_sunrise():
    observer = get_observer({"lon": 30, "lat": 45, "elevation": 100})
    time = Time("2024-01-01 00:00:00")
    sunrise = next_sunrise(observer, time)
    assert np.isclose(sunrise.unix, 1704087834.57)
