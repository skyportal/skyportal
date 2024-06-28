import json
import requests
import textwrap

from astropy.coordinates import SkyCoord
from astropy import units as u

from . import FollowUpAPI
from baselayer.app.env import load_env
from baselayer.app.flow import Flow

from ..app_utils import get_app_base_url
from ..utils import http

env, cfg = load_env()


SLACK_URL = f"{cfg['slack.expected_url_preamble']}/services"


class SLACKRequest:

    """A dictionary structure for SLACK ToO requests."""

    def _build_payload(self, request):
        """Payload json for SLACK queue requests.

        Parameters
        ----------
        request : skyportal.models.FollowupRequest
            The request to add to the queue and the SkyPortal database.

        Returns
        ----------
        payload : dict
            payload for requests. payload includes
              name: object name
              instrument_request: instrument name
              ra: right ascension in decimal degrees
              dec: declination in decimal degrees
              filters: comma delimited list of filters
              exposure_time: exposure time requested in seconds
              exposure_counts: number of exposures requested
              username: SkyPortal username of requester
        """

        for filt in request.payload["observation_choices"]:
            if filt not in request.instrument.to_dict()["filters"]:
                raise ValueError(f"Improper observation_choice {filt}")

        if (
            request.payload["exposure_time"] <= 0
            or request.payload["exposure_time"] >= 7200
        ):
            raise ValueError(
                "Exposure time must be greater than 0 or less than 2 hours"
            )

        if request.payload["exposure_counts"] <= 0:
            raise ValueError("Number of exposures must be greater than 0")

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
        text = (
            f"Name: {target['name']}\n"
            f"SkyPortal Link: {skyportal_url}\n"
            f"RA / Dec: {c.ra.to_string(sep=':')} {c.dec.to_string(sep=':')} ({target['ra']} {target['dec']})\n"
            f"Filters: {target['filters']}\n"
            f"Exposure time: {target['exposure_time']}\n"
            f"Exposure counts: {target['exposure_counts']}\n"
            f"Username: {target['username']}"
        )

        return target, textwrap.dedent(text)


class SLACKAPI(FollowUpAPI):
    """An interface to SLACK operations."""

    # subclasses *must* implement the method below
    @staticmethod
    def submit(request, session, **kwargs):
        """Submit a follow-up request to SLACK.

        Parameters
        ----------
        request : skyportal.models.FollowupRequest
            The request to add to the queue and the SkyPortal database.
        session: sqlalchemy.Session
            Database session for this transaction
        """

        from ..models import FacilityTransaction

        req = SLACKRequest()
        requestgroup, requesttext = req._build_payload(request)

        altdata = request.allocation.altdata

        if not altdata:
            raise ValueError('Missing allocation information.')

        slack_microservice_url = f'http://127.0.0.1:{cfg["slack.microservice_port"]}'

        data = json.dumps(
            {
                "url": f"{SLACK_URL}/{altdata['slack_workspace']}/{altdata['slack_channel']}/{altdata['slack_token']}",
                "text": requesttext,
            }
        )

        r = requests.post(
            slack_microservice_url,
            data=data,
            headers={'Content-Type': 'application/json'},
        )
        r.raise_for_status()

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
        from ..models import FollowupRequest

        last_modified_by_id = request.last_modified_by_id
        obj_internal_key = request.obj.internal_key

        if len(request.transactions) == 0:
            session.query(FollowupRequest).filter(
                FollowupRequest.id == request.id
            ).delete()
            session.commit()
        else:
            raise NotImplementedError(
                "Can't delete requests already sent successfully to Slack."
            )

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
            },
            "required": [
                "observation_choices",
                "exposure_time",
                "exposure_counts",
            ],
        }

        return form_json_schema

    ui_json_schema = {"observation_choices": {"ui:widget": "checkboxes"}}

    alias_lookup = {
        'observation_choices': "Request",
    }
