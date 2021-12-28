import requests
import json
from datetime import datetime, timedelta
from astropy.time import Time
import numpy as np
import pandas as pd
from io import StringIO

from . import FollowUpAPI
from baselayer.app.env import load_env

from ..utils import http

env, cfg = load_env()

ATLAS_URL = cfg['app.atlas_endpoint']


class ATLASRequest:

    """A dictionary structure for ATLAS forced photometry requests."""

    def _build_payload(self, request):
        """Payload json for ATLAS forced photometry requests.

        Parameters
        ----------

        request: skyportal.models.FollowupRequest
            The request to add to the queue and the SkyPortal database.

        Returns
        ----------
        payload: json
            payload for requests.
        """

        mjd_min = Time(request.payload["start_date"], format='iso').mjd
        mjd_max = Time(request.payload["end_date"], format='iso').mjd

        target = {
            'ra': request.obj.ra,
            'dec': request.obj.dec,
            'mjd_min': mjd_min,
            'mjd_max': mjd_max,
            'send_email': False,
        }

        return target


class ATLASAPI(FollowUpAPI):

    """An interface to ATLAS forced photometry."""

    @staticmethod
    def get(request):

        """Get a forced photometry request result from ATLAS.

        Parameters
        ----------
        request: skyportal.models.FollowupRequest
            The request to add to the queue and the SkyPortal database.
        """

        from ..models import (
            DBSession,
            FollowupRequest,
            FacilityTransaction,
            Allocation,
            Instrument,
        )

        req = (
            DBSession()
            .query(FollowupRequest)
            .filter(FollowupRequest.id == request.id)
            .one()
        )

        instrument = (
            Instrument.query_records_accessible_by(request.requester)
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
        r.raise_for_status()

        if r.status_code == 200:
            if r.json()['finishtimestamp']:
                result_url = r.json()['result_url']
                request.status = (
                    f"Task is complete with results available at {result_url}"
                )

                s = requests.get(
                    result_url,
                    headers={
                        'Authorization': f"Token {altdata['api_token']}",
                        'Accept': 'application/json',
                    },
                )
                s.raise_for_status()
                df = pd.read_csv(
                    StringIO(s.text.replace("###", "")), delim_whitespace=True
                )
                df.rename(
                    columns={
                        'MJD': 'mjd',
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

                df['filter'].loc[cyan] = 'sdssg'
                df['filter'].loc[orange] = 'sdssr'
                df['mag'].loc[snr] = None
                df['magerr'].loc[snr] = None
                df = df.replace({np.nan: None})

                df.drop(
                    columns=[
                        'min',
                        'phi',
                        'uJy',
                        'chi/N',
                        'duJy',
                        'maj',
                        'Obs',
                        'apfit',
                        'x',
                        'y',
                        'Sky',
                        'err',
                    ],
                    inplace=True,
                )
                df['magsys'] = 'ab'

                data_out = {
                    'obj_id': request.obj_id,
                    'instrument_id': instrument.id,
                    'group_ids': 'all',
                    **df.to_dict(orient='list'),
                }
                token_id = "720504e1-f163-478b-b624-a96573a68cbb"

                t = requests.post(
                    "http://localhost:5000/api/photometry",
                    json=data_out,
                    headers={"Authorization": f"token {token_id}"},
                )
                t.raise_for_status()

                request.status = "Photometry committed to database"

            elif r.json()['starttimestamp']:
                request.status = (
                    f"Task is running (started at {r.json()['starttimestamp']})"
                )
            else:
                request.status = (
                    f"Waiting for job to start (queued at {r.json()['timestamp']})"
                )
        else:
            request.status = f'error: {r.content}'

        transaction = FacilityTransaction(
            request=http.serialize_requests_request(r.request),
            response=http.serialize_requests_response(r),
            followup_request=request,
            initiator_id=request.last_modified_by_id,
        )

        DBSession().add(transaction)

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
            f"{ATLAS_URL}/queue/",
            headers={
                'Authorization': f"Token {altdata['api_token']}",
                'Accept': 'application/json',
            },
            data=requestgroup,
        )
        r.raise_for_status()

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
