from . import FollowUpAPI, Listener
from baselayer.app.env import load_env
from datetime import datetime, timedelta
import json
import requests

from ..utils import http

env, cfg = load_env()


class SEDMListener(Listener):

    schema = {
        'type': 'object',
        'properties': {'new_status': {'type': 'string',},},  # noqa: E231
        'required': ['new_status'],
    }

    @staticmethod
    def process_message(handler_instance):
        """Receive a POSTed message from SEDM.

        Parameters
        ----------
        message: skyportal.handlers.FacilityMessageHandler
           The instance of the handler that received the request.
        """

        from ..models import FollowupRequest, FacilityTransaction, DBSession

        data = handler_instance.get_json()
        request = FollowupRequest.query.get(int(data['followup_request_id']))
        request.status = data['new_status']

        transaction_record = FacilityTransaction(
            request=http.serialize_tornado_request(handler_instance),
            followup_request=request,
            initiator=handler_instance.associated_user_object,
        )

        DBSession().add(transaction_record)


def convert_request_to_sedm(request, method_value='new'):
    """Convert a FollowupRequest into a dictionary that can be directly
    submitted via HTTP to the SEDM queue.

    Parameters
    ----------
    request: skyportal.models.FollowupRequest
        The request to send to SEDM.

    method_value: 'new', 'edit', 'delete'
        The desired SEDM queue action.
    """

    from ..models import DBSession, UserInvitation, Invitation

    photometry = sorted(request.obj.photometry, key=lambda p: p.mjd, reverse=True)
    photometry_payload = {}

    for p in photometry:
        if (
            p.filter.startswith('ztf')
            and p.filter[-1] not in photometry_payload
            and p.mag is not None
        ):
            # using filter[-1] as SEDM expects the bandpass name without "ZTF"
            photometry_payload[p.filter[-1]] = {
                'jd': p.mjd + 2_400_000.5,
                'mag': p.mag,
                'obsdate': p.iso.date().isoformat(),
            }

    rtype = request.payload['observation_type']

    filtdict = {
        'IFU': '',
        '3-shot (gri)': 'g,r,i',
        '4-shot (ugri)': 'u,g,r,i',
        '4-shot+IFU': 'u,g,r,i',
        '3-shot+IFU': 'g,r,i',
    }

    if rtype == "Mix 'n Match":
        choices = request.payload['observation_choices']
        hasspec = 'IFU' in choices
        followup = 'IFU' if hasspec else ''
        if hasspec:
            choices.remove('IFU')
        filters = ','.join(choices)
    elif rtype in filtdict:
        filters = filtdict[rtype]
        followup = 'IFU' if 'IFU' in rtype else ''
    else:
        raise ValueError('Cannot coerce payload into SEDM format.')

    # default to user invitation email if preferred contact email has not been set
    email = request.requester.contact_email
    if email is None:
        invitation = (
            DBSession()
            .query(Invitation)
            .join(UserInvitation)
            .filter(
                UserInvitation.user_id == request.requester_id,
                Invitation.used.is_(True),
            )
            .first()
        )

        if invitation is not None:
            email = invitation.user_email
        else:
            # this should only be true in the CI test suite
            email = 'test_suite@skyportal.com'

    payload = {
        'Filters': filters,
        'Followup': followup,
        'email': email,
        'enddate': request.payload['end_date'],
        'startdate': request.payload['start_date'],
        'prior_photometry': photometry_payload,
        'priority': request.payload['priority'],
        'programname': request.allocation.group.name,
        'requestid': request.id,
        'sourceid': request.obj_id[:26],  # 26 characters is the max allowed by sedm
        'sourcename': request.obj_id[:26],
        'status': method_value,
        'username': request.requester.username,
        'ra': request.obj.ra,
        'dec': request.obj.dec,
    }

    return payload


class SEDMAPI(FollowUpAPI):
    """SkyPortal interface to the Spectral Energy Distribution machine (SEDM)."""

    @staticmethod
    def submit(request):
        """Submit a follow-up request to SEDM.

        Parameters
        ----------
        request: skyportal.models.FollowupRequest
            The request to submit.
        """

        from ..models import FacilityTransaction, DBSession

        payload = convert_request_to_sedm(request, method_value='new')
        content = json.dumps(payload)
        r = requests.post(
            cfg['app.sedm_endpoint'], files={'jsonfile': ('jsonfile', content)},
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

        DBSession().add(transaction)

    @staticmethod
    def delete(request):
        """Delete a follow-up request from SEDM queue.

        Parameters
        ----------
        request: skyportal.models.FollowupRequest
            The request to delete from the queue and the SkyPortal database.
        """

        from ..models import FacilityTransaction, DBSession

        payload = convert_request_to_sedm(request, method_value='delete')
        content = json.dumps(payload)
        r = requests.post(
            cfg['app.sedm_endpoint'], files={'jsonfile': ('jsonfile', content)},
        )

        r.raise_for_status()
        request.status = "deleted"

        transaction = FacilityTransaction(
            request=http.serialize_requests_request(r.request),
            response=http.serialize_requests_response(r),
            followup_request=request,
            initiator_id=request.last_modified_by_id,
        )

        DBSession().add(transaction)

    @staticmethod
    def update(request):
        """Update a request in the SEDM queue.

        Parameters
        ----------
        request: skyportal.models.FollowupRequest
            The updated request.
        """

        from ..models import FacilityTransaction, DBSession

        payload = convert_request_to_sedm(request, method_value='edit')
        content = json.dumps(payload)
        r = requests.post(
            cfg['app.sedm_endpoint'], files={'jsonfile': ('jsonfile', content)},
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

        DBSession().add(transaction)

    _observation_types = [
        '3-shot (gri)',
        '4-shot (ugri)',
        'IFU',
        '4-shot+IFU',
        '3-shot+IFU',
        "Mix 'n Match",
    ]

    _dependencies = [
        {"properties": {"observation_type": {"enum": [v], "title": "Mode"}}}
        for v in _observation_types[:-1]
    ]

    _dependencies.append(
        {
            "properties": {
                "observation_type": {"enum": _observation_types[-1:], "title": "Mode"},
                "observation_choices": {
                    "type": "array",
                    "title": "Desired Observations",
                    "items": {"type": "string", "enum": ["u", "g", "r", "i", "IFU"]},
                    "uniqueItems": True,
                    "minItems": 1,
                },
            },
            "required": ["observation_choices"],
        }
    )

    form_json_schema = {
        "type": "object",
        "properties": {
            "observation_type": {
                "type": "string",
                "enum": _observation_types,
                "title": "Mode",
                "default": "IFU",
            },
            "priority": {
                "type": "string",
                "enum": ["1", "2", "3", "4", "5"],
                "default": "1",
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
        "dependencies": {"observation_type": {"oneOf": _dependencies}},
        "required": ["observation_type", 'priority', "start_date", "end_date"],
    }

    ui_json_schema = {"observation_choices": {"ui:widget": "checkboxes"}}

    alias_lookup = {
        'observation_choices': "Request",
        'start_date': "Start Date",
        'end_date': "End Date",
        'priority': "Priority",
        'observation_type': 'Mode',
    }
