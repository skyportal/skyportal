from astropy.time import Time, TimeDelta
import json
import requests

from baselayer.app.flow import Flow
from baselayer.app.env import load_env

from . import FollowUpAPI
from ..utils import http

env, cfg = load_env()


def validate_request_to_sedmv2(request):
    """Validate FollowupRequest contents for SEDMv2 queue.

    Parameters
    ----------
    request: skyportal.models.FollowupRequest
        The request to send to SEDM.

    method_value: 'new', 'edit', 'delete'
        The desired SEDMv2 queue action.
    """

    for param in [
        "observation_choice",
        "exposure_time",
        "maximum_airmass",
        "minimum_lunar_distance",
        "priority",
        "start_date",
        "end_date",
        "observation_type",
        "too",
    ]:
        if param not in request.payload:
            raise ValueError(f'Parameter {param} required.')

    if request.payload["observation_choice"] not in ["IFU", "g", "r", "i", "z"]:
        raise ValueError(
            f'Filter configuration {request.payload["observation_choice"]} unknown.'
        )

    if request.payload["observation_type"] not in ["transient", "variable"]:
        raise ValueError('observation_type must be either transient or variable')

    if request.payload["exposure_time"] < 0:
        raise ValueError('exposure_time must be positive.')

    if request.payload["maximum_airmass"] < 1:
        raise ValueError('maximum_airmass must be at least 1.')

    if (
        request.payload["minimum_lunar_distance"] < 0
        or request.payload["minimum_lunar_distance"] > 180
    ):
        raise ValueError('minimum lunar distance must be within 0-180.')

    if request.payload["priority"] < 1 or request.payload["priority"] > 5:
        raise ValueError('priority must be within 1-5.')

    if request.payload["too"] not in ["Y", "N"]:
        raise ValueError('too must be Y or N')

    if (request.payload["observation_type"] == "variable") and (
        request.payload["frame_exposure_time"] not in [1, 2, 3, 5, 10, 15, 20, 25, 30]
    ):
        raise ValueError('frame_exposure_time must be [1, 2, 3, 5, 10, 15, 20, 25, 30]')


