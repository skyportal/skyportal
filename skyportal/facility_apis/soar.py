import json
import requests
from datetime import datetime, timedelta

from . import FollowUpAPI
from baselayer.app.env import load_env
from baselayer.app.flow import Flow
from baselayer.log import make_log

from ..utils import http

env, cfg = load_env()

requestpath = f"{cfg['app.lco_protocol']}://{cfg['app.lco_host']}:{cfg['app.lco_port']}/api/requestgroups/"

log = make_log('facility_apis/soar')


class SOAR_GHTS_REDCAM_IMAGER_Request:

    """A JSON structure for SOAR GHTS REDCAM IMAGER requests."""

    def __init__(self, request):
        """Initialize SOAR GHTS REDCAM request.

        Parameters
        ----------

        request: skyportal.models.FollowupRequest
            The request to add to the queue and the SkyPortal database.

        """

        self.requestgroup = self._build_payload(request)

    def _build_payload(self, request):
        """Payload json for SOAR GHTS REDCAM IMAGER queue requests.

        Parameters
        ----------

        request: skyportal.models.FollowupRequest
            The request to add to the queue and the SkyPortal database.

        Returns
        ----------
        payload: json
            payload for requests.
        """

        # Constraints used for scheduling this observation
        constraints = {
            'max_airmass': request.payload["maximum_airmass"],
            'min_lunar_distance': request.payload["minimum_lunar_distance"],
        }

        # The target of the observation
        target = {
            'name': request.obj.id,
            'type': 'ICRS',
            'ra': request.obj.ra,
            'dec': request.obj.dec,
            'epoch': 2000,
        }

        exp_time = request.payload["exposure_time"]
        exp_count = int(request.payload["exposure_counts"])

        configurations = []
        for filt in request.payload['observation_choices']:
            configurations.append(
                {
                    'type': 'EXPOSE',
                    'instrument_type': 'SOAR_GHTS_REDCAM_IMAGER',
                    'constraints': constraints,
                    'target': target,
                    'acquisition_config': {},
                    'guiding_config': {},
                    'instrument_configs': [
                        {
                            'exposure_time': exp_time,
                            'exposure_count': exp_count,
                            'optical_elements': {'filter': '%s' % filt},
                        }
                    ],
                }
            )

        tstart = request.payload["start_date"] + ' 00:00:00'
        tend = request.payload["end_date"] + ' 00:00:00'

        windows = [{'start': tstart, 'end': tend}]

        # The telescope class that should be used for this observation
        location = {'telescope_class': '4m0'}

        altdata = request.allocation.altdata

        # The full RequestGroup, with additional meta-data
        requestgroup = {
            'name': '%s' % (request.obj.id),  # The title
            'proposal': altdata["PROPOSAL_ID"],
            'ipp_value': request.payload["priority"],
            'operator': 'SINGLE',
            'observation_type': request.payload["observation_mode"],
            'requests': [
                {
                    'configurations': configurations,
                    'windows': windows,
                    'location': location,
                }
            ],
        }

        return requestgroup


class SOAR_GHTS_REDCAM_Request:

    """A JSON structure for SOAR GHTS REDCAM requests."""

    def __init__(self, request):
        """Initialize SOAR GHTS REDCAM request.

        Parameters
        ----------

        request: skyportal.models.FollowupRequest
            The request to add to the queue and the SkyPortal database.

        """

        self.requestgroup = self._build_payload(request)

    def _build_payload(self, request):
        """Payload header for SOAR GHTS REDCAM queue requests.

        Parameters
        ----------

        request: skyportal.models.FollowupRequest
            The request to add to the queue and the SkyPortal database.

        Returns
        ----------
        payload: json
            payload for requests.
        """

        # Constraints used for scheduling this observation
        constraints = {
            'max_airmass': request.payload["maximum_airmass"],
            'min_lunar_distance': request.payload["minimum_lunar_distance"],
        }

        # The target of the observation
        target = {
            'name': request.obj.id,
            'type': 'ICRS',
            'ra': request.obj.ra,
            'dec': request.obj.dec,
            'epoch': 2000,
        }

        # The telescope class that should be used for this observation
        location = {'telescope_class': '4m0'}

        exp_time = request.payload["exposure_time"]
        exp_count = int(request.payload["exposure_counts"])

        configurations = [
            {
                'type': 'SPECTRUM',
                'instrument_type': 'SOAR_GHTS_REDCAM',
                'constraints': constraints,
                'target': target,
                'acquisition_config': {'mode': 'WCS'},
                'guiding_config': {'mode': 'ON', 'optional': False},
                'instrument_configs': [
                    {
                        'exposure_time': exp_time,
                        'exposure_count': exp_count,
                        'rotator_mode': 'VFLOAT',
                        'optical_elements': {'slit': 'slit_1.6as'},
                    }
                ],
            },
        ]

        tstart = request.payload["start_date"] + ' 00:00:00'
        tend = request.payload["end_date"] + ' 00:00:00'

        windows = [{'start': tstart, 'end': tend}]

        altdata = request.allocation.altdata

        # The full RequestGroup, with additional meta-data
        requestgroup = {
            'name': '%s' % (request.obj.id),  # The title
            'proposal': altdata["PROPOSAL_ID"],
            'ipp_value': request.payload["priority"],
            'operator': 'SINGLE',
            'observation_type': request.payload["observation_mode"],
            'requests': [
                {
                    'configurations': configurations,
                    'windows': windows,
                    'location': location,
                }
            ],
        }

        return requestgroup


