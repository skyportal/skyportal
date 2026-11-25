import re
import urllib

import arrow
import astropy.units as u
import requests
import sqlalchemy as sa
from astropy.coordinates import Angle
from astropy.time import Time
from pydantic import BaseModel, ConfigDict, Field
from skyportal_py_models.objs import ObjMPCPostBody
from sqlalchemy.orm import scoped_session, sessionmaker
from tornado.ioloop import IOLoop

from baselayer.app.access import auth_or_token
from baselayer.app.env import load_env
from baselayer.app.flow import Flow
from baselayer.log import make_log

from ...models import (
    Instrument,
    Obj,
    Photometry,
    Telescope,
    User,
    new_session,
)
from ...models.photometry import PHOT_DETECTION_THRESHOLD
from ...utils.jpl_sbident import GEOCENTRIC_OBSCODE
from ..base import BaseHandler

env, cfg = load_env()
log = make_log("api/mpc")

MPC_ENDPOINT = cfg["app.mpc_endpoint"]
mpcheck_url = urllib.parse.urljoin(MPC_ENDPOINT, "cgi-bin/mpcheck.cgi")


async def detection_obscode(session, obj_id, date):
    nearest = (
        Photometry.select(session.user_or_token)
        .where(
            Photometry.obj_id == obj_id,
            Photometry.snr > PHOT_DETECTION_THRESHOLD,
        )
        .order_by(sa.func.abs(Photometry.mjd - date.mjd))
        .limit(1)
        .subquery()
    )
    obscode = await session.scalar(
        sa.select(Telescope.mpc_obscode)
        .join(Instrument, Instrument.telescope_id == Telescope.id)
        .join(nearest, nearest.c.instrument_id == Instrument.id)
    )
    return obscode or GEOCENTRIC_OBSCODE


def parse_date(date):
    if date is None:
        return Time.now()
    return Time(arrow.get(date).datetime, format="datetime")


class ObjMPCGetQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")

    date: str | None = Field(
        default=None,
        description="UTC date of the MPC query. Defaults to now.",
    )


class ObjMPCHandler(BaseHandler):
    @auth_or_token
    async def get(self, obj_id: str, *, query: ObjMPCGetQuery = None):
        """
        ---
        summary: Get an object's default MPC observatory code
        description: |
          Observatory code used when an MPC query does not give one: the code
          of the telescope that took the detection closest to the date, or the
          geocentric code when that telescope has none.
        tags:
          - objs
        parameters:
          - in: path
            name: obj_id
            required: true
            schema:
              type: string
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
        query = self.parse_query(ObjMPCGetQuery)
        try:
            date = parse_date(query.date)
        except (TypeError, arrow.ParserError):
            return self.error(f'Cannot parse time input value "{query.date}".')

        async with self.AsyncSession() as session:
            obj = await session.scalar(
                Obj.select(session.user_or_token).where(Obj.id == obj_id)
            )
            if obj is None:
                return self.error(f"Cannot find object with ID {obj_id}.")
            obscode = await detection_obscode(session, obj_id, date)
        return self.success(data={"obscode": obscode})

    @auth_or_token
    async def post(self, obj_id: str, *, body: ObjMPCPostBody = None):
        """
        ---
        summary: Crossmatch an object with MPC
        description: Retrieve an object's status from Minor Planet Center
        tags:
          - objs
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

        body = self.parse_body(ObjMPCPostBody)
        try:
            date = parse_date(body.date)
        except (TypeError, arrow.ParserError):
            return self.error(f'Cannot parse time input value "{body.date}".')

        limiting_magnitude = body.limiting_magnitude
        try:
            limiting_magnitude = float(limiting_magnitude)
        except Exception:
            return self.error("Cannot read in limiting magnitude.")

        search_radius = body.search_radius
        try:
            search_radius = float(search_radius)
        except Exception:
            return self.error("Cannot read in search radius.")

        async with self.AsyncSession() as session:
            obj = await session.scalar(
                Obj.select(session.user_or_token, mode="update").where(Obj.id == obj_id)
            )
            if obj is None:
                return self.error(f"Cannot find object with ID {obj_id}.")

            obscode = (body.obscode or "").strip() or await detection_obscode(
                session, obj_id, date
            )

            year = date.strftime("%Y")
            month = date.strftime("%m")
            hour = int(date.strftime("%H"))
            minute = int(date.strftime("%M"))
            second = float(date.strftime("%S.%f"))
            day = f"{int(date.strftime('%d')) + (hour + minute / 60 + second / 3600) / 24:.2f}"

            ra = Angle(obj.ra, unit="degree")
            ra_hms = ra.to_string(
                unit="hourangle", sep=" ", precision=2, pad=True
            ).split(" ")
            dec = Angle(obj.dec, unit="degree")
            dec_dms = dec.to_string(unit=u.deg, sep=" ", precision=2, pad=True).split(
                " "
            )

            params = {
                "year": year,
                "month": month,
                "day": day,
                "which": "pos",
                "ra": f"{ra_hms[0]}+{ra_hms[1]}+{ra_hms[2]}",
                "decl": f"{dec_dms[0]}+{dec_dms[1]}+{dec_dms[2]}",
                "TextArea": "",
                "radius": search_radius,
                "limit": limiting_magnitude,
                "oc": obscode,
                "sort": "d",
                "mot": "h",
                "tmot": "s",
                "pdes": "u",
                "needed": "f",
                "ps": "n",
                "type": "p",
            }

            url = f"{mpcheck_url}?{urllib.parse.urlencode(params)}"
            url = url.replace("%2B", "+")

            IOLoop.current().run_in_executor(
                None,
                lambda: query_mpc(obj_id, self.associated_user_object.id, url),
            )

            return self.success(data={"obscode": obscode})


