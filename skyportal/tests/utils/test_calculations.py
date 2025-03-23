import numpy as np
from astropy import units as u
from astropy.time import Time

from baselayer.app.models import DBSession
from skyportal.models import Telescope
from skyportal.tests.external.test_moving_objects import (
    add_telescope_and_instrument,
    remove_telescope_and_instrument,
)
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
    sun_altitude = -18 * u.degree
    target = get_target(fields)
    observer = get_observer({"lon": 30, "lat": 45, "elevation": 100})
    time = Time("2024-01-01 00:00:00")

    # rise and set times of the target
    rise_time, set_time = get_rise_set_time(
        target, observer=observer, time=time, sun_altitude=sun_altitude
    )
    assert rise_time[0].iso == "2023-12-31 11:22:28.590"
    assert set_time[0].iso == "2023-12-31 23:21:29.263"

    assert rise_time[1].iso == "2023-12-31 19:02:11.732"
    assert set_time[1].iso == "2024-01-01 06:59:22.583"

    # rise and set times of the target only during nighttime
    rise_time_by_night, set_time_by_night = get_rise_set_time(
        target, observer=observer, time=time, sun_altitude=sun_altitude, night_only=True
    )
    sunset = observer.sun_set_time(time, which="previous", horizon=sun_altitude)
    sunrise = observer.sun_rise_time(time, which="next", horizon=sun_altitude)
    # The target rise before the sunset so the rise time by night should be the sunset time
    assert rise_time[0] < sunset
    assert rise_time_by_night[0].iso == sunset.iso
    # The target set before the sunrise so the set time by night should be the set time
    assert set_time[0] < sunrise
    assert set_time_by_night[0].iso == set_time[0].iso
    # The target rise after the sunset so the rise time by night should be the rise time
    assert sunset < rise_time[1]
    assert rise_time_by_night[1].iso == rise_time[1].iso

    assert sunrise < set_time[1]
    assert set_time_by_night[1].iso == sunrise.iso

    # Test the rise and set times of the target with airmass 3.0
    target = get_target([{"ra": 30, "dec": 45, "field_id": 1}])
    altitude = get_altitude_from_airmass(3.0)
    assert np.isclose(altitude, 19.29494943)
    rise_time, set_time = get_rise_set_time(
        target, altitude=altitude * u.deg, observer=observer, time=time
    )
    assert rise_time.iso == "2023-12-31 10:03:10.595"
    assert set_time.iso == "2024-01-01 00:40:47.194"

    # Test the rise and set times of the target with airmass 2.0
    altitude = get_altitude_from_airmass(2.0)
    assert np.isclose(altitude, 29.88587059)
    rise_time, set_time = get_rise_set_time(
        target, altitude=altitude * u.deg, observer=observer, time=time
    )
    # With airmass 2.0 the rise and set range is smaller
    assert rise_time.iso == "2023-12-31 11:21:40.955"
    assert set_time.iso == "2023-12-31 23:22:16.866"


def test_get_next_observing_time(super_admin_token):
    fields = [
        {"ra": 30, "dec": 45, "field_id": 1},
    ]
    target = get_target(fields)
    telescope_id, instrument_id, _, _ = add_telescope_and_instrument(
        "Tarot", super_admin_token
    )
    telescope = (
        DBSession().query(Telescope).filter(Telescope.id == telescope_id).first()
    )
    sun_altitude = -18 * u.degree

    time = Time.now()

    altitude = get_altitude_from_airmass(3.0)
    assert np.isclose(altitude, 19.29494943)

    sunset = telescope.observer.sun_set_time(time, which="next", horizon=sun_altitude)
    sunrise = telescope.observer.sun_rise_time(time, which="next", horizon=sun_altitude)

    if sunrise < sunset:
        sunset = telescope.observer.sun_set_time(
            time, which="previous", horizon=sun_altitude
        )

    rise_time, set_time = get_rise_set_time(
        target,
        altitude=altitude * u.deg,
        observer=telescope.observer,
        time=time,
        sun_altitude=sun_altitude,
        night_only=True,
    )

    try:
        next_valid_observing_time = get_next_valid_observing_time(
            start_time=time,
            end_time=time + 7 * u.day,
            telescope=telescope,
            target=target,
            airmass=3.0,
            observe_at_optimal_airmass=False,
        )
        if not rise_time and not set_time:
            return

        # if the rise time is the real one and not the actual time or the one by night, check the airmass is 3.0
        if time < rise_time and sunset + 30 * u.second < rise_time:
            # Do not compare the milliseconds part
            assert (
                next_valid_observing_time.iso.split(".")[0]
                == rise_time.iso.split(".")[0]
            )
            assert np.isclose(
                get_airmass(
                    fields,
                    np.array([next_valid_observing_time]),
                    observer=telescope.observer,
                ).item(),
                3.00,
                atol=1e-2,
            )
        elif rise_time < time and sunset < time:
            assert next_valid_observing_time.iso.split(".")[0] == time.iso.split(".")[0]
        else:
            assert (
                next_valid_observing_time.iso.split(".")[0] == sunset.iso.split(".")[0]
            )

    except ValueError as e:
        if "No valid observing time found in the range" in str(e):
            assert not rise_time and not set_time
        else:
            raise e

    try:
        next_valid_observing_time = get_next_valid_observing_time(
            start_time=time,
            end_time=time + 7 * u.day,
            telescope=telescope,
            target=target,
            airmass=3.0,
            observe_at_optimal_airmass=True,
        )
        if not rise_time and not set_time:
            return

        real_rise_time, real_set_time = get_rise_set_time(
            target,
            altitude=altitude * u.deg,
            observer=telescope.observer,
            time=time,
            sun_altitude=sun_altitude,
            night_only=False,
        )
        optimal_time = Time(
            (real_rise_time.unix + real_set_time.unix) / 2, format="unix"
        )

        # if the optimal time is the real one and not the actual time or the one by night, check the airmass is better than 2.98
        if time < optimal_time and sunset + 30 * u.second < optimal_time < sunrise:
            # Do not compare the milliseconds part
            assert (
                next_valid_observing_time.iso.split(".")[0]
                == optimal_time.iso.split(".")[0]
            )
            assert (
                get_airmass(
                    fields,
                    np.array([next_valid_observing_time]),
                    observer=telescope.observer,
                ).item()
                < 2.98
            )
        elif optimal_time < time and sunset < time:
            assert next_valid_observing_time.iso.split(".")[0] == time.iso.split(".")[0]
        else:
            assert (
                next_valid_observing_time.iso.split(".")[0] == sunset.iso.split(".")[0]
            )

    except ValueError as e:
        if "No valid observing time found in the range" in str(e):
            assert not rise_time and not set_time
        else:
            raise e

    remove_telescope_and_instrument(telescope_id, instrument_id, super_admin_token)


def test_next_sunrise():
    observer = get_observer({"lon": 30, "lat": 45, "elevation": 100})
    time = Time("2024-01-01 00:00:00")
    sunrise = next_sunrise(observer, time)
    assert np.isclose(sunrise.unix, 1704087834.57)
