import json
import requests
from datetime import datetime, timedelta

from . import FollowUpAPI
from baselayer.app.env import load_env

from ..utils import http

env, cfg = load_env()


requestpath = f"{cfg['app.lco_protocol']}://{cfg['app.lco_host']}:{cfg['app.lco_port']}/api/requestgroups/"


class SINISTRORequest:

    """A JSON structure for LCO 1m SINISTRO requests."""

    def __init__(self, request):
        """Initialize SINISTRO request.

        Parameters
        ----------

        request: skyportal.models.FollowupRequest
            The request to add to the queue and the SkyPortal database.

        """

        self.requestgroup = self._build_payload(request)

    def _build_payload(self, request):
        """Payload json for LCO 1m SINISTRO queue requests.

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
            'min_lunar_distance': 30,
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
                    'instrument_type': '1M0-SCICAM-SINISTRO',
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
        location = {'telescope_class': '1m0'}

        altdata = request.allocation.altdata

        # The full RequestGroup, with additional meta-data
        requestgroup = {
            'name': '%s' % (request.obj.id),  # The title
            'proposal': altdata["PROPOSAL_ID"],
            'ipp_value': request.payload["priority"],
            'operator': 'SINGLE',
            'observation_type': 'NORMAL',
            'requests': [
                {
                    'configurations': configurations,
                    'windows': windows,
                    'location': location,
                }
            ],
        }

        return requestgroup


class SPECTRALRequest:

    """A JSON structure for LCO 2m SPECTRAL requests."""

    def __init__(self, request):
        """Initialize SPECTRAL request.

        Parameters
        ----------

        request: skyportal.models.FollowupRequest
            The request to add to the queue and the SkyPortal database.

        """

        self.requestgroup = self._build_payload(request)

    def _build_payload(self, request):
        """Payload json for LCO 2m SPECTRAL queue requests.

        Parameters
        ----------

        request: skyportal.models.FollowupRequest
            The request to add to the queue and the SkyPortal database.

        Returns
        ----------
        payload: json
            payload for requests.
        """

        if request.obj.dec > 17:
            raise ValueError('Spectral only available in South.')

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
                    'instrument_type': '2M0-SCICAM-SPECTRAL',
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
        location = {'telescope_class': '2m0'}

        altdata = request.allocation.altdata

        # The full RequestGroup, with additional meta-data
        requestgroup = {
            'name': '%s' % (request.obj.id),  # The title
            'proposal': altdata["PROPOSAL_ID"],
            'ipp_value': request.payload["priority"],
            'operator': 'SINGLE',
            'observation_type': 'NORMAL',
            'requests': [
                {
                    'configurations': configurations,
                    'windows': windows,
                    'location': location,
                }
            ],
        }

        return requestgroup


class MUSCATRequest:

    """An XML structure for LCO 2m MUSCAT requests."""

    def __init__(self, request):
        """Initialize MUSCAT request.

        Parameters
        ----------

        request: skyportal.models.FollowupRequest
            The request to add to the queue and the SkyPortal database.

        """

        self.requestgroup = self._build_payload(request)

    def _build_payload(self, request):
        """Payload json for LCO 2m MUSCAT queue requests.

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

        configurations = [
            {
                'type': 'EXPOSE',
                'instrument_type': '2M0-SCICAM-MUSCAT',
                'target': target,
                'constraints': constraints,
                'acquisition_config': {},
                'guiding_config': {},
                'instrument_configs': [
                    {
                        'exposure_time': exp_time,
                        'exposure_count': exp_count,
                        'optical_elements': {
                            'diffuser_g_position': 'out',
                            'diffuser_r_position': 'out',
                            'diffuser_i_position': 'out',
                            'diffuser_z_position': 'out',
                        },
                        'extra_params': {
                            'exposure_mode': 'SYNCHRONOUS',
                            'exposure_time_g': exp_time,
                            'exposure_time_r': exp_time,
                            'exposure_time_i': exp_time,
                            'exposure_time_z': exp_time,
                        },
                    }
                ],
            }
        ]

        tstart = request.payload["start_date"] + ' 00:00:00'
        tend = request.payload["end_date"] + ' 00:00:00'

        windows = [{'start': tstart, 'end': tend}]

        # The telescope class that should be used for this observation
        location = {'telescope_class': '2m0'}

        altdata = request.allocation.altdata

        # The full RequestGroup, with additional meta-data
        requestgroup = {
            'name': '%s' % (request.obj.id),  # The title
            'proposal': altdata["PROPOSAL_ID"],
            'ipp_value': request.payload["priority"],
            'operator': 'SINGLE',
            'observation_type': 'NORMAL',
            'requests': [
                {
                    'configurations': configurations,
                    'windows': windows,
                    'location': location,
                }
            ],
        }

        return requestgroup