class SOARAPI(FollowUpAPI):

    """An interface to SOAR operations."""

    @staticmethod
    def delete(request, session, **kwargs):
        """Delete a follow-up request from SOAR queue (all instruments).

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

        if len(request.transactions) == 0:
            session.query(FollowupRequest).filter(
                FollowupRequest.id == request.id
            ).delete()
            session.commit()
        else:
            altdata = request.allocation.altdata

            if not altdata:
                raise ValueError('Missing allocation information.')

            content = request.transactions[0].response["content"]
            content = json.loads(content)
            uid = content["id"]

            r = requests.post(
                f"{requestpath}{uid}/cancel/",
                headers={"Authorization": f'Token {altdata["API_TOKEN"]}'},
            )

            r.raise_for_status()
            request.status = "deleted"

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
                payload={'obj_key': obj_internal_key},
            )
        if kwargs.get('refresh_requests', False):
            flow = Flow()
            flow.push(
                last_modified_by_id,
                'skyportal/REFRESH_FOLLOWUP_REQUESTS',
            )


class SOARGHTSREDCAMIMAGERAPI(SOARAPI):

    """An interface to SOAR GHTS REDCAM IMAGER operations."""

    # subclasses *must* implement the method below
    @staticmethod
    def submit(request, session, **kwargs):
        """Submit a follow-up request to SOAR's GHTS REDCAM IMAGER.

        Parameters
        ----------
        request: skyportal.models.FollowupRequest
            The request to add to the queue and the SkyPortal database.
        session: sqlalchemy.Session
            Database session for this transaction
        """

        from ..models import FacilityTransaction

        altdata = request.allocation.altdata
        if not altdata:
            raise ValueError('Missing allocation information.')

        soarreq = SOAR_GHTS_REDCAM_IMAGER_Request(request)
        requestgroup = soarreq.requestgroup

        r = requests.post(
            requestpath,
            headers={"Authorization": f'Token {altdata["API_TOKEN"]}'},
            json=requestgroup,  # Make sure you use json!
        )

        if r.status_code == 201:
            request.status = 'submitted'
        else:
            if "non_field_errors" in r.json():
                error_message = r.json()["non_field_errors"]
            else:
                error_message = r.content.decode()
            request.status = error_message

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

    form_json_schema = {
        "type": "object",
        "properties": {
            "observation_mode": {
                "type": "string",
                "enum": ["NORMAL", "RAPID_RESPONSE", "TIME_CRITICAL"],
                "default": "NORMAL",
            },
            "observation_choices": {
                "type": "array",
                "title": "Desired Observations",
                "items": {"type": "string", "enum": ["gp", "rp", "ip", "zs"]},
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
            "minimum_lunar_distance": {
                "title": "Minimum Lunar Distance [deg.] (0-180)",
                "type": "number",
                "default": 30.0,
                "minimum": 0,
                "maximum": 180,
            },
            "priority": {
                "title": "IPP (0-2)",
                "type": "number",
                "default": 1.0,
                "minimum": 0,
                "maximum": 2,
            },
        },
        "required": [
            "start_date",
            "end_date",
            "maximum_airmass",
            "minimum_lunar_distance",
            "priority",
        ],
    }

    ui_json_schema = {"observation_choices": {"ui:widget": "checkboxes"}}


class SOARGHTSREDCAMAPI(SOARAPI):

    """An interface to SOAR's GHTS REDCAM operations."""

    # subclasses *must* implement the method below
    @staticmethod
    def submit(request, session, **kwargs):
        """Submit a follow-up request to SOAR's GHTS REDCAM.

        Parameters
        ----------
        request: skyportal.models.FollowupRequest
            The request to add to the queue and the SkyPortal database.
        session: sqlalchemy.Session
            Database session for this transaction
        """

        from ..models import FacilityTransaction

        altdata = request.allocation.altdata
        if not altdata:
            raise ValueError('Missing allocation information.')

        soarreq = SOAR_GHTS_REDCAM_Request(request)
        requestgroup = soarreq.requestgroup

        r = requests.post(
            requestpath,
            headers={"Authorization": f'Token {altdata["API_TOKEN"]}'},
            json=requestgroup,  # Make sure you use json!
        )

        if r.status_code == 201:
            request.status = 'submitted'
        else:
            if "non_field_errors" in r.json():
                error_message = r.json()["non_field_errors"]
            else:
                error_message = r.content.decode()
            request.status = error_message

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

    form_json_schema = {
        "type": "object",
        "properties": {
            "observation_mode": {
                "type": "string",
                "enum": ["NORMAL", "RAPID_RESPONSE", "TIME_CRITICAL"],
                "default": "NORMAL",
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
            "minimum_lunar_distance": {
                "title": "Minimum Lunar Distance [deg.] (0-180)",
                "type": "number",
                "default": 30.0,
                "minimum": 0,
                "maximum": 180,
            },
            "priority": {
                "title": "IPP (0-2)",
                "type": "number",
                "default": 1.0,
                "minimum": 0,
                "maximum": 2,
            },
        },
        "required": [
            "start_date",
            "end_date",
            "maximum_airmass",
            "minimum_lunar_distance",
            "priority",
        ],
    }

    ui_json_schema = {}
