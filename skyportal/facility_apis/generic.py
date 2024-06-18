from astropy.coordinates import SkyCoord
import astropy.units as u
from datetime import datetime, timedelta
import json
import requests
import textwrap

from baselayer.app.flow import Flow
from baselayer.app.env import load_env

from . import FollowUpAPI
from ..email_utils import send_email
from ..app_utils import get_app_base_url
from ..utils import http

env, cfg = load_env()

SLACK_URL = f"{cfg['slack.expected_url_preamble']}/services"

email = False
if cfg.get("email_service") == "sendgrid" or cfg.get("email_service") == "smtp":
    email = True


def validate_request(request, filters):
    """Validate FollowupRequest contents for queue.

    Parameters
    ----------
    request : skyportal.models.FollowupRequest
        The request to send to the instrument.
    filters : List[string]
        Filters allowed by instrument
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
        if filt not in filters:
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


def create_target_text(request, request_type='email', comments=False):
    """Payload json for SLACK / email queue requests.

    Parameters
    ----------
    request : skyportal.models.FollowupRequest
        The request to add to the queue and the SkyPortal database.
    request_type : str
        Type of request. Must be either email or slack.
    comments : bool
        Include comments in notification. Defaults to False.

    Returns
    ----------
    text : str
        String which summarizes the request payload. Payload includes
          name: object name
          instrument_request: instrument name
          ra: right ascension in decimal degrees
          dec: declination in decimal degrees
          filters: comma delimited list of filters
          exposure_time: exposure time requested in seconds
          exposure_counts: number of exposures requested
          username: SkyPortal username of requester
    """

    # The target of the observation
    target = {
        'name': request.obj.id,
        'instrument_request': request.allocation.instrument.name,
        'ra': f"{request.obj.ra:.5f}",
        'dec': f"{request.obj.dec:.5f}",
        'filters': ",".join(request.payload["observation_choices"]),
        'exposure_time': request.payload["exposure_time"],
        'exposure_counts': request.payload["exposure_counts"],
        'username': request.requester.username,
    }

    c = SkyCoord(ra=request.obj.ra * u.degree, dec=request.obj.dec * u.degree)

    app_url = get_app_base_url()
    skyportal_url = f"{app_url}/source/{request.obj.id}"

    if request_type == 'email':
        linebreak = "<br>"
    elif request_type == 'slack':
        linebreak = "\n"
    else:
        raise ValueError('request_type must be either email or slack')

    text = (
        f"Name: {target['name']}{linebreak}"
        f"SkyPortal Link: {skyportal_url}{linebreak}"
        f"RA / Dec: {c.ra.to_string(sep=':')} {c.dec.to_string(sep=':')} ({target['ra']} {target['dec']}){linebreak}"
        f"Filters: {target['filters']}{linebreak}"
        f"Exposure time: {target['exposure_time']}{linebreak}"
        f"Exposure counts: {target['exposure_counts']}{linebreak}"
        f"Username: {target['username']}"
    )

    if comments:
        if len(request.obj.comments) > 0:
            text_comments = [f"{linebreak}{linebreak}Comments:"]
            for comment in request.obj.comments:
                text_comments.append(f'{comment.author.username}: {comment.text}')
        else:
            text_comments = [f"{linebreak}{linebreak}No Comments"]

        text = text + f"{linebreak}".join(text_comments)

    return textwrap.dedent(text)


class GENERICAPI(FollowUpAPI):
    """SkyPortal interface for generic imaging follow-up"""

    @staticmethod
    def submit(request, session, **kwargs):
        """Submit a follow-up request to an instrument.

        Parameters
        ----------
        request: skyportal.models.FollowupRequest
            The request to submit.
        session: sqlalchemy.Session
            Database session for this transaction
        """

        from ..models import FacilityTransaction, Allocation

        if (
            getattr(request, 'allocation', None) is None
            and getattr(request, 'allocation_id', None) is None
        ):
            raise ValueError('No allocation associated with this request.')
        elif (
            getattr(request, 'allocation', None) is None
            and getattr(request, 'allocation_id', None) is not None
        ):
            allocation = session.scalars(
                Allocation.select(session.user_or_token).where(
                    Allocation.id == request.allocation_id
                )
            ).first()
            request.allocation = allocation

        validate_request(request, request.allocation.instrument.to_dict()["filters"])

        altdata = (
            request.allocation.altdata
            if getattr(request.allocation, 'altdata', None) not in [None, {}]
            else None
        )

        transaction = None
        if altdata is not None:
            if 'endpoint' in altdata and 'api_token' in altdata:
                payload = {
                    'obj_id': request.obj_id,
                    'allocation_id': request.allocation.id,
                    'payload': request.payload,
                }

                r = requests.post(
                    altdata['endpoint'],
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

            elif 'type' in altdata and altdata['type'] == 'slack':
                slack_microservice_url = (
                    f'http://127.0.0.1:{cfg["slack.microservice_port"]}'
                )

                if altdata.get('comments') in ["True", "t", "true", "1", True, 1]:
                    comments = True
                else:
                    comments = False

                text = create_target_text(
                    request, request_type='slack', comments=comments
                )

                data = json.dumps(
                    {
                        "url": f"{SLACK_URL}/{altdata['slack_workspace']}/{altdata['slack_channel']}/{altdata['slack_token']}",
                        "text": text,
                    }
                )

                r = requests.post(
                    slack_microservice_url,
                    data=data,
                    headers={'Content-Type': 'application/json'},
                )
                r.raise_for_status()

                request.status = 'submitted'

                transaction = FacilityTransaction(
                    request=http.serialize_requests_request(r.request),
                    response=http.serialize_requests_response(r),
                    followup_request=request,
                    initiator_id=request.last_modified_by_id,
                )

            elif 'type' in altdata and altdata['type'] == 'email':
                if email:
                    subject = f"{cfg['app.title']} - New observation request"

                    if altdata.get('comments') in ["True", "t", "true", "1", True, 1]:
                        comments = True
                    else:
                        comments = False

                    text = create_target_text(
                        request, request_type='email', comments=comments
                    )

                    send_email(
                        recipients=altdata['email'].split(","),
                        subject=subject,
                        body=text,
                    )

                    request.status = 'submitted'

                transaction = FacilityTransaction(
                    request=None,
                    response=None,
                    followup_request=request,
                    initiator_id=request.last_modified_by_id,
                )

            else:
                request.status = (
                    'rejected: missing endpoint or API token in allocation altdata'
                )
        else:
            request.status = 'submitted'

            transaction = FacilityTransaction(
                request=None,
                response=None,
                followup_request=request,
                initiator_id=request.last_modified_by_id,
            )

        if transaction is not None:
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
        """Delete a follow-up request from the instrument queue.

        Parameters
        ----------
        request: skyportal.models.FollowupRequest
            The request to delete from the queue and the SkyPortal database.
        session: sqlalchemy.Session
            Database session for this transaction
        """

        from ..models import DBSession, FollowupRequest, FacilityTransaction

        last_modified_by_id = request.last_modified_by_id
        obj_internal_key = request.obj.internal_key

        altdata = request.allocation.altdata
        has_valid_transaction = False
        if altdata:
            req = (
                DBSession()
                .query(FollowupRequest)
                .filter(FollowupRequest.id == request.id)
                .one()
            )
            if (
                getattr(req, 'transactions', None) is not None
                and getattr(req, 'transactions', None) != []
                and getattr(req.transactions[0], 'response', None) is not None
            ):
                content = req.transactions[0].response["content"]
                content = json.loads(content)

                uid = content["data"]["id"]

                r = requests.delete(
                    f"{altdata['endpoint']}/{uid}",
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
                has_valid_transaction = True

        if not has_valid_transaction:
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

    @staticmethod
    def update(request, session, **kwargs):
        """Update a request in the instrument queue.

        Parameters
        ----------
        request: skyportal.models.FollowupRequest
            The updated request.
        session: sqlalchemy.Session
            Database session for this transaction
        """

        from ..models import FacilityTransaction

        validate_request(request, request.allocation.instrument.to_dict()["filters"])

        altdata = request.allocation.altdata

        if altdata:
            payload = {
                'obj_id': request.obj_id,
                'allocation_id': request.allocation.id,
                'payload': request.payload,
            }

            r = requests.post(
                altdata['endpoint'],
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
        if kwargs.get('refresh_requests', False):
            flow = Flow()
            flow.push(
                request.last_modified_by_id,
                'skyportal/REFRESH_FOLLOWUP_REQUESTS',
            )

    def custom_json_schema(instrument, user, **kwargs):
        form_json_schema = {
            "type": "object",
            "properties": {
                "observation_choices": {
                    "type": "array",
                    "title": "Desired Observations",
                    "items": {
                        "type": "string",
                        "enum": instrument.to_dict()["filters"],
                    },
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
                    "format": "date",
                    "default": datetime.utcnow().date().isoformat(),
                    "title": "Start Date (UT)",
                },
                "end_date": {
                    "type": "string",
                    "format": "date",
                    "title": "End Date (UT)",
                    "default": (
                        datetime.utcnow().date() + timedelta(days=7)
                    ).isoformat(),
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

        return form_json_schema

    ui_json_schema = {"observation_choices": {"ui:widget": "checkboxes"}}

    alias_lookup = {
        'observation_choices': "Request",
        'start_date': "Start Date",
        'end_date': "End Date",
        'priority': "Priority",
        'observation_type': 'Mode',
    }
