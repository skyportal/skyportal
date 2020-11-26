from ...base import BaseHandler
from baselayer.app.access import auth_or_token
from ....models import Telescope
from astropy import time as ap_time


class EphemerisHandler(BaseHandler):
    @auth_or_token
    def get(self, telescope_id):

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

        telescope = Telescope.query.get(telescope_id)
        if telescope is None:
            return self.error(
                f'Invalid telescope id: {telescope_id}, record does not exist.'
            )

        ephemeris = telescope.ephemeris(time)
        return self.success(data=ephemeris)
