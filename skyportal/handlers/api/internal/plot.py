from baselayer.app.access import auth_or_token
from baselayer.app.env import load_env
from ...base import BaseHandler
from ..photometry import get_effective_wavelength
from ....models import ClassicalAssignment, Obj, Telescope

import numpy as np
from astropy import time as ap_time
import astropy.units as u
import pandas as pd
import datetime


device_types = [
    "browser",
    "mobile_landscape",
    "mobile_portrait",
    "tablet_landscape",
    "tablet_portrait",
]

_, cfg = load_env()


class AirmassHandler(BaseHandler):
    def calculate_airmass(self, obj, telescope, sunset, sunrise, sample_size=50):
        time = np.linspace(sunset.unix, sunrise.unix, sample_size)
        time = ap_time.Time(time, format='unix')

        airmass = obj.airmass(telescope, time)
        time = time.unix * 1000
        df = pd.DataFrame({'time': time, 'airmass': airmass})
        return df


class PlotAssignmentAirmassHandler(AirmassHandler):
    @auth_or_token
    async def get(self, assignment_id):
        with self.Session() as session:
            assignment = session.scalar(
                ClassicalAssignment.select(session.user_or_token).where(
                    ClassicalAssignment.id == assignment_id
                )
            )
            if assignment is None:
                return self.error(f"Could not load assignment with ID {assignment_id}")

            obj = assignment.obj
            telescope = assignment.run.instrument.telescope
            time = assignment.run.calendar_noon

            sunrise = telescope.next_sunrise(time=time)
            sunset = telescope.next_sunset(time=time)

            if sunrise is None or sunset is None:
                return self.error('sunrise or sunset not available')

            if sunset > sunrise:
                sunset = telescope.observer.sun_set_time(time, which='previous')

            json = self.calculate_airmass(obj, telescope, sunrise, sunset).to_dict(
                orient='records'
            )
            return self.success(data=json)


class PlotObjTelAirmassHandler(AirmassHandler):
    @auth_or_token
    async def get(self, obj_id, telescope_id):
        time = self.get_query_argument('time', None)
        if time is not None:
            try:
                time = ap_time.Time(time, format='iso')
            except ValueError as e:
                return self.error(f'Invalid time format: {e.args[0]}')
        else:
            time = ap_time.Time.now()

        try:
            telescope_id = int(telescope_id)
        except TypeError:
            return self.error(f'Invalid telescope id: {telescope_id}, must be integer.')

        with self.Session() as session:
            obj = session.scalar(
                Obj.select(session.user_or_token).where(Obj.id == obj_id)
            )
            if obj is None:
                return self.error(f"Could not load object with ID {obj_id}")

            telescope = session.scalar(
                Telescope.select(session.user_or_token).where(
                    Telescope.id == telescope_id
                )
            )
            if telescope is None:
                return self.error(f"Could not load telescope with ID {telescope_id}")

            sunrise = telescope.next_sunrise(time=time)
            sunset = telescope.next_sunset(time=time)

            if sunrise is None or sunset is None:
                return self.error('sunrise or sunset not available')

            if sunset > sunrise:
                sunset = telescope.observer.sun_set_time(time, which='previous')

            json = self.calculate_airmass(obj, telescope, sunrise, sunset).to_dict(
                orient='records'
            )
            return self.success(data=json)


class PlotHoursBelowAirmassHandler(AirmassHandler):
    @auth_or_token
    async def get(self, obj_id, telescope_id):
        threshold = cfg["misc.hours_below_airmass_threshold"]
        if threshold is None:
            threshold = 2.9

        try:
            telescope_id = int(telescope_id)
        except TypeError:
            return self.error(f'Invalid telescope id: {telescope_id}, must be integer.')

        with self.Session() as session:
            obj = session.scalar(
                Obj.select(session.user_or_token).where(Obj.id == obj_id)
            )
            if obj is None:
                return self.error(f"Could not load object with ID {obj_id}")

            telescope = session.scalar(
                Telescope.select(session.user_or_token).where(
                    Telescope.id == telescope_id
                )
            )
            if telescope is None:
                return self.error(f"Could not load telescope with ID {telescope_id}")

            year = datetime.date.today().year
            year_start = datetime.datetime(year, 1, 1, 0, 0, 0)

            json = []
            # Sample every 7 days for the year
            deltat = 7
            for day in range(365 // deltat):
                day = year_start + datetime.timedelta(days=day * deltat)
                day = ap_time.Time(day.isoformat(), format='isot')

                # Get sunrise/sunset times for that day
                sunrise = telescope.next_sunrise(time=day)
                sunset = telescope.next_sunset(time=day)

                if sunrise is None or sunset is None:
                    continue

                # check if is in middle of night
                if (sunrise - sunset).to_value('hr') < 0:
                    sunrise = sunrise + ap_time.TimeDelta(1 * u.day)

                # Compute airmasses for that day
                sample_size = 60
                df = self.calculate_airmass(
                    obj, telescope, sunrise, sunset, sample_size
                )

                # Compute hours below airmass
                num_times_below = df.loc[df["airmass"] < threshold].shape[0]
                total_hours = (sunrise - sunset).to_value('hr')
                hours_below = num_times_below / sample_size * total_hours
                json.append({"date": day.isot, "hours_below": hours_below})

            return self.success(data=json)


class FilterWavelengthHandler(BaseHandler):
    @auth_or_token
    async def get(self):
        filters = self.get_query_argument('filters', None)
        if filters:
            filters = filters.split(',')
            wavelengths = []
            for filter in filters:
                try:
                    wavelengths.append(get_effective_wavelength(filter))
                except ValueError:
                    return self.error("Invalid filters")
            return self.success(data={'wavelengths': wavelengths})
        return self.error("Need to pass in a set of filters")
