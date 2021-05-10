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

        telescope = Telescope.get_if_accessible_by(
            telescope_id, self.current_user, raise_if_none=True
        )

        ephemeris = telescope.ephemeris(time)
        self.verify_and_commit()
        return self.success(data=ephemeris)
