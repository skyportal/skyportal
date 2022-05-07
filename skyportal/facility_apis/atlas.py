import requests
import json
from datetime import datetime, timedelta
from astropy.time import Time
import numpy as np
import pandas as pd
from io import StringIO
from sqlalchemy.orm import sessionmaker, scoped_session
from tornado.ioloop import IOLoop

from . import FollowUpAPI
from baselayer.app.env import load_env
from baselayer.app.flow import Flow
from baselayer.log import make_log

from ..utils import http

env, cfg = load_env()

if cfg['app.atlas.port'] is None:
    ATLAS_URL = f"{cfg['app.atlas.protocol']}://{cfg['app.atlas.host']}"
else:
    ATLAS_URL = (
        f"{cfg['app.atlas.protocol']}://{cfg['app.atlas.host']}:{cfg['app.atlas.port']}"
    )

log = make_log('facility_apis/atlas')


class ATLASRequest:

    """A dictionary structure for ATLAS forced photometry requests."""

    def _build_payload(self, request):
        """Payload json for ATLAS forced photometry requests.

        Parameters
        ----------

        request : skyportal.models.FollowupRequest
            The request to add to the queue and the SkyPortal database.

        Returns
        ----------
        payload : dict
            payload for requests.
        """

        if "start_date" not in request.payload:
            raise ValueError('start_date is a required parameter')
        if "end_date" not in request.payload:
            raise ValueError('end_date is a required parameter')

        mjd_min = Time(request.payload["start_date"], format='iso').mjd
        mjd_max = Time(request.payload["end_date"], format='iso').mjd

        if mjd_max < mjd_min:
            raise ValueError('mjd_min must be smaller than mjd_max')

        target = {
            'ra': request.obj.ra,
            'dec': request.obj.dec,
            'mjd_min': mjd_min,
            'mjd_max': mjd_max,
            'send_email': False,
        }

        return target


def commit_photometry(json_response, altdata, request_id, instrument_id, user_id):
    """
    Commits ATLAS photometry to the database

    Parameters
    ----------
    json_response : dict
        response.json() from call to ATLAS photometry service.
    altdata: dict
        Contains ATLAS photometry api_token for the user
    request_id : int
        FollowupRequest SkyPortal ID
    instrument_id : int
        Instrument SkyPortal ID
    user_id: int
        User SkyPortal ID
    """

    from ..models import (
        DBSession,
        FollowupRequest,
        Instrument,
        User,
    )

    Session = scoped_session(sessionmaker(bind=DBSession.session_factory.kw["bind"]))
    session = Session()

    try:
        request = session.query(FollowupRequest).get(request_id)
        instrument = session.query(Instrument).get(instrument_id)
        user = session.query(User).get(user_id)

        result_url = json_response['result_url']
        request.status = f"Task is complete with results available at {result_url}"

        s = requests.get(
            result_url,
            headers={
                'Authorization': f"Token {altdata['api_token']}",
                'Accept': 'application/json',
            },
        )
        s.raise_for_status()

        # ATLAS response looks like
        """
     ###MJD          m      dm   uJy   duJy F err chi/N     RA       Dec        x        y     maj  min   phi  apfit mag5sig Sky   Obs
     59226.235875  16.177  0.012  1228   15 c  0  54.64 342.45960  51.26340  7768.79  7767.00 2.53 2.39 -63.4 -0.375 19.58 21.54 01a59226o0051c
     59228.242600  16.258  0.017  1140   20 c  0   7.87 342.45960  51.26340  2179.59  9252.78 3.41 3.09 -51.0 -0.396 19.28 21.28 02a59228o0102c
     59228.246262  16.582  0.021   846   18 c  0  28.37 342.45960  51.26340  2162.23  9213.32 3.53 3.25 -52.3 -0.366 19.14 21.26 02a59228o0110c
     59228.252679  16.451  0.019   954   18 c  0  13.76 342.45960  51.26340  2218.02  9291.76 3.34 3.03 -49.8 -0.389 19.17 21.24 02a59228o0124c
     59228.265532  17.223  0.049   469   23 c  0   3.90 342.45960  51.26340  2237.25  9167.94 4.31 3.88 -43.7 -0.473 18.95 21.20 02a59228o0152c
         """

        try:
            df = pd.read_csv(
                StringIO(s.text.replace("###MJD", "mjd")), delim_whitespace=True
            )
        except Exception as e:
            raise ValueError(f'Format of response not understood: {e.message}')

        desired_columns = {'mjd', 'RA', 'Dec', 'm', 'dm', 'mag5sig', 'F'}
        if not desired_columns.issubset(set(df.columns)):
            raise ValueError('Missing expected column')

        df.rename(
            columns={
                'RA': 'ra',
                'Dec': 'dec',
                'm': 'mag',
                'dm': 'magerr',
                'mag5sig': 'limiting_mag',
                'F': 'filter',
            },
            inplace=True,
        )
        cyan = df['filter'] == 'c'
        orange = df['filter'] == 'o'

        snr = df['uJy'] / df['duJy'] < 5

        df['filter'].loc[cyan] = 'atlasc'
        df['filter'].loc[orange] = 'atlaso'
        df['mag'].loc[snr] = None
        df['magerr'].loc[snr] = None

        iszero = df['duJy'] == 0.0
        df['mag'].loc[iszero] = None
        df['magerr'].loc[iszero] = None

        isnan = np.isnan(df['uJy'])
        df['mag'].loc[isnan] = None
        df['magerr'].loc[isnan] = None

        df = df.replace({np.nan: None})

        drop_columns = list(
            set(df.columns.values)
            - {'mjd', 'ra', 'dec', 'mag', 'magerr', 'limiting_mag', 'filter'}
        )

        df.drop(
            columns=drop_columns,
            inplace=True,
        )
        df['magsys'] = 'ab'

        data_out = {
            'obj_id': request.obj_id,
            'instrument_id': instrument.id,
            'group_ids': [g.id for g in user.accessible_groups],
            **df.to_dict(orient='list'),
        }

        from skyportal.handlers.api.photometry import add_external_photometry

        if len(df.index) > 0:
            add_external_photometry(data_out, request.requester)
            request.status = "Photometry committed to database"
        else:
            request.status = "No photometry to commit to database"

        session.add(request)
        session.commit()

        flow = Flow()
        flow.push(
            '*',
            "skyportal/REFRESH_SOURCE",
            payload={"obj_key": request.obj.internal_key},
        )

    except Exception as e:
        return log(f"Unable to commit photometry for {request_id}: {e}")
    finally:
        Session.remove()


