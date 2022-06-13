from ...base import BaseHandler
from baselayer.app.access import auth_or_token
from ....models import Telescope
from astropy import time as ap_time

MAX_TELESCOPES_TO_RETURN = 16


class EphemerisHandler(BaseHandler):
    @auth_or_token
    def get(self, telescope_id=None):

        time = self.get_query_argument('time', None)

        if time is not None:
            try:
                time = ap_time.Time(time, format='iso')
            except ValueError as e:
                return self.error(f'Invalid time format: {e.args[0]}')
        else:
            time = ap_time.Time.now()

        ephemerides = None

        if telescope_id is not None:
            try:
                telescope_id = int(telescope_id)
            except ValueError as e:
                return self.error(f'Invalid value for Telescope id: {e.args[0]}')
            telescope = Telescope.query.filter(Telescope.id == telescope_id).first()
            if telescope is None:
                return self.error('No Telescope with this id')
            else:
                if telescope.fixed_location is not True:
                    return self.error('Telescope is not fixed')
                else:
                    ephemerides = telescope.ephemeris(time)
        else:
            telescope_ids = self.get_query_argument('telescopeIds', None)
            if telescope_ids is not None:
                try:
                    telescope_ids = [int(t) for t in telescope_ids.split(',')]
                except ValueError as e:
                    return self.error(f'Invalid telescopeIds format: {e.args[0]}')

                if len(telescope_ids) > MAX_TELESCOPES_TO_RETURN:
                    telescope_ids = telescope_ids[:MAX_TELESCOPES_TO_RETURN]

                telescopes = Telescope.query.filter(
                    Telescope.id.in_(telescope_ids)
                ).all()
            else:
                telescopes = Telescope.query.all()
                if len(telescopes) > MAX_TELESCOPES_TO_RETURN:
                    telescopes = telescopes[:MAX_TELESCOPES_TO_RETURN]

            ephemerides = {
                telescope.id: telescope.ephemeris(time) for telescope in telescopes
            }

        self.verify_and_commit()
        return self.success(data=ephemerides)
