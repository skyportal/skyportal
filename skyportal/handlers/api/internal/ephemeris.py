from astropy import time as ap_time

from baselayer.app.access import auth_or_token

from ....models import Telescope
from ...base import BaseHandler

MAX_TELESCOPES_TO_DISPLAY = 16


class EphemerisHandler(BaseHandler):
    @auth_or_token
    # TODO: add pagination to this endpoint
    def get(self, telescope_id=None):
        f"""
        ---
        single:
          description: Retrieve ephemeris data for a single telescope, or for all telescopes if no telescope_id is provided, up to {MAX_TELESCOPES_TO_DISPLAY} telescopes.
          tags:
            - ephemeris
          parameters:
            - in: path
              name: telescope_id
              required: false
              schema:
                type: string
          responses:
            200:
              content:
                application/json:
                    schema:
                        type: object
            400:
              content:
                application/json:
                  schema: Error
        multiple:
          tags:
            - ephemeris
          description: Retrieve ephemeris data for multiple telescopes, up to {MAX_TELESCOPES_TO_DISPLAY}
          parameters:
          - in: query
            name: telescope_ids
            nullable: true
            schema:
              type: array
            description: |
                List of telescope IDs to retrieve ephemeris data for.
          responses:
            200:
              content:
                application/json:
                  schema:
                    type: object
            400:
              content:
                application/json:
                  schema: Error
        """

        time = self.get_query_argument("time", None)

        if time is not None:
            try:
                time = ap_time.Time(time, format="iso")
            except ValueError as e:
                return self.error(f"Invalid time format: {e.args[0]}")
        else:
            time = ap_time.Time.now()

        ephemerides = None

        with self.Session() as session:
            if telescope_id is not None:
                try:
                    telescope_id = int(telescope_id)
                except ValueError as e:
                    return self.error(f"Invalid value for Telescope id: {e.args[0]}")
                telescope = session.scalars(
                    Telescope.select(session.user_or_token).where(
                        Telescope.id == telescope_id
                    )
                ).first()
                if telescope is None:
                    return self.error("No Telescope with this id")
                else:
                    if telescope.fixed_location is not True:
                        return self.error("Telescope is not fixed")
                    else:
                        ephemerides = telescope.ephemeris(time)
            else:
                telescope_ids = self.get_query_argument("telescopeIds", None)
                if telescope_ids is not None:
                    try:
                        telescope_ids = [int(t) for t in telescope_ids.split(",")]
                    except ValueError as e:
                        return self.error(f"Invalid telescopeIds format: {e.args[0]}")

                    if len(telescope_ids) > MAX_TELESCOPES_TO_DISPLAY:
                        telescope_ids = telescope_ids[:MAX_TELESCOPES_TO_DISPLAY]

                    telescopes = session.scalars(
                        Telescope.select(session.user_or_token).where(
                            Telescope.id.in_(telescope_ids)
                        )
                    ).all()
                else:
                    telescopes = Telescope.query.all()
                    if len(telescopes) > MAX_TELESCOPES_TO_DISPLAY:
                        telescopes = telescopes[:MAX_TELESCOPES_TO_DISPLAY]

                ephemerides = {
                    telescope.id: telescope.ephemeris(time) for telescope in telescopes
                }

            return self.success(data=ephemerides)
