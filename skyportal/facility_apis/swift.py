from astropy.time import Time
import base64
from datetime import datetime
import json
import requests
import tempfile

from . import FollowUpAPI
from baselayer.app.env import load_env

from ..utils import http

env, cfg = load_env()


# Submission URL
API_URL = f"{cfg['app.swift.protocol']}://{cfg['app.swift.host']}:{cfg['app.swift.port']}/toop/submit_json.php"
XRT_URL = f"{cfg['app.swift_xrt_endpoint']}/run_userobject.php"


class UVOTXRTRequest:

    """A JSON structure for Swift UVOT/XRT requests."""

    def __init__(self, request):
        """Initialize UVOT/XRT request.

        Parameters
        ----------
        request : skyportal.models.FollowupRequest
            The request to add to the queue and the SkyPortal database.

        """

        self.requestgroup = self._build_payload(request)

    def _build_payload(self, request):
        """Payload json for Swift UVOT/XRT TOO requests.

        Parameters
        ----------
        request : skyportal.models.FollowupRequest
            The request to add to the queue and the SkyPortal database.

        Returns
        -------
        payload : swifttools.swift_too.Swift_TOO
            payload for requests.
        """

        altdata = request.allocation.altdata

        from swifttools.swift_too import Swift_TOO

        too = Swift_TOO()
        too.username = altdata["username"]
        too.shared_secret = altdata["secret"]

        too.source_name = request.obj.id
        too.ra, too.dec = request.obj.ra, request.obj.dec

        too.source_type = request.payload["source_type"]

        too.exp_time_per_visit = request.payload["exposure_time"]
        too.monitoring_freq = "%d days" % request.payload["monitoring_freq"]
        too.num_of_visits = int(request.payload["exposure_counts"])

        too.xrt_countrate = request.payload["xrt_countrate"]
        too.exp_time_just = request.payload["exp_time_just"]
        too.immediate_objective = request.payload["immediate_objective"]

        if request.payload["urgency"] not in ["1", "2", "3", "4"]:
            raise ValueError('urgency not in ["1", "2", "3", "4"].')
        too.urgency = int(request.payload["urgency"])

        if request.payload["obs_type"] not in [
            "Spectroscopy",
            "Light Curve",
            "Position",
            "Timing",
        ]:
            raise ValueError('obs_type not an allowed value.')
        too.obs_type = request.payload["obs_type"]

        too.uvot_mode = request.payload["uvot_mode"]
        too.science_just = request.payload["science_just"]

        return too


class XRTAPIRequest:

    """A JSON structure for Swift XRT API requests."""

    def __init__(self, request):
        """Initialize XRT API request.

        Parameters
        ----------
        request : skyportal.models.FollowupRequest
            The request to add to the queue and the SkyPortal database.

        """

        self.requestgroup = self._build_payload(request)

    def _build_payload(self, request):
        """Payload json for Swift UVOT/XRT TOO requests.

        Parameters
        ----------
        request : skyportal.models.FollowupRequest
            The request to add to the queue and the SkyPortal database.

        Returns
        -------
        payload : swifttools.swift_too.Swift_TOO
            payload for requests.
        """

        from swifttools.xrt_prods import XRTProductRequest

        altdata = request.allocation.altdata

        T0 = Time(request.payload["T0"], format='iso')
        MET = Time('2001-01-01 00:00:00', format='iso')
        Tdiff = (T0 - MET).jd * 86400

        if "detornot" in request.payload and request.payload["detornot"]:
            centroid = True
        else:
            centroid = False

        myReq = XRTProductRequest(altdata["XRT_UserID"])
        myReq.setGlobalPars(
            getTargs=True,
            centroid=centroid,
            name=request.obj.id,
            RA=request.obj.ra,
            Dec=request.obj.dec,
            centMeth=request.payload["centMeth"],
            detMeth=request.payload["detMeth"],
            useSXPS=False,
            T0=Tdiff,
            posErr=request.payload["poserr"],
        )
        myReq.addLightCurve(binMeth='counts', pcCounts=20, wtCounts=30, dynamic=True)
        myReq.addSpectrum(hasRedshift=False)
        myReq.addStandardPos()
        myReq.addEnhancedPos()
        myReq.addAstromPos(useAllObs=True)

        return myReq


