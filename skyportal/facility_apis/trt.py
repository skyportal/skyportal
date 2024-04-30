import json
from datetime import datetime, timedelta

import requests
from astropy.time import Time, TimeDelta
from astropy.coordinates import SkyCoord
import astropy.units as u

from baselayer.app.env import load_env
from baselayer.app.flow import Flow
from baselayer.log import make_log

from ..utils import http
from . import FollowUpAPI

env, cfg = load_env()

log = make_log('facility_apis/trt')


def validate_request_to_trt(request):
    """Validate FollowupRequest contents for TRT queue.

    Parameters
    ----------
    request: skyportal.models.FollowupRequest
        The request to send to TRT.
    """

    for param in [
        "observation_choices",
        "exposure_time",
        "maximum_airmass",
        "station_name",
        "start_date",
        "end_date",
    ]:
        if param not in request.payload:
            raise ValueError(f'Parameter {param} required.')

    if any(
        filt not in ["B", "V", "R", "I"]
        for filt in request.payload["observation_choices"]
    ):
        raise ValueError(
            f'Filter configuration {request.payload["observation_choice"]} unknown.'
        )

    if request.payload["station_name"] not in ["SRO", "GAO", "SBO"]:
        raise ValueError('observation_type must be SRO, GAO, or SBO')

    if request.payload["exposure_time"] < 0:
        raise ValueError('exposure_time must be positive.')

    if request.payload["maximum_airmass"] < 1:
        raise ValueError('maximum_airmass must be at least 1.')

    coord = SkyCoord(request.obj.ra, request.obj.dec, unit="deg")
    ra_str = coord.ra.to_string(unit='hour', sep=':', precision=2, pad=True)
    dec_str = coord.dec.to_string(unit='degree', sep=':', precision=2, pad=True)

    tstart = Time(request.payload["start_date"] + 'T00:00:00', format="isot")
    tend = Time(request.payload["end_date"] + 'T00:00:00', format="isot")
    expired = tend + TimeDelta(1 * u.day)

    requestgroup = {
        "ObjectName": request.obj.id,
        "StationName": request.payload['station_name'],
        "RA": ra_str,
        "DEC": dec_str,
        "Subframe": "1",
        "BinningXY": "1,1",
        "CadenceInterval": "00:00:00",
        "MaxAirmass": request.payload["maximum_airmass"],
        "PA": "0",
        "Dither": "0",
        "ExpiryDate": expired.iso,
        "StartDate": tstart.iso,
        "EndDate": tend.iso,
        "ExposuresMode": "1",
        "M3Port": "1",
        "Filter": request.payload["observation_choices"],
        "Suffix": [
            f"{request.obj.id}_{filt}"
            for filt in request.payload["observation_choices"]
        ],
        "Exposure": [str(request.payload["exposure_time"])]
        * len(request.payload["observation_choices"]),
        "Repeat": [str(request.payload["exposure_counts"])]
        * len(request.payload["observation_choices"]),
    }

    return requestgroup


class TRTAPI(FollowUpAPI):
    """SkyPortal interface to the Thai Robotic Telescope"""

    @staticmethod
    def submit(request, session, **kwargs):
        """Submit a follow-up request to TRT.

        Parameters
        ----------
        request: skyportal.models.FollowupRequest
            The request to submit.
        session: sqlalchemy.Session
            Database session for this transaction
        """

        from ..models import FacilityTransaction

        requestgroup = validate_request_to_trt(request)

        if cfg['app.trt_endpoint'] is not None:
            altdata = request.allocation.altdata

            if not altdata:
                raise ValueError('Missing allocation information.')

            headers = {
                'Content-Type': 'application/json',
                'TRT': altdata['token'],
            }
            payload = json.dumps({"script": [requestgroup]})
            url = f"{cfg['app.trt_endpoint']}/newobservation"

            r = requests.request(
                "POST",
                url,
                data=payload,
                headers=headers,
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
        if kwargs.get('refresh_requests', False):
            flow = Flow()
            flow.push(
                request.last_modified_by_id,
                'skyportal/REFRESH_FOLLOWUP_REQUESTS',
            )

    @staticmethod
    def delete(request, session, **kwargs):
        """Delete a follow-up request from TRT queue.

        Parameters
        ----------
        request: skyportal.models.FollowupRequest
            The request to delete from the queue and the SkyPortal database.
        session: sqlalchemy.Session
            Database session for this transaction
        """

        from ..models import DBSession, FacilityTransaction, FollowupRequest

        last_modified_by_id = request.last_modified_by_id
        obj_internal_key = request.obj.internal_key

        if cfg['app.trt_endpoint'] is not None:
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

            url = f"{cfg['app.trt_endpoint']}/cancelobservation"

            content = req.transactions[0].response["content"]
            content = json.loads(content)
            uid = content[0]

            payload = json.dumps({"obs_id": [uid]})

            headers = {
                'Content-Type': 'application/json',
                'TRT': altdata['token'],
            }
            r = requests.request("POST", url, headers=headers, data=payload)

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

    form_json_schema = {
        "type": "object",
        "properties": {
            "station_name": {
                "type": "string",
                "enum": ["SRO", "GAO", "SBO"],
                "default": "SRO",
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
            "maximum_airmass": {
                "title": "Maximum Airmass (1-3)",
                "type": "number",
                "default": 2.0,
                "minimum": 1,
                "maximum": 3,
            },
        },
        "required": [
            "start_date",
            "end_date",
            "maximum_airmass",
            "station_name",
        ],
        "dependencies": {
            "station_name": {
                "oneOf": [
                    {
                        "properties": {
                            "station_name": {
                                "enum": ["SRO"],
                            },
                            "observation_choices": {
                                "type": "array",
                                "title": "Desired Observations",
                                "items": {
                                    "type": "string",
                                    "enum": ["B", "V", "R", "I"],
                                },
                                "uniqueItems": True,
                                "minItems": 1,
                            },
                        },
                    },
                    {
                        "properties": {
                            "station_name": {
                                "enum": ["GAO"],
                            },
                            "observation_choices": {
                                "type": "array",
                                "title": "Desired Observations",
                                "items": {
                                    "type": "string",
                                    "enum": ["B", "V", "R", "I"],
                                },
                                "uniqueItems": True,
                                "minItems": 1,
                            },
                        },
                    },
                    {
                        "properties": {
                            "station_name": {
                                "enum": ["SBO"],
                            },
                            "observation_choices": {
                                "type": "array",
                                "title": "Desired Observations",
                                "items": {
                                    "type": "string",
                                    "enum": ["B", "V", "Rc", "Ic"],
                                },
                                "uniqueItems": True,
                                "minItems": 1,
                            },
                        },
                    },
                ],
            },
        },
    }

    ui_json_schema = {"observation_choices": {"ui:widget": "checkboxes"}}