class ATLASAPI(FollowUpAPI):

    """An interface to ATLAS forced photometry."""

    @staticmethod
    def get(request):

        """Get a forced photometry request result from ATLAS.

        Parameters
        ----------
        request : skyportal.models.FollowupRequest
            The request to add to the queue and the SkyPortal database.
        """

        from ..models import (
            DBSession,
            FollowupRequest,
            FacilityTransaction,
            Allocation,
            Instrument,
        )

        Session = scoped_session(
            sessionmaker(bind=DBSession.session_factory.kw["bind"])
        )
        session = Session()

        req = (
            session.query(FollowupRequest)
            .filter(FollowupRequest.id == request.id)
            .one()
        )

        instrument = (
            Instrument.query_records_accessible_by(req.requester)
            .join(Allocation)
            .join(FollowupRequest)
            .filter(FollowupRequest.id == request.id)
            .first()
        )

        altdata = request.allocation.altdata

        if not altdata:
            raise ValueError('Missing allocation information.')

        content = req.transactions[0].response["content"]
        content = json.loads(content)

        r = requests.get(
            content["url"],
            headers={
                'Authorization': f"Token {altdata['api_token']}",
                'Accept': 'application/json',
            },
        )

        if r.status_code == 200:
            try:
                json_response = r.json()
            except Exception:
                raise ('No JSON data returned in request')

            if json_response['finishtimestamp']:
                IOLoop.current().run_in_executor(
                    None,
                    lambda: commit_photometry(
                        json_response,
                        altdata,
                        req.id,
                        instrument.id,
                        request.requester.id,
                    ),
                )
                req.status = "Committing photometry to database"

            elif json_response['starttimestamp']:
                req.status = (
                    f"Task is running (started at {json_response['starttimestamp']})"
                )
            else:
                req.status = (
                    f"Waiting for job to start (queued at {json_response['timestamp']})"
                )
        else:
            req.status = f'error: {r.content}'

        transaction = FacilityTransaction(
            request=http.serialize_requests_request(r.request),
            response=http.serialize_requests_response(r),
            followup_request=req,
            initiator_id=req.last_modified_by_id,
        )

        session.add(transaction)
        session.commit()

    # subclasses *must* implement the method below
    @staticmethod
    def submit(request):

        """Submit a forced photometry request to ATLAS.

        Parameters
        ----------
        request: skyportal.models.FollowupRequest
            The request to add to the queue and the SkyPortal database.
        """

        from ..models import FacilityTransaction, DBSession

        req = ATLASRequest()
        requestgroup = req._build_payload(request)

        altdata = request.allocation.altdata
        if not altdata:
            raise ValueError('Missing allocation information.')

        r = requests.post(
            f"{ATLAS_URL}/forcedphot/queue/",
            headers={
                'Authorization': f"Token {altdata['api_token']}",
                'Accept': 'application/json',
            },
            data=requestgroup,
        )

        if r.status_code == 201:
            request.status = 'submitted'
        elif r.status_code == 429:
            request.status = f'throttled: {r.content}'
        else:
            request.status = f'rejected: {r.content}'

        transaction = FacilityTransaction(
            request=http.serialize_requests_request(r.request),
            response=http.serialize_requests_response(r),
            followup_request=request,
            initiator_id=request.last_modified_by_id,
        )

        DBSession().add(transaction)

    @staticmethod
    def delete(request):

        """Delete a photometry request from ATLAS API.

        Parameters
        ----------
        request: skyportal.models.FollowupRequest
            The request to delete from the queue and the SkyPortal database.
        """

        from ..models import DBSession, FollowupRequest

        DBSession().query(FollowupRequest).filter(
            FollowupRequest.id == request.id
        ).delete()
        DBSession().commit()

    form_json_schema = {
        "type": "object",
        "properties": {
            "start_date": {
                "type": "string",
                "default": str(datetime.utcnow() - timedelta(days=365)).replace(
                    "T", ""
                ),
                "title": "Start Date (UT)",
            },
            "end_date": {
                "type": "string",
                "title": "End Date (UT)",
                "default": str(datetime.utcnow()).replace("T", ""),
            },
        },
        "required": [
            "start_date",
            "end_date",
        ],
    }

    ui_json_schema = {}