class UVOTXRTAPI(FollowUpAPI):

    """An interface to Swift operations."""

    @staticmethod
    def get(request, session):

        """Get an analysis request result from Swift.

        Parameters
        ----------
        request : skyportal.models.FollowupRequest
            The request to retrieve Swift XRT data.
        session : baselayer.DBSession
            Database session to use for photometry
        """

        from ..models import (
            FollowupRequest,
            Comment,
            Group,
        )

        req = (
            session.query(FollowupRequest)
            .filter(FollowupRequest.id == request.id)
            .one()
        )

        altdata = request.allocation.altdata

        if not altdata:
            raise ValueError('Missing allocation information.')

        content = req.transactions[-1].response["content"]
        content = json.loads(content)
        swiftreq = XRTAPIRequest(request)

        swiftreq.requestgroup._status = 1
        swiftreq.requestgroup._submitted = int(content["OK"])
        swiftreq.requestgroup._jobID = content["JobID"]
        swiftreq.requestgroup._retData["URL"] = content["URL"]
        swiftreq.requestgroup._retData["jobPars"] = content["jobPars"]

        if not swiftreq.requestgroup.complete:
            raise ValueError('Result not yet available. Please try again later.')
        else:
            group_ids = [g.id for g in request.requester.accessible_groups]
            groups = session.scalars(
                Group.select(request.requester).where(Group.id.in_(group_ids))
            ).all()
            with tempfile.TemporaryDirectory() as tmpdirname:
                retDict = swiftreq.requestgroup.downloadProducts(tmpdirname)
                for key in retDict:
                    filename = retDict[key]
                    attachment_name = filename.split("/")[-1]
                    with open(filename, 'rb') as f:
                        attachment_bytes = base64.b64encode(f.read())
                    comment = Comment(
                        text=f'Swift XRT: {key}',
                        obj_id=request.obj.id,
                        attachment_bytes=attachment_bytes,
                        attachment_name=attachment_name,
                        author=request.requester,
                        groups=groups,
                        bot=False,
                    )
                    session.add(comment)
                req.status = 'Result posted as comment'
                session.commit()

    # subclasses *must* implement the method below
    @staticmethod
    def submit(request, session):

        """Submit a follow-up request to Swift's UVOT/XRT

        Parameters
        ----------
        request : skyportal.models.FollowupRequest
            The request to add to the queue and the SkyPortal database.
        session: sqlalchemy.Session
            Database session for this transaction
        """

        from ..models import FacilityTransaction

        altdata = request.allocation.altdata
        if not altdata:
            raise ValueError('Missing allocation information.')

        if request.payload["request_type"] == "XRT/UVOT ToO":
            swiftreq = UVOTXRTRequest(request)
            swiftreq.requestgroup.validate()

            r = requests.post(
                url=API_URL, verify=True, data={'jwt': swiftreq.requestgroup.jwt}
            )
            r.raise_for_status()

            if r.status_code == 201:
                request.status = 'submitted'
            else:
                request.status = f'rejected: {r.content}'
        elif request.payload["request_type"] == "XRT API":
            swiftreq = XRTAPIRequest(request)
            r = requests.post(url=XRT_URL, json=swiftreq.requestgroup.getJSONDict())
            returnedData = json.loads(r.text)
            if r.status_code != 200:
                request.status = f'rejected: {r.reason}'
            else:
                if returnedData["OK"] == 0:
                    request.status = (
                        f'rejected: {returnedData["ERROR"], returnedData["listErr"]}'
                    )
                else:
                    request.status = 'submitted'

        transaction = FacilityTransaction(
            request=http.serialize_requests_request(r.request),
            response=http.serialize_requests_response(r),
            followup_request=request,
            initiator_id=request.last_modified_by_id,
        )

        session.add(transaction)

    form_json_schema = {
        "type": "object",
        "properties": {
            "request_type": {
                "type": "string",
                "enum": ["XRT/UVOT ToO", "XRT API"],
                "default": "XRT/UVOT ToO",
                "title": "Request Type",
            },
        },
        "dependencies": {
            "request_type": {
                "oneOf": [
                    {
                        "properties": {
                            "request_type": {
                                "enum": ["XRT API"],
                            },
                            "detornot": {
                                "title": "Do you want to centroid?",
                                "type": "boolean",
                            },
                            "centMeth": {
                                "type": "string",
                                "enum": ["simple", "iterative"],
                                "default": "simple",
                                "title": "Centroid Method",
                            },
                            "detMeth": {
                                "type": "string",
                                "enum": ["simple", "iterative"],
                                "default": "simple",
                                "title": "Detection Method",
                            },
                            "T0": {
                                "type": "string",
                                "title": "Date (UT)",
                                "default": str(datetime.utcnow()).replace("T", ""),
                            },
                            "poserr": {
                                "title": "Position Error [arcmin]",
                                "type": "number",
                                "default": 1,
                            },
                            "binMeth": {
                                "type": "string",
                                "enum": ["counts", "time", "snapshot", "obsid"],
                                "default": "counts",
                                "title": "Binning method",
                            },
                        }
                    },
                    {
                        "properties": {
                            "request_type": {
                                "enum": ["XRT/UVOT ToO"],
                            },
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
                                "enum": [
                                    "Spectroscopy",
                                    "Light Curve",
                                    "Position",
                                    "Timing",
                                ],
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
                                "default": "We wish to measure the X-ray emission of an optically discovered potential orphan afterglow/kilonova.",
                            },
                            "uvot_mode": {
                                "title": "UVOT Mode",
                                "type": "string",
                                "default": "default",
                            },
                            "science_just": {
                                "title": "Science Justification",
                                "type": "string",
                                "default": "An X-ray detection of this transient will further associate this object to a relativistic explosion and will help unveil the nature of the progenitor type.",
                            },
                        },
                    },
                ],
            },
        },
    }

    ui_json_schema = {"observation_choices": {"ui:widget": "checkboxes"}}