class SEDMV2API(FollowUpAPI):
    """SkyPortal interface to the Spectral Energy Distribution machine (SEDMv2)."""

    @staticmethod
    def submit(request, session, **kwargs):
        """Submit a follow-up request to SEDMv2.

        Parameters
        ----------
        request: skyportal.models.FollowupRequest
            The request to submit.
        session: sqlalchemy.Session
            Database session for this transaction
        """

        from ..models import FacilityTransaction

        validate_request_to_sedmv2(request)

        if cfg['app.sedmv2_endpoint'] is not None:
            altdata = request.allocation.altdata

            if not altdata:
                raise ValueError('Missing allocation information.')

            payload = {
                'obj_id': request.obj_id,
                'allocation_id': request.allocation.id,
                'payload': request.payload,
            }

            r = requests.post(
                cfg['app.sedmv2_endpoint'],
                json=payload,
                headers={"Authorization": f"token {altdata['api_token']}"},
            )

            if r.status_code == 200:
                request.status = 'submitted'
            else:
                request.status = f'rejected: {r.content}'

            transaction = FacilityTransaction(
                request=http.serialize_requests_request(r.request),
                response=http.serialize_requests_response(r),
                followup_request=request,
                initiator_id=request.last_modified_by_id,
            )
        else:
            request.status = 'submitted'

            transaction = FacilityTransaction(
                request=None,
                response=None,
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

    @staticmethod
    def delete(request, session):
        """Delete a follow-up request from SEDMv2 queue.

        Parameters
        ----------
        request: skyportal.models.FollowupRequest
            The request to delete from the queue and the SkyPortal database.
        session: sqlalchemy.Session
            Database session for this transaction
        """

        from ..models import DBSession, FollowupRequest, FacilityTransaction

        if cfg['app.sedmv2_endpoint'] is not None:
            altdata = request.allocation.altdata

            req = (
                DBSession()
                .query(FollowupRequest)
                .filter(FollowupRequest.id == request.id)
                .one()
            )

            altdata = request.allocation.altdata

            if not altdata:
                raise ValueError('Missing allocation information.')

            content = req.transactions[0].response["content"]
            content = json.loads(content)

            uid = content["data"]["id"]

            r = requests.delete(
                f"{cfg['app.sedmv2_endpoint']}/{uid}",
                headers={"Authorization": f"token {altdata['api_token']}"},
            )
            r.raise_for_status()
            request.status = "deleted"

            transaction = FacilityTransaction(
                request=http.serialize_requests_request(r.request),
                response=http.serialize_requests_response(r),
                followup_request=request,
                initiator_id=request.last_modified_by_id,
            )
        else:
            request.status = 'deleted'

            transaction = FacilityTransaction(
                request=None,
                response=None,
                followup_request=request,
                initiator_id=request.last_modified_by_id,
            )

        session.add(transaction)

        flow = Flow()
        flow.push(
            '*',
            'skyportal/REFRESH_SOURCE',
            payload={'obj_key': request.obj.internal_key},
        )

    @staticmethod
    def update(request, session):
        """Update a request in the SEDMv2 queue.

        Parameters
        ----------
        request: skyportal.models.FollowupRequest
            The updated request.
        session: sqlalchemy.Session
            Database session for this transaction
        """

        from ..models import FacilityTransaction

        validate_request_to_sedmv2(request)

        if cfg['app.sedmv2_endpoint'] is not None:
            altdata = request.allocation.altdata

            if not altdata:
                raise ValueError('Missing allocation information.')

            payload = {
                'obj_id': request.obj_id,
                'allocation_id': request.allocation.id,
                'payload': request.payload,
            }

            r = requests.post(
                cfg['app.sedmv2_endpoint'],
                json=payload,
                headers={"Authorization": f"token {altdata['api_token']}"},
            )

            if r.status_code == 200:
                request.status = 'submitted'
            else:
                request.status = f'rejected: {r.content}'

            transaction = FacilityTransaction(
                request=http.serialize_requests_request(r.request),
                response=http.serialize_requests_response(r),
                followup_request=request,
                initiator_id=request.last_modified_by_id,
            )
        else:
            request.status = 'submitted'

            transaction = FacilityTransaction(
                request=None,
                response=None,
                followup_request=request,
                initiator_id=request.last_modified_by_id,
            )

        session.add(transaction)

        flow = Flow()
        flow.push(
            '*',
            'skyportal/REFRESH_SOURCE',
            payload={'obj_key': request.obj.internal_key},
        )

    form_json_schema = {
        "type": "object",
        "properties": {
            "observation_choice": {
                "type": "string",
                "title": "Desired Observations",
                "enum": ["g", "r", "i", "z", "IFU"],
                "default": "IFU",
            },
            "exposure_time": {
                "title": "Exposure Time [s]",
                "type": "number",
                "default": 300.0,
            },
            "maximum_airmass": {
                "title": "Maximum Airmass (1-3)",
                "type": "number",
                "default": 2.0,
                "minimum": 1,
                "maximum": 3,
            },
            "minimum_lunar_distance": {
                "title": "Minimum Lunar Distance [deg] (0-180)",
                "type": "number",
                "default": 30.0,
                "minimum": 0,
                "maximum": 180,
            },
            "priority": {
                "type": "number",
                "default": 1.0,
                "minimum": 1.0,
                "maximum": 5.0,
                "title": "Priority",
            },
            "start_date": {
                "type": "string",
                "default": Time.now().isot,
                "title": "Start Date (UT)",
            },
            "end_date": {
                "type": "string",
                "title": "End Date (UT)",
                "default": (Time.now() + TimeDelta(7, format='jd')).isot,
            },
            "too": {
                "title": "Is this a Target of Opportunity observation?",
                "type": "string",
                "enum": [
                    "N",
                    "Y",
                ],
                "default": "N",
            },
            "observation_type": {
                "title": "What type of observation is this?",
                "type": "string",
                "enum": [
                    "transient",
                    "variable",
                ],
                "default": "transient",
            },
        },
        "required": [
            "observation_choice",
            "observation_type",
            "priority",
            "start_date",
            "end_date",
            "exposure_time",
            "maximum_airmass",
            "minimum_lunar_distance",
            "too",
        ],
        "dependencies": {
            "observation_type": {
                "oneOf": [
                    {
                        "properties": {
                            "observation_type": {
                                "enum": ["variable"],
                            },
                            "frame_exposure_time": {
                                "title": "Exposure time per frame (s)",
                                "enum": [1, 2, 3, 5, 10, 15, 20, 25, 30],
                                "default": 10,
                            },
                        },
                    },
                    {
                        "properties": {
                            "observation_type": {
                                "enum": ["transient"],
                            },
                        }
                    },
                ],
            },
        },
    }
    ui_json_schema = {}
    alias_lookup = {
        'observation_choice': "Request",
        'start_date': "Start Date",
        'end_date': "End Date",
        'priority': "Priority",
        'observation_type': 'Mode',
    }
