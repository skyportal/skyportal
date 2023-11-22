import requests
from datetime import datetime, timedelta
from astropy.time import Time
from marshmallow.exceptions import ValidationError
import numpy as np
import pandas as pd
from io import StringIO
from sqlalchemy.orm import sessionmaker, scoped_session

from . import FollowUpAPI
from baselayer.app.env import load_env
from baselayer.app.flow import Flow
from baselayer.log import make_log

from ..utils import http

env, cfg = load_env()

if cfg.get('app.atlas.port') is None:
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


def commit_photometry(
    json_response,
    altdata,
    request_id,
    instrument_id,
    user_id,
    parent_session=None,
    duplicates="error",
):
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
    user_id : int
        User SkyPortal ID
    parent_session : sqlalchemy.orm.session.Session
        Session to use for database transactions. If None, a new session will be created.
    """

    from ..models import (
        DBSession,
        FollowupRequest,
        Instrument,
    )

    if parent_session is None:
        Session = scoped_session(sessionmaker())
        if Session.registry.has():
            session = Session()
        else:
            session = Session(bind=DBSession.session_factory.kw["bind"])
    else:
        session = parent_session

    try:
        request = session.query(FollowupRequest).get(request_id)
        instrument = session.query(Instrument).get(instrument_id)
        allocation = request.allocation
        if not allocation:
            raise ValueError("Missing request's allocation information.")

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

        snr = df['uJy'] / df['duJy'] < 3

        df.loc[cyan, 'filter'] = 'atlasc'
        df.loc[orange, 'filter'] = 'atlaso'
        df.loc[snr, 'mag'] = None
        df.loc[snr, 'magerr'] = None

        iszero = df['duJy'] == 0.0
        df.loc[iszero, 'mag'] = None
        df.loc[iszero, 'magerr'] = None

        isnan = np.isnan(df['uJy'])
        df.loc[isnan, 'mag'] = None
        df.loc[isnan, 'magerr'] = None

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
        df['origin'] = 'fp'

        # data is visible to the group attached to the allocation
        # as well as to any of the allocation's default share groups
        data_out = {
            'obj_id': request.obj_id,
            'instrument_id': instrument.id,
            'group_ids': list(
                set(
                    [allocation.group_id] + allocation.default_share_group_ids
                    if allocation.default_share_group_ids
                    else []
                )
            ),
            **df.to_dict(orient='list'),
        }

        from skyportal.handlers.api.photometry import add_external_photometry

        if len(df.index) > 0:
            ids, _ = add_external_photometry(
                data_out, request.requester, duplicates=duplicates
            )
            if ids is None:
                raise ValueError('Failed to commit photometry')
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
        session.rollback()
        log(f"Unable to commit photometry for {request_id}: {e}")
        raise Exception(f"Unable to commit photometry for {request_id}: {e}")
    finally:
        if parent_session is None:
            session.close()
            Session.remove()


class ATLASAPI(FollowUpAPI):

    """An interface to ATLAS forced photometry."""

    # subclasses *must* implement the method below
    @staticmethod
    def submit(request, session, **kwargs):

        """Submit a forced photometry request to ATLAS.

        Parameters
        ----------
        request: skyportal.models.FollowupRequest
            The request to add to the queue and the SkyPortal database.
        session: sqlalchemy.Session
            Database session for this transaction
        """

        from ..models import FacilityTransaction, FacilityTransactionRequest

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
        content = r.json()

        if r.status_code == 201:
            request.status = 'submitted'

            request_body = {
                'method': 'GET',
                'endpoint': content["url"],
                'headers': {
                    'Authorization': f"Token {altdata['api_token']}",
                    'Accept': 'application/json',
                },
                'followup_request_id': request.id,
                'initiator_id': request.last_modified_by_id,
            }

            try:
                req = FacilityTransactionRequest(**request_body)
            except ValidationError as e:
                raise ValidationError(
                    'Invalid/missing parameters: ' f'{e.normalized_messages()}'
                )
            session.add(req)
            session.commit()

            facility_microservice_url = (
                f'http://127.0.0.1:{cfg["ports.facility_queue"]}'
            )
            requests.post(
                facility_microservice_url,
                json={
                    'request_id': req.id,
                    'followup_request_id': req.followup_request_id,
                },
            )

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

        session.add(transaction)

        if kwargs.get('refresh_source', False):
            flow = Flow()
            flow.push(
                '*',
                'skyportal/REFRESH_SOURCE',
                payload={'obj_key': request.obj.internal_key},
            )
        if kwargs.get('refresh_requests', False):
            flow = Flow()
            flow.push(
                request.last_modified_by_id,
                'skyportal/REFRESH_FOLLOWUP_REQUESTS',
            )

    @staticmethod
    def delete(request, session, **kwargs):

        """Delete a photometry request from ATLAS API.

        Parameters
        ----------
        request: skyportal.models.FollowupRequest
            The request to delete from the queue and the SkyPortal database.
        session: sqlalchemy.Session
            Database session for this transaction
        """

        from ..models import FacilityTransactionRequest

        last_modified_by_id = request.last_modified_by_id
        obj_internal_key = request.obj.internal_key

        transaction = (
            session.query(FacilityTransactionRequest)
            .filter(FacilityTransactionRequest.followup_request_id == request.id)
            .first()
        )
        if transaction is not None:
            if transaction.status == "complete":
                raise ValueError('Request already complete. Cannot delete.')
            session.delete(transaction)
        session.delete(request)
        session.commit()

        if kwargs.get('refresh_source', False):
            flow = Flow()
            flow.push(
                '*',
                'skyportal/REFRESH_SOURCE',
                payload={'obj_key': obj_internal_key},
            )
        if kwargs.get('refresh_requests', False):
            flow = Flow()
            flow.push(
                last_modified_by_id,
                'skyportal/REFRESH_FOLLOWUP_REQUESTS',
            )

    form_json_schema_forced_photometry = {
        "type": "object",
        "properties": {
            "start_date": {
                "type": "string",
                "default": str(datetime.utcnow() - timedelta(days=30)).replace("T", ""),
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