# Row: "<designation>  <RA hh mm ss.s>  <Dec ±dd mm ss>  ...".
_MPC_ROW = re.compile(
    r"^(?P<desig>.+?)\s+\d{2} \d{2} \d{2}\.\d\s+[-+]\d{2} \d{2} \d{2}\b"
)


def _parse_mpc_designation(pre_text):
    """First minor-planet designation in an MPChecker <pre> block, or None."""
    for line in pre_text.splitlines():
        match = _MPC_ROW.match(line)
        if match:
            return match.group("desig").strip()
    return None


def query_mpc(obj_id, user_id, url):
    """Query MPC for a given object.
    obj_id : str
        Object ID
    user_id : int
        SkyPortal ID of User posting the MPC result
    url : str
        MPC query URL
    """

    session = new_session()

    log(f"Querying MPC for {obj_id}: {url}")

    try:
        user = session.get(User, user_id)

        obj = session.scalars(Obj.select(user).where(Obj.id == obj_id)).first()

        requests_session = requests.Session()
        response = requests_session.get(url)

        # Matches are the data rows inside <pre>; empty <pre> means none.
        pre = re.search(r"<pre>(.*?)</pre>", response.text, re.DOTALL)
        mpc_name = _parse_mpc_designation(pre.group(1)) if pre else None

        if mpc_name is not None:
            log(f"{obj_id}: identified MPC name {mpc_name}")
            obj.is_roid = True
            obj.mpc_name = mpc_name
            session.commit()
        elif pre is not None:
            log(f"{obj_id}: No known minor planets")
            obj.is_roid = False
            session.commit()
        else:
            log(f"Message from MPC for {obj_id} not parsable: {response.text}")

        flow = Flow()
        flow.push(
            "*",
            "skyportal/REFRESH_SOURCE",
            payload={"obj_key": obj.internal_key},
        )
        # Also refresh the scanning-page card in place, if shown.
        flow.push(
            "*",
            "skyportal/REFRESH_CANDIDATE",
            payload={"id": obj.internal_key},
        )

    except Exception as e:
        log(f"Error checking MPC for {obj_id}: {(str(e))}")
        session.rollback()
    finally:
        session.close()
