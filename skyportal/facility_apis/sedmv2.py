from datetime import datetime, timedelta
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
        "observation_choices",
        "exposure_time",
        "exposure_counts",
        "maximum_airmass",
        "minimum_lunar_distance",
        "priority",
        "start_date",
        "end_date",
    ]:
        if param not in request.payload:
            raise ValueError(f'Parameter {param} required.')

    for filt in request.payload["observation_choices"]:
        if filt not in ["IFU", "g", "r", "i", "z"]:
            raise ValueError(f'Filter configuration {filt} unknown.')

    if request.payload["exposure_time"] < 0:
        raise ValueError('exposure_time must be positive.')

    if request.payload["exposure_counts"] < 1:
        raise ValueError('exposure_counts must be at least 1.')

    if request.payload["maximum_airmass"] < 1:
        raise ValueError('maximum_airmass must be at least 1.')

    if (
        request.payload["minimum_lunar_distance"] < 0
        or request.payload["minimum_lunar_distance"] > 180
    ):
        raise ValueError('minimum lunar distance must be within 0-180.')

    if request.payload["priority"] < 1 or request.payload["priority"] > 5:
        raise ValueError('priority must be within 1-5.')


class SEDMV2API(FollowUpAPI):
    """SkyPortal interface to the Spectral Energy Distribution machine (SEDMv2)."""

    @staticmethod
    def submit(request, session):
        """Submit a follow-up request to SEDMv2.

        Parameters
        ----------
        request: skyportal.models.FollowupRequest
            The request to submit.
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
            "observation_choices": {
                "type": "array",
                "title": "Desired Observations",
                "items": {"type": "string", "enum": ["g", "r", "i", "z", "IFU"]},
                "uniqueItems": True,
                "minItems": 1,
            },
            "exposure_time": {
                "title": "Exposure Time [s]",
                "type": "number",
                "default": 300.0,
            },
            "exposure_counts": {
                "title": "Exposure Counts",
                "type": "number",
                "default": 1,
            },
            "maximum_airmass": {
                "title": "Maximum Airmass (1-3)",
                "type": "number",
                "default": 2.0,
                "minimum": 1,
                "maximum": 3,
            },
            "minimum_lunar_distance": {
                "title": "Maximum Lunar Distance [deg] (0-180)",
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
                "format": "date",
                "default": datetime.utcnow().date().isoformat(),
                "title": "Start Date (UT)",
            },
            "end_date": {
                "type": "string",
                "format": "date",
                "title": "End Date (UT)",
                "default": (datetime.utcnow().date() + timedelta(days=7)).isoformat(),
            },
        },
        "required": [
            "observation_choices",
            "priority",
            "start_date",
            "end_date",
            "exposure_time",
            "exposure_counts",
            "maximum_airmass",
            "minimum_lunar_distance",
        ],
    }

    ui_json_schema = {"observation_choices": {"ui:widget": "checkboxes"}}

    alias_lookup = {
        'observation_choices': "Request",
        'start_date': "Start Date",
        'end_date': "End Date",
        'priority': "Priority",
        'observation_type': 'Mode',
    }
