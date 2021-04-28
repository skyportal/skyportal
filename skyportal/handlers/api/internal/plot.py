from baselayer.app.access import auth_or_token
from ...base import BaseHandler
from .... import plot
from ....models import ClassicalAssignment, Obj, Telescope

import numpy as np
from astropy import time as ap_time
import pandas as pd


device_types = [
    "browser",
    "mobile_landscape",
    "mobile_portrait",
    "tablet_landscape",
    "tablet_portrait",
]


class PlotPhotometryHandler(BaseHandler):
    @auth_or_token
    def get(self, obj_id):
        width = self.get_query_argument("width", 600)
        device = self.get_query_argument("device", None)
        # Just return browser by default if not one of accepted types
        if device not in device_types:
            device = "browser"
        json = plot.photometry_plot(
            obj_id,
            self.current_user,
            width=int(width),
            device=device,
        )
        self.verify_and_commit()
        self.success(data={'bokehJSON': json, 'url': self.request.uri})


class PlotSpectroscopyHandler(BaseHandler):
    @auth_or_token
    def get(self, obj_id):
        width = self.get_query_argument("width", 600)
        device = self.get_query_argument("device", None)
        # Just return browser by default if not one of accepted types
        if device not in device_types:
            device = "browser"
        spec_id = self.get_query_argument("spectrumID", None)
        json = plot.spectroscopy_plot(
            obj_id,
            self.associated_user_object,
            spec_id,
            width=int(width),
            device=device,
        )
        self.verify_and_commit()
        self.success(data={'bokehJSON': json, 'url': self.request.uri})


class AirmassHandler(BaseHandler):
    def calculate_airmass(self, obj, telescope, sunset, sunrise):
        time = np.linspace(sunset.unix, sunrise.unix, 50)
        time = ap_time.Time(time, format='unix')

        airmass = obj.airmass(telescope, time)
        time = time.unix * 1000
        df = pd.DataFrame({'time': time, 'airmass': airmass})
        json = df.to_dict(orient='records')
        return json


class PlotAssignmentAirmassHandler(AirmassHandler):
    @auth_or_token
    def get(self, assignment_id):
        assignment = ClassicalAssignment.get_if_accessible_by(
            assignment_id, self.current_user, raise_if_none=True
        )
        obj = assignment.obj
        telescope = assignment.run.instrument.telescope
        time = assignment.run.calendar_noon

        sunrise = telescope.next_sunrise(time=time)
        sunset = telescope.next_sunset(time=time)

        if sunset > sunrise:
            sunset = telescope.observer.sun_set_time(time, which='previous')

        json = self.calculate_airmass(obj, telescope, sunrise, sunset)
        self.verify_and_commit()
        return self.success(data=json)


class PlotObjTelAirmassHandler(AirmassHandler):
    @auth_or_token
    def get(self, obj_id, telescope_id):

        time = self.get_query_argument('time', None)
        if time is not None:
            try:
                time = ap_time.Time(time, format='iso')
            except ValueError as e:
                return self.error(f'Invalid time format: {e.args[0]}')
        else:
            time = ap_time.Time.now()

        obj = Obj.get_if_accessible_by(obj_id, self.current_user, raise_if_none=True)
        try:
            telescope_id = int(telescope_id)
        except TypeError:
            return self.error(f'Invalid telescope id: {telescope_id}, must be integer.')

        telescope = Telescope.get_if_accessible_by(
            telescope_id, self.current_user, raise_if_none=True
        )

        sunrise = telescope.next_sunrise(time=time)
        sunset = telescope.next_sunset(time=time)

        if sunset > sunrise:
            sunset = telescope.observer.sun_set_time(time, which='previous')

        json = self.calculate_airmass(obj, telescope, sunrise, sunset)
        self.verify_and_commit()
        return self.success(data=json)
