import astropy
import requests
import numpy as np

from . import FollowUpAPI
from baselayer.app.env import load_env

from ..utils import http

env, cfg = load_env()

PS1_URL = cfg['app.ps1_endpoint']


class PS1API(FollowUpAPI):

    """An interface to PS1 forced photometry."""

    @staticmethod
    def get(request):

        """Get a forced photometry request result from PS1.

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

        content = req.transactions[0].response["content"]
        tab = astropy.io.ascii.read(content)
        objid = tab['objID'][0]

        params = {
            'objID': objid,
            'columns': [
                'detectID',
                'filterID',
                'obsTime',
                'ra',
                'dec',
                'psfFlux',
                'psfFluxerr',
                'psfQfPerfect',
            ],
        }

        url = f"{PS1_URL}/dr2/detections.csv"
        r = requests.get(url, params=params)
        r.raise_for_status()

        if r.status_code == 200:
            tab = astropy.io.ascii.read(r.text)
            # good data only
            tab = tab[tab['psfQfPerfect'] > 0.9]
            id2filter = np.array(['ps1::g', 'ps1::r', 'ps1::i', 'ps1::z', 'ps1::y'])
            tab['filter'] = id2filter[(tab['filterID'] - 1).data.astype(int)]
            df = tab.to_pandas()

            df.rename(
                columns={
                    'obsTime': 'mjd',
                    'psfFlux': 'flux',
                    'psfFluxerr': 'fluxerr',
                },
                inplace=True,
            )
            df = df.replace({np.nan: None})

            df.drop(
                columns=[
                    'detectID',
                    'filterID',
                    'psfQfPerfect',
                ],
                inplace=True,
            )
            df['magsys'] = 'ab'
            df['zp'] = 8.90

            data_out = {
                'obj_id': request.obj_id,
                'instrument_id': instrument.id,
                'group_ids': 'all',
                **df.to_dict(orient='list'),
            }
            token_id = "9a5e8bbf-373f-43d0-86b2-0c65b10fef31"

            t = requests.post(
                "http://localhost:5000/api/photometry",
                json=data_out,
                headers={"Authorization": f"token {token_id}"},
            )
            t.raise_for_status()

            request.status = "Photometry committed to database"
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

        """Submit a photometry request to PS1.

        Parameters
        ----------
        request: skyportal.models.FollowupRequest
            The request to add to the queue and the SkyPortal database.
        """

        from ..models import FacilityTransaction, DBSession

        params = {
            'ra': request.obj.ra,
            'dec': request.obj.dec,
            'radius': request.payload["radius"] / 3600.0,
            'nDetections.gt': request.payload["min_detections"],
            'columns': [
                'objID',
                'raMean',
                'decMean',
                'nDetections',
                'gMeanPSFMag',
                'rMeanPSFMag',
                'iMeanPSFMag',
                'zMeanPSFMag',
                'yMeanPSFMag',
            ],
        }

        url = f"{PS1_URL}/dr2/mean.csv"
        r = requests.get(url, params=params)
        r.raise_for_status()
        tab = astropy.io.ascii.read(r.text)

        if len(tab) == 0:
            request.status = 'No DR2 source'
        else:
            request.status = 'Source available'

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
            "radius": {
                "type": "number",
                "default": 1.0,
                "minimum": 0.0,
                "maximum": 50.0,
                "title": "Query Radius [arcsec]",
            },
            "min_detections": {
                "type": "number",
                "default": 1.0,
                "minimum": 1.0,
                "maximum": 100.0,
                "title": "Minimum Number of Detections",
            },
        },
        "required": [
            "start_date",
            "end_date",
        ],
    }

    ui_json_schema = {}
