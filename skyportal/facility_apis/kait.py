import requests
from requests.auth import HTTPBasicAuth

from . import FollowUpAPI
from baselayer.app.env import load_env

from ..utils import http

env, cfg = load_env()


if cfg['app.kait.port'] is None:
    KAIT_URL = f"{cfg['app.kait.protocol']}://{cfg['app.kait.host']}"
else:
    KAIT_URL = (
        f"{cfg['app.kait.protocol']}://{cfg['app.kait.host']}:{cfg['app.kait.port']}"
    )


class KAITRequest:

    """A dictionary structure for KAIT ToO requests."""

    def _build_payload(self, request):
        """Payload json for KAIT queue requests.

        Parameters
        ----------

        request: skyportal.models.FollowupRequest
            The request to add to the queue and the SkyPortal database.

        Returns
        ----------
        payload: json
            payload for requests.
        """

        for filt in request.payload["observation_choices"]:
            if filt not in ["U", "g", "r", "i", "z", "B", "V", "R", "I"]:
                raise ValueError(f"Improper observation_choice {filt}")

        if request.payload["observation_type"] not in ["long", "short"]:
            raise ValueError(
                f"Improper observation_type {request.payload['observation_type']}"
            )

        # The target of the observation
        target = {
            'name': request.obj.id,
            'ra': "{:.5f}".format(request.obj.ra),
            'dec': "{:.5f}".format(request.obj.dec),
            'filters': "".join(request.payload["observation_choices"]),
            'exposure': request.payload["observation_type"],
        }

        return target


class KAITAPI(FollowUpAPI):

    """An interface to KAIT operations."""

    # subclasses *must* implement the method below
    @staticmethod
    def submit(request):

        """Submit a follow-up request to KAIT.

        Parameters
        ----------
        request: skyportal.models.FollowupRequest
            The request to add to the queue and the SkyPortal database.
        """

        from ..models import FacilityTransaction, DBSession

        req = KAITRequest()
        requestgroup = req._build_payload(request)

        altdata = request.allocation.altdata
        if not altdata:
            raise ValueError('Missing allocation information.')

        requestpath = f"{KAIT_URL}/cgi-bin/internal/process_kait_ztf_request.py"

        r = requests.post(
            requestpath,
            auth=HTTPBasicAuth(altdata['username'], altdata['password']),
            json=requestgroup,
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

        DBSession().add(transaction)

    form_json_schema = {
        "type": "object",
        "properties": {
            "observation_choices": {
                "type": "array",
                "title": "Desired Observations",
                "items": {
                    "type": "string",
                    "enum": ["U", "g", "r", "i", "z", "B", "V", "R", "I"],
                },
                "uniqueItems": True,
                "minItems": 1,
            },
            "observation_type": {
                "type": "string",
                "enum": ["long", "short"],
                "default": "long",
            },
        },
        "required": [
            "observation_choices",
            "observation_type",
        ],
    }

    ui_json_schema = {"observation_choices": {"ui:widget": "checkboxes"}}

    alias_lookup = {
        'observation_choices': "Request",
    }
