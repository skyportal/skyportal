import arrow
from astropy.time import Time
from astropy.coordinates import Angle
import astropy.units as u
import asyncio
import requests
import re
from tornado.ioloop import IOLoop
import urllib

from baselayer.app.env import load_env
from baselayer.app.access import auth_or_token
from baselayer.log import make_log
from baselayer.app.flow import Flow

from ..base import BaseHandler
from ...models import (
    ThreadSession,
    Obj,
    User,
)

env, cfg = load_env()
log = make_log('api/mpc')

MPC_ENDPOINT = cfg['app.mpc_endpoint']
mpcheck_url = urllib.parse.urljoin(MPC_ENDPOINT, 'cgi-bin/mpcheck.cgi')


class ObjMPCHandler(BaseHandler):
    @auth_or_token
    def post(self, obj_id):
        """
        ---
        description: Retrieve an object's status from Minor Planet Center
        tags:
          - objs
        parameters:
          - in: path
            name: obj_id
            required: true
            schema:
              type: string
        requestBody:
          content:
            application/json:
              schema:
                type: object
                properties:
                  obscode:
                    type: string
                    description: |
                      Minor planet center observatory code.
                      Defaults to 500, corresponds to geocentric.
                  date:
                    type: string
                    description: |
                      Time to check MPC for.
                      Defaults to current time.
                  limiting_magnitude:
                    type: float
                    description: |
                      Limiting magnitude down which to search.
                      Defaults to 24.0.
                  search_radius:
                    type: float
                    description: |
                      Search radius for MPC [in arcmin].
                      Defaults to 1 arcminute.

        responses:
          200:
            content:
              application/json:
                schema: Success
          400:
            content:
              application/json:
                schema: Error
        """

        data = self.get_json()
        date = data.get('date')
        if date is None:
            date = Time.now()
        else:
            try:
                date = Time(arrow.get(date).datetime, format='datetime')
            except (TypeError, arrow.ParserError):
                return self.error(f'Cannot parse time input value "{date}".')

        limiting_magnitude = data.get('limiting_magnitude', 24.0)
        try:
            limiting_magnitude = float(limiting_magnitude)
        except Exception:
            return self.error('Cannot read in limiting magnitude.')

        search_radius = data.get('search_radius', 1)
        try:
            search_radius = float(search_radius)
        except Exception:
            return self.error('Cannot read in search radius.')

        obscode = data.get('obscode', '500')

        with self.Session() as session:
            obj = session.scalars(
                Obj.select(session.user_or_token, mode='update').where(Obj.id == obj_id)
            ).first()
            if obj is None:
                return self.error(f"Cannot find object with ID {obj_id}.")

            year = date.strftime("%Y")
            month = date.strftime("%m")
            hour = int(date.strftime("%H"))
            minute = int(date.strftime("%M"))
            second = float(date.strftime("%S.%f"))
            day = f"{int(date.strftime('%d'))+(hour+minute/60+second/3600)/24:.2f}"

            ra = Angle(obj.ra, unit='degree')
            ra_hms = ra.to_string(
                unit='hourangle', sep=' ', precision=2, pad=True
            ).split(" ")
            dec = Angle(obj.dec, unit='degree')
            dec_dms = dec.to_string(unit=u.deg, sep=' ', precision=2, pad=True).split(
                " "
            )

            params = {
                'year': year,
                'month': month,
                'day': day,
                'which': 'pos',
                'ra': f'{ra_hms[0]}+{ra_hms[1]}+{ra_hms[2]}',
                'decl': f'{dec_dms[0]}+{dec_dms[1]}+{dec_dms[2]}',
                'TextArea': '',
                'radius': search_radius,
                'limit': limiting_magnitude,
                'oc': obscode,
                'sort': 'd',
                'mot': 'h',
                'tmot': 's',
                'pdes': 'u',
                'needed': 'f',
                'ps': 'n',
                'type': 'p',
            }

            url = f"{mpcheck_url}?{urllib.parse.urlencode(params)}"
            url = url.replace("%2B", "+")

            try:
                loop = asyncio.get_event_loop()
            except Exception:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            IOLoop.current().run_in_executor(
                None,
                lambda: query_mpc(obj_id, self.associated_user_object.id, url),
            )

            return self.success()


def query_mpc(obj_id, user_id, url):
    """Query MPC for a given object.
    obj_id : str
        Object ID
    user_id : int
        SkyPortal ID of User posting the MPC result
    url : str
        MPC query URL
    """

    log(f'Querying MPC for {obj_id}: {url}')

    with ThreadSession() as session:
        try:
            user = session.query(User).get(user_id)

            obj = session.scalars(Obj.select(user).where(Obj.id == obj_id)).first()

            requests_session = requests.Session()
            response = requests_session.get(url)

            if re.findall("The following objects,.*", response.text):
                responseSplit = response.text.split("(1)")[-1].split(" ")
                mpc_name = list(filter(None, responseSplit))[0]

                log(f'{obj_id}: identified MPC name {mpc_name}')

                obj.is_roid = True
                obj.mpc_name = mpc_name
                session.commit()
            elif re.findall("No known minor planets,.*", response.text):
                log(f'{obj_id}: No known minor planets')
                obj.is_roid = False
                session.commit()
            else:
                log(f'Message from MPC for {obj_id} not parsable: {response.text}')

            flow = Flow()
            flow.push(
                '*',
                'skyportal/REFRESH_SOURCE',
                payload={'obj_key': obj.internal_key},
            )
        except Exception as e:
            log(f"Error checking MPC for {obj_id}: {(str(e))}")
            session.rollback()
