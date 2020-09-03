from . import FollowUpAPI
from baselayer.app.env import load_env
from datetime import datetime, timedelta
import json
import requests
from requests_toolbelt.utils import dump

env, cfg = load_env()


def convert_request_to_sedm(request, method_value='new'):
    photometry = sorted(request.obj.photometry, key=lambda p: p.mjd, reverse=True)
    photometry_payload = {}

    for p in photometry:
        if (
            p.filter.startswith('ztf')
            and p.filter not in photometry_payload
            and p.mag is not None
        ):
            # using filter[-1] as SEDM expects the bandpass name without "ZTF"
            photometry_payload[p.filter[-1]] = {
                'jd': p.mjd + 2_400_000.5,
                'mag': p.mag,
                'obsdate': p.iso.date().isoformat(),
            }

    rtype = request.payload['observation_type']
    if rtype == 'IFU':
        filters = ''
        followup = 'IFU'
    elif rtype == '3-shot (gri)':
        filters = 'g,r,i'
        followup = ''
    elif rtype == '4-shot (ugri)':
        filters = 'u,g,r,i'
        followup = ''
    elif rtype == '4-shot+IFU':
        filters = 'u,g,r,i'
        followup = 'IFU'
    elif rtype == '3-shot+IFU':
        filters = 'g,r,i'
        followup = 'IFU'
    elif rtype == "Mix 'n Match":
        choices = request.payload['observation_choices']
        hasspec = 'IFU' in choices
        followup = 'IFU' if hasspec else ''
        if hasspec:
            choices.remove('IFU')
        filters = ','.join(choices)
    else:
        raise ValueError('Cannot coerce payload into SEDM format.')

    payload = {
        'Filters': filters,
        'Followup': followup,
        'email': request.requester.contact_email,
        'enddate': request.payload['end_date'],
        'startdate': request.payload['start_date'],
        'prior_photometry': photometry_payload,
        'priority': request.payload['priority'],
        'programname': request.allocation.group.name,
        'requestid': request.id,
        'sourceid': request.obj_id,
        'sourcename': request.obj_id,
        'status': method_value,
        'username': request.requester.username,
    }

    return payload


class SEDMAPI(FollowUpAPI):
    """SkyPortal interface to the Spectral Energy Distribution machine (SEDM)."""

    @staticmethod
    def submit(request):
        """Submit a follow-up request to SEDM."""
        from ..models import DBSession, FollowupRequestHTTPRequest

        payload = convert_request_to_sedm(request, method_value='new')
        content = json.dumps(payload)
        r = requests.post(
            cfg['app.sedm_endpoint'], files={'jsonfile': ('jsonfile', content)},
        )

        if r.status_code == 200:
            request.status = 'submitted'
        else:
            request.status = f'rejected: {r.content}'

        message = FollowupRequestHTTPRequest(
            content=dump.dump_all(r).decode('utf-8'),
            origin='skyportal',
            request=request,
        )
        DBSession().add(message)
        DBSession().add(request)
        DBSession().commit()

    @staticmethod
    def delete(request):
        """Delete a follow-up request from SEDM queue."""
        from ..models import DBSession, FollowupRequest

        payload = convert_request_to_sedm(request, method_value='delete')
        content = json.dumps(payload)
        r = requests.post(
            cfg['app.sedm_endpoint'], files={'jsonfile': ('jsonfile', content)},
        )

        r.raise_for_status()

        DBSession().query(FollowupRequest).filter(
            FollowupRequest.id == request.id
        ).delete()
        DBSession().commit()

    @staticmethod
    def update(request):
        """Update a request in the SEDM queue."""
        from ..models import DBSession, FollowupRequestHTTPRequest

        payload = convert_request_to_sedm(request, method_value='edit')
        content = json.dumps(payload)
        r = requests.post(
            cfg['app.sedm_endpoint'], files={'jsonfile': ('jsonfile', content)},
        )

        if r.status_code == 200:
            request.status = 'submitted'
        else:
            request.status = f'rejected: {r.content}'

        message = FollowupRequestHTTPRequest(
            content=dump.dump_all(r).decode('utf-8'),
            origin='skyportal',
            request=request,
        )
        DBSession().add(message)
        DBSession().add(request)
        DBSession().commit()

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
