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

from baselayer.app.models import Base, restricted
from baselayer.log import make_log

log = make_log('api/source')


class Telescope(Base):
    """A ground or space-based observational facility that can host Instruments."""

    create = restricted

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
        facility, accounting for the latitude, longitude, elevation, and
        local time zone of the observatory (if ground based)."""
        try:
            return self._observer
        except AttributeError:
            if not self.fixed_location:
                return None

            try:
                tf = timezonefinder.TimezoneFinder(in_memory=True)
                local_tz = tf.closest_timezone_at(
                    lng=(self.lon + 180) % 360 - 180, lat=self.lat, delta_degree=5
                )
                elevation = self.elevation
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
                    timezone=local_tz,
                )

            except Exception as e:
                log(
                    f'Telescope {self.id} ("{self.name}") cannot calculate an observer: {e}'
                )
                return None

        return self._observer

    def next_sunset(self, time=None):
        """The astropy timestamp of the next sunset after `time` at this site.
        If time=None, uses the current time."""
        if time is None:
            time = ap_time.Time.now()
        observer = self.observer
        if observer is None:
            return None
        return observer.sun_set_time(time, which='next')

    def next_sunrise(self, time=None):
        """The astropy timestamp of the next sunrise after `time` at this site.
        If time=None, uses the current time."""
        if time is None:
            time = ap_time.Time.now()
        observer = self.observer
        if observer is None:
            return None
        return observer.sun_rise_time(time, which='next')

    def next_twilight_evening_nautical(self, time=None):
        """The astropy timestamp of the next evening nautical (-12 degree)
        twilight at this site. If time=None, uses the current time."""
        if time is None:
            time = ap_time.Time.now()
        observer = self.observer
        if observer is None:
            return None
        return observer.twilight_evening_nautical(time, which='next')

    def next_twilight_morning_nautical(self, time=None):
        """The astropy timestamp of the next morning nautical (-12 degree)
        twilight at this site. If time=None, uses the current time."""
        if time is None:
            time = ap_time.Time.now()
        observer = self.observer
        if observer is None:
            return None
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
        if time is None:
            time = ap_time.Time.now()
        observer = self.observer
        if observer is None:
            return None
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            t = observer.twilight_evening_astronomical(time, which='next')
            if isinstance(t.value, np.ma.core.MaskedArray):
                return None
        return t

    def next_twilight_morning_astronomical(self, time=None):
        """The astropy timestamp of the next morning astronomical (-18 degree)
        twilight at this site. If time=None, uses the current time."""
        if time is None:
            time = ap_time.Time.now()
        observer = self.observer
        if observer is None:
            return None
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

        return {
            'sunset_utc': sunset.isot,
            'sunrise_utc': sunrise.isot,
            'twilight_morning_astronomical_utc': twilight_morning_astronomical.isot,
            'twilight_evening_astronomical_utc': twilight_evening_astronomical.isot,
            'twilight_morning_nautical_utc': twilight_morning_nautical.isot,
            'twilight_evening_nautical_utc': twilight_evening_nautical.isot,
            'utc_offset_hours': self.observer.timezone.utcoffset(time.datetime)
            / timedelta(hours=1),
            'sunset_unix_ms': sunset.unix * 1000,
            'sunrise_unix_ms': sunrise.unix * 1000,
            'twilight_morning_astronomical_unix_ms': twilight_morning_astronomical.unix
            * 1000,
            'twilight_evening_astronomical_unix_ms': twilight_evening_astronomical.unix
            * 1000,
            'twilight_morning_nautical_unix_ms': twilight_morning_nautical.unix * 1000,
            'twilight_evening_nautical_unix_ms': twilight_evening_nautical.unix * 1000,
        }
