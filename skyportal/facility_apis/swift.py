from swifttools.swift_too import Swift_TOO

from . import FollowUpAPI
from baselayer.app.env import load_env

from ..utils import http

env, cfg = load_env()


class UVOTRequest:

    """A JSON structure for Swift UVOT requests."""

    def __init__(self, request):
        """Initialize UVOT request.

        Parameters
        ----------

        request: skyportal.models.FollowupRequest
            The request to add to the queue and the SkyPortal database.

        """

        self.requestgroup = self._build_payload(request)

    def _build_payload(self, request):
        """Payload json for Swift UVOT TOO requests.

        Parameters
        ----------

        request: skyportal.models.FollowupRequest
            The request to add to the queue and the SkyPortal database.

        Returns
        ----------
        payload: json
            payload for requests.
        """

        altdata = request.allocation.altdata

        too = Swift_TOO()
        too.username = altdata["username"]
        too.shared_secret = altdata["secret"]
        # too.debug = True

        too.source_name = request.obj.id
        too.ra, too.dec = request.obj.ra, request.obj.dec

        too.source_type = request.payload["source_type"]

        too.exp_time_per_visit = request.payload["exposure_time"]
        too.monitoring_freq = "%d days" % request.payload["monitoring_freq"]
        too.num_of_visits = int(request.payload["exposure_counts"])

        too.xrt_countrate = request.payload["xrt_countrate"]
        too.exp_time_just = request.payload["exp_time_just"]
        too.immediate_objective = request.payload["immediate_objective"]

        too.urgency = int(request.payload["urgency"])
        too.obs_type = request.payload["obs_type"]

        too.uvot_mode = request.payload["uvot_mode"]
        too.science_just = request.payload["science_just"]

        return too


class UVOTAPI(FollowUpAPI):

    """An interface to Swift operations."""

    # subclasses *must* implement the method below
    @staticmethod
    def submit(request):

        """Submit a follow-up request to Swift's UVOT

        Parameters
        ----------
        request: skyportal.models.FollowupRequest
            The request to add to the queue and the SkyPortal database.
        """

        from ..models import FacilityTransaction, DBSession

        altdata = request.allocation.altdata
        if not altdata:
            raise ValueError('Missing allocation information.')

        swiftreq = UVOTRequest(request)

        swiftreq.requestgroup.validate()
        r = swiftreq.requestgroup.submit_post()

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
                "default": 4000.0,
            },
            "exposure_counts": {
                "title": "Exposure Counts",
                "type": "number",
                "default": 1,
            },
            "monitoring_freq": {
                "title": "Monitoring Frequency [day]",
                "type": "number",
                "default": 1,
            },
            "xrt_countrate": {
                "title": "XRT Count rate [counts/s]",
                "type": "number",
                "default": 0.0025,
            },
            "urgency": {
                "type": "string",
                "enum": ["1", "2", "3", "4"],
                "default": "3",
                "title": "Urgency",
            },
            "obs_type": {
                "type": "string",
                "enum": ["Spectroscopy", "Light Curve", "Position", "Timing"],
                "default": "Light Curve",
                "title": "Observation Type",
            },
            "source_type": {
                "title": "Source Type",
                "type": "string",
                "default": "Optical fast transient",
            },
            "exp_time_just": {
                "title": "Exposure Time Justification",
                "type": "string",
                "default": "At ~2.5e-3 counts/sec, 4ks should suffice to achieve a high SNR, assuming a background of ~1e-4 counts/sec (Pagani et al. 2007)",
            },
            "immediate_objective": {
                "title": "Immediate Objective",
                "type": "string",
            },
            "uvot_mode": {
                "title": "UVOT Mode",
                "type": "string",
                "default": "default",
            },
            "science_just": {
                "title": "Science Justification",
                "type": "string",
            },
        },
        "required": [
            "exposure_time",
            "exposure_counts",
            "monitoring_freq",
            "urgency",
            "obs_type",
            "source_type",
            "exp_time_just",
            "immediate_objective",
            "uvot_mode",
            "science_just",
            "xrt_countrate",
        ],
    }

    ui_json_schema = {"observation_choices": {"ui:widget": "checkboxes"}}