class FLOYDSRequest:

    """An XML structure for LCO 2m FLOYDS requests."""

    def __init__(self, request):
        """Initialize FLOYDS request.

        Parameters
        ----------

        request: skyportal.models.FollowupRequest
            The request to add to the queue and the SkyPortal database.

        """

        self.requestgroup = self._build_payload(request)

    def _build_payload(self, request):
        """Payload header for LCO 2m FLOYDS queue requests.

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
        location = {'telescope_class': '2m0'}

        exp_time = request.payload["exposure_time"]
        exp_count = int(request.payload["exposure_counts"])

        configurations = [
            {
                'type': 'LAMP_FLAT',
                'instrument_type': '2M0-FLOYDS-SCICAM',
                'constraints': constraints,
                'target': target,
                'acquisition_config': {},
                'guiding_config': {'mode': 'OFF', 'optional': False},
                'instrument_configs': [
                    {
                        'exposure_time': 50,
                        'exposure_count': 1,
                        'rotator_mode': 'VFLOAT',
                        'optical_elements': {'slit': 'slit_1.6as'},
                    }
                ],
            },
            {
                'type': 'ARC',
                'instrument_type': '2M0-FLOYDS-SCICAM',
                'constraints': constraints,
                'target': target,
                'acquisition_config': {},
                'guiding_config': {'mode': 'OFF', 'optional': False},
                'instrument_configs': [
                    {
                        'exposure_time': 60,
                        'exposure_count': 1,
                        'rotator_mode': 'VFLOAT',
                        'optical_elements': {'slit': 'slit_1.6as'},
                    }
                ],
            },
            {
                'type': 'SPECTRUM',
                'instrument_type': '2M0-FLOYDS-SCICAM',
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
            {
                'type': 'ARC',
                'instrument_type': '2M0-FLOYDS-SCICAM',
                'constraints': constraints,
                'target': target,
                'acquisition_config': {},
                'guiding_config': {'mode': 'OFF', 'optional': False},
                'instrument_configs': [
                    {
                        'exposure_time': 60,
                        'exposure_count': 1,
                        'rotator_mode': 'VFLOAT',
                        'optical_elements': {'slit': 'slit_1.6as'},
                    }
                ],
            },
            {
                'type': 'LAMP_FLAT',
                'instrument_type': '2M0-FLOYDS-SCICAM',
                'constraints': constraints,
                'target': target,
                'acquisition_config': {},
                'guiding_config': {'mode': 'OFF', 'optional': False},
                'instrument_configs': [
                    {
                        'exposure_time': 50,
                        'exposure_count': 1,
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
            'observation_type': 'NORMAL',
            'requests': [
                {
                    'configurations': configurations,
                    'windows': windows,
                    'location': location,
                }
            ],
        }

        return requestgroup


class LCOAPI(FollowUpAPI):

    """An interface to LCO operations."""

    @staticmethod
    def delete(request):

        """Delete a follow-up request from LCO queue (all instruments).

        Parameters
        ----------
        request: skyportal.models.FollowupRequest
            The request to delete from the queue and the SkyPortal database.
        """

        from ..models import DBSession, FollowupRequest, FacilityTransaction

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

        DBSession().add(transaction)

    @staticmethod
    def update(request):

        """Update a follow-up request from LCO queue (all instruments).

        Parameters
        ----------
        request: skyportal.models.FollowupRequest
            The request to update from the queue and the SkyPortal database.
        """

        from ..models import DBSession, FollowupRequest, FacilityTransaction

        req = (
            DBSession()
            .query(FollowupRequest)
            .filter(FollowupRequest.id == request.id)
            .one()
        )

        # this happens for failed submissions
        # just go ahead and delete
        if len(req.transactions) == 0:
            DBSession().query(FollowupRequest).filter(
                FollowupRequest.id == request.id
            ).delete()
            DBSession().commit()
            return

        altdata = request.allocation.altdata
        if not altdata:
            raise ValueError('Missing allocation information.')

        content = req.transactions[0].response["content"]
        content = json.loads(content)
        uid = content["id"]

        r = requests.get(
            f"{requestpath}{uid}/",
            headers={"Authorization": f'Token {altdata["API_TOKEN"]}'},
        )

        r.raise_for_status()

        content = req.transactions[0].response["content"]
        content = json.loads(content)

        if content["state"] == "COMPLETED":
            request.status = "complete"

        transaction = FacilityTransaction(
            request=http.serialize_requests_request(r.request),
            response=http.serialize_requests_response(r),
            followup_request=request,
            initiator_id=request.last_modified_by_id,
        )

        DBSession().add(transaction)


class SINISTROAPI(LCOAPI):

    """An interface to LCO SINISTRO operations."""

    # subclasses *must* implement the method below
    @staticmethod
    def submit(request):

        """Submit a follow-up request to LCO's SINISTRO.

        Parameters
        ----------
        request: skyportal.models.FollowupRequest
            The request to add to the queue and the SkyPortal database.
        """

        from ..models import FacilityTransaction, DBSession

        altdata = request.allocation.altdata
        if not altdata:
            raise ValueError('Missing allocation information.')

        lcoreq = SINISTRORequest(request)
        requestgroup = lcoreq.requestgroup

        r = requests.post(
            requestpath,
            headers={"Authorization": f'Token {altdata["API_TOKEN"]}'},
            json=requestgroup,  # Make sure you use json!
        )
        r.raise_for_status()

        if r.status_code == 201:
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
                "items": {"type": "string", "enum": ["gp", "rp", "ip", "zs", "Y"]},
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
                "title": "Maximum Seeing [arcsec] (0-180)",
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


class SPECTRALAPI(LCOAPI):

    """An interface to LCO SPECTRAL operations."""

    # subclasses *must* implement the method below
    @staticmethod
    def submit(request):

        """Submit a follow-up request to LCO's SPECTRAL.

        Parameters
        ----------
        request: skyportal.models.FollowupRequest
            The request to add to the queue and the SkyPortal database.
        """

        from ..models import FacilityTransaction, DBSession

        altdata = request.allocation.altdata

        if not altdata:
            raise ValueError('Missing allocation information.')

        lcoreq = SPECTRALRequest(request)
        requestgroup = lcoreq.requestgroup

        r = requests.post(
            requestpath,
            headers={"Authorization": f'Token {altdata["API_TOKEN"]}'},
            json=requestgroup,  # Make sure you use json!
        )

        r.raise_for_status()

        if r.status_code == 201:
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
                "items": {"type": "string", "enum": ["gp", "rp", "ip", "zs", "Y"]},
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
                "title": "Maximum Seeing [arcsec] (0-180)",
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


class MUSCATAPI(LCOAPI):

    """An interface to LCO MUSCAT operations."""

    # subclasses *must* implement the method below
    @staticmethod
    def submit(request):

        """Submit a follow-up request to LCO's MUSCAT.

        Parameters
        ----------
        request: skyportal.models.FollowupRequest
            The request to add to the queue and the SkyPortal database.
        """

        from ..models import FacilityTransaction, DBSession

        altdata = request.allocation.altdata
        if not altdata:
            raise ValueError('Missing allocation information.')

        lcoreq = MUSCATRequest(request)
        requestgroup = lcoreq.requestgroup

        r = requests.post(
            requestpath,
            headers={"Authorization": f'Token {altdata["API_TOKEN"]}'},
            json=requestgroup,  # Make sure you use json!
        )
        r.raise_for_status()

        if r.status_code == 201:
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
                "title": "Maximum Seeing [arcsec] (0-180)",
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


class FLOYDSAPI(LCOAPI):

    """An interface to LCO FLOYDS operations."""

    # subclasses *must* implement the method below
    @staticmethod
    def submit(request):

        """Submit a follow-up request to LCO's FLOYDS.

        Parameters
        ----------
        request: skyportal.models.FollowupRequest
            The request to add to the queue and the SkyPortal database.
        """

        from ..models import FacilityTransaction, DBSession

        altdata = request.allocation.altdata
        if not altdata:
            raise ValueError('Missing allocation information.')

        lcoreq = FLOYDSRequest(request)
        requestgroup = lcoreq.requestgroup

        r = requests.post(
            requestpath,
            headers={"Authorization": f'Token {altdata["API_TOKEN"]}'},
            json=requestgroup,  # Make sure you use json!
        )

        r.raise_for_status()

        if r.status_code == 201:
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
                "title": "Maximum Seeing [arcsec] (0-180)",
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
