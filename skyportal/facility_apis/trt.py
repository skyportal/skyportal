import base64
import json
import os
from datetime import datetime, timedelta
import sqlalchemy as sa

import requests
from astropy.time import Time, TimeDelta
from astropy.coordinates import SkyCoord
import astropy.units as u
import urllib
from urllib.parse import urlparse

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
        filt not in ["B", "V", "R", "I", "Rc", "Ic"]
        for filt in request.payload["observation_choices"]
    ):
        raise ValueError(
            f'Filter configuration {request.payload["observation_choices"]} unknown.'
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


def download_observations(request_id, urls):
    """Fetch data from the TRT API.
    request_id : int
        SkyPortal ID for request
    urls : List[str]
        List of image URLs from TRT archive
    """

    from ..models import (
        Comment,
        DBSession,
        FollowupRequest,
        Group,
    )

    with DBSession() as session:
        try:
            req = session.scalar(
                sa.select(FollowupRequest).where(FollowupRequest.id == request_id)
            )

            group_ids = [g.id for g in req.requester.accessible_groups]
            groups = session.scalars(
                Group.select(req.requester).where(Group.id.in_(group_ids))
            ).all()
            for url in urls:
                url_parse = urlparse(url)
                attachment_name = os.path.basename(url_parse.path)
                try:
                    with urllib.request.urlopen(url) as f:
                        attachment_bytes = base64.b64encode(f.read())
                    comment = Comment(
                        text=f'TRT: {attachment_name}',
                        obj_id=req.obj.id,
                        attachment_bytes=attachment_bytes,
                        attachment_name=attachment_name,
                        author=req.requester,
                        groups=groups,
                        bot=True,
                    )
                except Exception as e:
                    log(
                        f"TRT API Retrieve: unable to download data for {request_id}: {e}"
                    )
                    comment = Comment(
                        text=f'TRT: {attachment_name}, **failed to download** data [at this url]({url})',
                        obj_id=req.obj.id,
                        author=req.requester,
                        groups=groups,
                        bot=True,
                    )
                session.add(comment)
            req.status = f'{len(urls)} images posted as comment'
            session.commit()
        except Exception as e:
            session.rollback()
            log(f"Unable to post data for {request_id}: {e}")


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

            if r.status_code == 200 and 'token expired' in str(r.text):
                request.status = (
                    'rejected: API token specified in the allocation is expired.'
                )
            elif r.status_code == 200:
                request.status = 'submitted'
            else:
                request.status = f'rejected: {r.text}'

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

        try:
            flow = Flow()
            if kwargs.get('refresh_source', False):
                flow.push(
                    '*',
                    'skyportal/REFRESH_SOURCE',
                    payload={'obj_key': request.obj.internal_key},
                )
            if kwargs.get('refresh_requests', False):
                flow.push(
                    request.last_modified_by_id,
                    'skyportal/REFRESH_FOLLOWUP_REQUESTS',
                )
            if str(request.status) != 'submitted':
                flow.push(
                    request.last_modified_by_id,
                    'baselayer/SHOW_NOTIFICATION',
                    payload={
                        'note': f'Failed to submit TRT request: "{request.status}"',
                        'type': 'error',
                    },
                )
        except Exception as e:
            log(f'Failed to send notification: {e}')
            pass

    @staticmethod
    def get(request, session, **kwargs):
        """Get a follow-up request from TRT queue (all instruments).

        Parameters
        ----------
        request: skyportal.models.FollowupRequest
            The request to update from the queue and the SkyPortal database.
        session: sqlalchemy.Session
            Database session for this transaction
        """

        from ..models import FacilityTransaction, FollowupRequest
        from ..utils.asynchronous import run_async

        if cfg['app.trt_endpoint'] is not None:
            altdata = request.allocation.altdata

            if not altdata:
                raise ValueError('Missing allocation information.')

            req = session.scalar(
                sa.select(FollowupRequest).where(FollowupRequest.id == request.id)
            )

            url = f"{cfg['app.trt_endpoint']}/getfilepath"

            content = str(req.transactions[-1].response["content"])

            if 'token expired' in content:
                raise ValueError(
                    'Token expired, the request might have not been submitted correctly, or cannot be retrieved.'
                )

            try:
                content = json.loads(content)
            except json.JSONDecodeError:
                raise ValueError(
                    f'Unable to parse submission response from TRT: {content}'
                )

            uid = content[0]
            if not uid:
                raise ValueError('Unable to find observation ID in response from TRT.')

            payload = json.dumps({"obs_id": uid})

            headers = {
                'Content-Type': 'application/json',
                'TRT': altdata['token'],
            }
            r = requests.request("POST", url, headers=headers, data=payload)

            r.raise_for_status()

            if r.status_code == 200:
                try:
                    data = r.json()
                except json.JSONDecodeError:
                    raise ValueError(
                        f'Unable to parse retrieval response from TRT: {r.content}'
                    )

                urls = []

                if not isinstance(data.get('file_path', []), list):
                    raise ValueError(
                        f'Unexpected response from TRT, expected list of file paths, got {data.get("file_path", [])}'
                    )
                for file_path in data.get('file_path', []):
                    for key in file_path.keys():
                        calibrated = file_path[key].get('calibrated', '')
                        if calibrated:
                            urls.append(calibrated)

                if len(urls) > 0:
                    request.status = "complete"
                    run_async(download_observations, request.id, urls)
                else:
                    request.status = "pending"
            else:
                request.status = f'failed to retrieve: {r.content.decode()}'

        transaction = FacilityTransaction(
            request=http.serialize_requests_request(r.request),
            response=http.serialize_requests_response(r),
            followup_request=request,
            initiator_id=request.last_modified_by_id,
        )

        session.add(transaction)
        session.commit()

        try:
            flow = Flow()
            if kwargs.get('refresh_source', False):
                flow.push(
                    '*',
                    'skyportal/REFRESH_SOURCE',
                    payload={'obj_key': request.obj.internal_key},
                )
            if kwargs.get('refresh_requests', False):
                flow.push(
                    request.last_modified_by_id,
                    'skyportal/REFRESH_FOLLOWUP_REQUESTS',
                )
            if str(request.status) == 'pending':
                flow.push(
                    request.last_modified_by_id,
                    'baselayer/SHOW_NOTIFICATION',
                    payload={
                        'note': 'TRT request is still pending.',
                        'type': 'warning',
                    },
                )
            elif str(request.status).startswith('complete'):
                flow.push(
                    request.last_modified_by_id,
                    'baselayer/SHOW_NOTIFICATION',
                    payload={
                        'note': 'TRT request is complete, observations will be downloaded shortly.',
                        'type': 'info',
                    },
                )
            else:
                flow.push(
                    request.last_modified_by_id,
                    'baselayer/SHOW_NOTIFICATION',
                    payload={
                        'note': f'Failed to retrieve TRT request: "{request.status}"',
                        'type': 'error',
                    },
                )
        except Exception as e:
            log(f'Failed to send notification: {e}')
            pass

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

        from ..models import FacilityTransaction, FollowupRequest

        last_modified_by_id = request.last_modified_by_id
        obj_internal_key = request.obj.internal_key

        if cfg['app.trt_endpoint'] is not None:
            altdata = request.allocation.altdata

            if not altdata:
                raise ValueError('Missing allocation information.')

            req = session.scalar(
                sa.select(FollowupRequest).where(FollowupRequest.id == request.id)
            )

            url = f"{cfg['app.trt_endpoint']}/cancelobservation"

            content = str(req.transactions[-1].response["content"])
            if 'token expired' in content:
                request.status = 'failed to delete: API token specified in the allocation is expired.'
                session.commit()
            else:
                try:
                    content = json.loads(content)
                except json.JSONDecodeError:
                    raise ValueError(
                        f'Unable to parse submission response from TRT: {content}'
                    )

                uid = content[0]
                if not uid:
                    raise ValueError(
                        'Unable to find observation ID in response from TRT.'
                    )

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
                                "enum": ["SRO", "GAO"],
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

    form_json_schema_altdata = {
        "type": "object",
        "properties": {
            "token": {
                "type": "string",
                "title": "Token",
            },
        },
    }

    ui_json_schema = {"observation_choices": {"ui:widget": "checkboxes"}}
