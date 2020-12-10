from baselayer.app.access import auth_or_token
from ...base import BaseHandler
from .... import plot
from ....models import ClassicalAssignment, Obj, Telescope

import numpy as np
from astropy import time as ap_time
import pandas as pd


class PlotPhotometryHandler(BaseHandler):
    @auth_or_token
    def get(self, obj_id):
        height = self.get_query_argument("height", 300)
        width = self.get_query_argument("width", 600)
        json = plot.photometry_plot(
            obj_id, self.current_user, height=int(height), width=int(width),
        )
        self.success(data={'bokehJSON': json, 'url': self.request.uri})


class PlotSpectroscopyHandler(BaseHandler):
    @auth_or_token
    def get(self, obj_id):
        height = self.get_query_argument("height", 300)
        width = self.get_query_argument("width", 600)
        spec_id = self.get_query_argument("spectrumID", None)
        json = plot.spectroscopy_plot(
            obj_id,
            self.associated_user_object,
            spec_id,
            height=int(height),
            width=int(width),
        )
        self.success(data={'bokehJSON': json, 'url': self.request.uri})


class AirmassHandler(BaseHandler):
    def calculate_airmass(self, obj, telescope, sunset, sunrise):
        permission_check = Obj.get_if_readable_by(obj.id, self.current_user)
        if permission_check is None:
            return self.error('Invalid assignment id.')

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
        assignment = ClassicalAssignment.get_if_readable_by(
            assignment_id, self.current_user
        )
        if assignment is None:
            return self.error('Invalid assignment id.')
        obj = assignment.obj
        telescope = assignment.run.instrument.telescope
        time = assignment.run.calendar_noon

        sunrise = telescope.next_sunrise(time=time)
        sunset = telescope.next_sunset(time=time)

        if sunset > sunrise:
            sunset = telescope.observer.sun_set_time(time, which='previous')

        json = self.calculate_airmass(obj, telescope, sunrise, sunset)
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

        obj = Obj.get_if_readable_by(obj_id, self.current_user)
        if obj is None:
            return self.error('Invalid assignment id.')

        try:
            telescope_id = int(telescope_id)
        except TypeError:
            return self.error(f'Invalid telescope id: {telescope_id}, must be integer.')

        telescope = Telescope.query.get(telescope_id)
        if telescope is None:
            return self.error(
                f'Invalid telescope id: {telescope_id}, record does not exist.'
            )

        sunrise = telescope.next_sunrise(time=time)
        sunset = telescope.next_sunset(time=time)

        if sunset > sunrise:
            sunset = telescope.observer.sun_set_time(time, which='previous')

        json = self.calculate_airmass(obj, telescope, sunrise, sunset)
        return self.success(data=json)
