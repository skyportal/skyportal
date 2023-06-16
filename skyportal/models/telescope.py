__all__ = ['Telescope']

import numpy as np
from datetime import timedelta
import warnings
import sqlalchemy as sa
from sqlalchemy.orm import relationship
from sqlalchemy_utils import URLType

import timezonefinder
import astroplan
from astropy import units as u
from astropy import time as ap_time

from baselayer.app.models import (
    Base,
    CustomUserAccessControl,
    DBSession,
    public,
)
from baselayer.log import make_log

log = make_log('model/telescope')


def manage_telescope_access_logic(cls, user_or_token):
    if user_or_token.is_system_admin:
        return DBSession().query(cls)
    elif 'Manage allocations' in [acl.id for acl in user_or_token.acls]:
        return DBSession().query(cls)
    else:
        # return an empty query
        return DBSession().query(cls).filter(cls.id == -1)


class Telescope(Base):
    """A ground or space-based observational facility that can host Instruments."""

    read = public
    create = update = delete = CustomUserAccessControl(manage_telescope_access_logic)

    name = sa.Column(
        sa.String,
        unique=True,
        nullable=False,
        doc="Unabbreviated facility name (e.g., Palomar 200-inch Hale Telescope).",
    )
    nickname = sa.Column(
        sa.String, nullable=False, doc="Abbreviated facility name (e.g., P200)."
    )
    lat = sa.Column(sa.Float, nullable=True, doc='Latitude in deg.')
    lon = sa.Column(sa.Float, nullable=True, doc='Longitude in deg.')
    elevation = sa.Column(sa.Float, nullable=True, doc='Elevation in meters.')
    diameter = sa.Column(sa.Float, nullable=False, doc='Diameter in meters.')
    skycam_link = sa.Column(
        URLType, nullable=True, doc="Link to the telescope's sky camera."
    )
    weather_link = sa.Column(URLType, doc="Link to the preferred weather site")
    robotic = sa.Column(
        sa.Boolean, default=False, nullable=False, doc="Is this telescope robotic?"
    )

    fixed_location = sa.Column(
        sa.Boolean,
        nullable=False,
        server_default='true',
        doc="Does this telescope have a fixed location (lon, lat, elev)?",
    )

    instruments = relationship(
        'Instrument',
        back_populates='telescope',
        cascade='save-update, merge, refresh-expire, expunge',
        passive_deletes=True,
        doc="The Instruments on this telescope.",
    )

    @property
    def observer(self):
        """Return an `astroplan.Observer` representing an observer at this
        facility, accounting for the latitude, longitude, and elevation."""
        try:
            return self._observer
        except AttributeError:
            if (
                self.lon is None
                or self.lon == ""
                or np.isnan(self.lon)
                or self.lat is None
                or self.lat == ""
                or np.isnan(self.lat)
                or self.fixed_location is False
                or self.fixed_location is None
            ):
                self._observer = None
                return self._observer

        try:
            elevation = self.elevation
            # if elevation is not specified, assume it is 0
            if (
                self.elevation is None
                or self.elevation == ""
                or np.isnan(self.elevation)
            ):
                elevation = 0

            self._observer = astroplan.Observer(
                longitude=self.lon * u.deg,
                latitude=self.lat * u.deg,
                elevation=elevation * u.m,
            )

        except Exception as e:
            log(
                f'Telescope {self.id} ("{self.name}") cannot calculate an observer: {e}'
            )
            self._observer = None

        return self._observer

    @property
    def observer_timezone(self):
        """Return an `astroplan.Observer` representing an observer at this
        facility, accounting for the latitude, longitude, elevation, and
        local time zone of the observatory (if ground based)."""
        try:
            return self._observer_timezone
        except AttributeError:
            if (
                self.lon is None
                or self.lon == ""
                or np.isnan(self.lon)
                or self.lat is None
                or self.lat == ""
                or np.isnan(self.lat)
                or self.fixed_location is False
                or self.fixed_location is None
            ):
                self._observer_timezone = None
                return self._observer_timezone

        try:
            tf = timezonefinder.TimezoneFinder(in_memory=True)
            local_tz = tf.timezone_at(lng=(self.lon + 180) % 360 - 180, lat=self.lat)
            elevation = self.elevation
            # if elevation is not specified, assume it is 0
            if (
                self.elevation is None
                or self.elevation == ""
                or np.isnan(self.elevation)
            ):
                elevation = 0

            self._observer_timezone = astroplan.Observer(
                longitude=self.lon * u.deg,
                latitude=self.lat * u.deg,
                elevation=elevation * u.m,
                timezone=local_tz,
            )

        except Exception as e:
            log(
                f'Telescope {self.id} ("{self.name}") cannot calculate an observer: {e}'
            )
            self._observer_timezone = None

        return self._observer_timezone

    def next_sunset(self, time=None):
        """The astropy timestamp of the next sunset after `time` at this site.
        If time=None, uses the current time."""
        observer = self.observer
        if observer is None:
            return None
        if time is None:
            time = ap_time.Time.now()
        return observer.sun_set_time(time, which='next')

    def next_sunrise(self, time=None):
        """The astropy timestamp of the next sunrise after `time` at this site.
        If time=None, uses the current time."""
        observer = self.observer
        if observer is None:
            return None
        if time is None:
            time = ap_time.Time.now()
        return observer.sun_rise_time(time, which='next')

    def next_twilight_evening_nautical(self, time=None):
        """The astropy timestamp of the next evening nautical (-12 degree)
        twilight at this site. If time=None, uses the current time."""
        observer = self.observer
        if observer is None:
            return None
        if time is None:
            time = ap_time.Time.now()
        return observer.twilight_evening_nautical(time, which='next')

    def next_twilight_morning_nautical(self, time=None):
        """The astropy timestamp of the next morning nautical (-12 degree)
        twilight at this site. If time=None, uses the current time."""
        observer = self.observer
        if observer is None:
            return None
        if time is None:
            time = ap_time.Time.now()
        with warnings.catch_warnings():
            # for telescopes above the arctic circle (or below antarctic circle)
            # there is no morning nautical twilight
            # so this returns a MaskedArray and raises a warning.
            warnings.simplefilter("ignore")
            t = observer.twilight_morning_nautical(time, which='next')
            if isinstance(t.value, np.ma.core.MaskedArray):
                return None
        return t

    def next_twilight_evening_astronomical(self, time=None):
        """The astropy timestamp of the next evening astronomical (-18 degree)
        twilight at this site. If time=None, uses the current time."""
        observer = self.observer
        if observer is None:
            return None
        if time is None:
            time = ap_time.Time.now()
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            t = observer.twilight_evening_astronomical(time, which='next')
            if isinstance(t.value, np.ma.core.MaskedArray):
                return None
        return t

    def next_twilight_morning_astronomical(self, time=None):
        """The astropy timestamp of the next morning astronomical (-18 degree)
        twilight at this site. If time=None, uses the current time."""
        observer = self.observer
        if observer is None:
            return None
        if time is None:
            time = ap_time.Time.now()
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            t = observer.twilight_morning_astronomical(time, which='next')
            if isinstance(t.value, np.ma.core.MaskedArray):
                return None
        return t

    def ephemeris(self, time):

        if self.observer is None:
            return {}

        sunrise = self.next_sunrise(time=time)
        sunset = self.next_sunset(time=time)

        if sunset is not None and sunset > sunrise:
            sunset = self.observer.sun_set_time(time, which='previous')
            time = sunset - ap_time.TimeDelta(30, format='sec')

        twilight_morning_astronomical = self.next_twilight_morning_astronomical(
            time=time
        )
        twilight_evening_astronomical = self.next_twilight_evening_astronomical(
            time=time
        )

        twilight_morning_nautical = self.next_twilight_morning_nautical(time=time)
        twilight_evening_nautical = self.next_twilight_evening_nautical(time=time)

        if sunset is not None:
            sunset_utc = sunset.isot
            sunset_unix_ms = sunset.unix * 1000
        else:
            sunset_utc = None
            sunset_unix_ms = None

        if sunrise is not None:
            sunrise_utc = sunrise.isot
            sunrise_unix_ms = sunrise.unix * 1000
        else:
            sunrise_utc = None
            sunrise_unix_ms = None

        if twilight_morning_astronomical is not None:
            twilight_morning_astronomical_utc = twilight_morning_astronomical.isot
            twilight_morning_astronomical_unix_ms = (
                twilight_morning_astronomical.unix * 1000
            )
        else:
            twilight_morning_astronomical_utc = None
            twilight_morning_astronomical_unix_ms = None

        if twilight_evening_astronomical is not None:
            twilight_evening_astronomical_utc = twilight_evening_astronomical.isot
            twilight_evening_astronomical_unix_ms = (
                twilight_evening_astronomical.unix * 1000
            )
        else:
            twilight_evening_astronomical_utc = None
            twilight_evening_astronomical_unix_ms = None

        if twilight_morning_nautical is not None:
            twilight_morning_nautical_utc = twilight_morning_nautical.isot
            twilight_morning_nautical_unix_ms = twilight_morning_nautical.unix * 1000
        else:
            twilight_morning_nautical_utc = None
            twilight_morning_nautical_unix_ms = None

        if twilight_evening_nautical is not None:
            twilight_evening_nautical_utc = twilight_evening_nautical.isot
            twilight_evening_nautical_unix_ms = twilight_evening_nautical.unix * 1000
        else:
            twilight_evening_nautical_utc = None
            twilight_evening_nautical_unix_ms = None

        return {
            'sunset_utc': sunset_utc,
            'sunrise_utc': sunrise_utc,
            'twilight_morning_astronomical_utc': twilight_morning_astronomical_utc,
            'twilight_evening_astronomical_utc': twilight_evening_astronomical_utc,
            'twilight_morning_nautical_utc': twilight_morning_nautical_utc,
            'twilight_evening_nautical_utc': twilight_evening_nautical_utc,
            'utc_offset_hours': self.observer.timezone.utcoffset(time.datetime)
            / timedelta(hours=1),
            'sunset_unix_ms': sunset_unix_ms,
            'sunrise_unix_ms': sunrise_unix_ms,
            'twilight_morning_astronomical_unix_ms': twilight_morning_astronomical_unix_ms,
            'twilight_evening_astronomical_unix_ms': twilight_evening_astronomical_unix_ms,
            'twilight_morning_nautical_unix_ms': twilight_morning_nautical_unix_ms,
            'twilight_evening_nautical_unix_ms': twilight_evening_nautical_unix_ms,
        }

    @property
    def current_time(self):
        morning = False
        evening = False
        is_night_astronomical = False
        if (
            self.fixed_location
            and self.lon is not None
            and self.lat is not None
            and self.elevation is not None
            and self.observer is not None
        ):
            try:
                morning = self.next_twilight_morning_astronomical()
                evening = self.next_twilight_evening_astronomical()
                if morning is not None and evening is not None:
                    is_night_astronomical = bool(morning.jd < evening.jd)
            except Exception:
                is_night_astronomical = False
                morning = False
                evening = False

        return {
            "is_night_astronomical": is_night_astronomical,
            "morning": morning,
            "evening": evening,
        }
