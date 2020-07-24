from baselayer.app.access import auth_or_token
from ...base import BaseHandler
from .... import plot
from ....models import ClassicalAssignment, Source

import numpy as np
from astropy import time as ap_time
import pandas as pd


# TODO this should distinguish between "no data to plot" and "plot failed"
class PlotPhotometryHandler(BaseHandler):
    @auth_or_token
    def get(self, obj_id):
        height = self.get_query_argument("plotHeight", 300)
        width = self.get_query_argument("plotWidth", 600)
        docs_json, render_items, custom_model_js = plot.photometry_plot(
            obj_id, self.current_user, height=int(height), width=int(width),
        )
        if docs_json is None:
            self.success(data={'docs_json': None, 'url': self.request.path})
        else:
            self.success(data={'docs_json': docs_json, 'render_items': render_items,
                               'custom_model_js': custom_model_js,
                               'url': self.request.uri})


class PlotSpectroscopyHandler(BaseHandler):
    @auth_or_token
    def get(self, obj_id):
        docs_json, render_items, custom_model_js = plot.spectroscopy_plot(obj_id)
        if docs_json is None:
            self.success(data={'docs_json': None, 'url': self.request.path})
        else:
            self.success(data={'docs_json': docs_json, 'render_items': render_items,
                               'custom_model_js': custom_model_js,
                               'url': self.request.path})


class PlotAirmassHandler(BaseHandler):
    @auth_or_token
    def get(self, assignment_id):
        assignment = ClassicalAssignment.query.get(assignment_id)
        if assignment is None:
            self.error('Invalid assignment id.')
        obj = assignment.obj
        permission_check = Source.get_obj_if_owned_by(obj.id, self.current_user)
        if permission_check is None:
            self.error('Invalid assignment id.')

        sunset = assignment.run.sunset
        sunrise = assignment.run.sunrise

        time = np.linspace(sunset.unix, sunrise.unix, 50)
        time = ap_time.Time(time, format='unix')

        airmass = obj.airmass(assignment.run.instrument.telescope, time)
        time = time.iso
        df = pd.DataFrame({'time': time, 'airmass': airmass})
        json = df.to_dict(orient='records')
        return self.success(data=json)
