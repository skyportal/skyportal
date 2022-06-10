from ...base import BaseHandler
from baselayer.app.access import auth_or_token
from ....models import Telescope
from astropy import time as ap_time


class EphemerisHandler(BaseHandler):
    @auth_or_token
    def get(self):

        time = self.get_query_argument('time', None)
        telescope_ids = self.get_query_argument('telescopeIds', None)
        if time is not None:
            try:
                time = ap_time.Time(time, format='iso')
            except ValueError as e:
                return self.error(f'Invalid time format: {e.args[0]}')
        else:
            time = ap_time.Time.now()
        if telescope_ids is not None:
            try:
                telescope_ids = [int(t) for t in telescope_ids.split(',')]
            except ValueError as e:
                return self.error(f'Invalid telescopeIds format: {e.args[0]}')

            telescopes = Telescope.query.filter(Telescope.id.in_(telescope_ids)).all()
        else:
            telescopes = Telescope.query.all()

        ephemerides = {
            telescope.id: telescope.ephemeris(time) for telescope in telescopes
        }
        self.verify_and_commit()
        return self.success(data=ephemerides)
