import re
import urllib
from datetime import datetime, timedelta

import requests
from astropy.time import Time

from baselayer.app.env import load_env
from baselayer.app.flow import Flow
from baselayer.log import make_log

from ..utils import http
from . import FollowUpAPI

env, cfg = load_env()


# Submission URL
LOGIN_URL = f"{cfg['app.heasarc_endpoint']}/ark/LOGIN"
NICER_URL = f"{cfg['app.heasarc_endpoint']}/ark/nicertoo/form.html"

log = make_log("facility_apis/nicer")

CLEANR = re.compile("<.*?>|&([a-z0-9]+|#[0-9]{1,6}|#x[0-9a-f]{1,6});")


class NICERRequest:
    """A JSON structure for NICER requests."""

    def __init__(self, request):
        """Initialize NICER request.

        Parameters
        ----------
        request : skyportal.models.FollowupRequest
            The request to add to the queue and the SkyPortal database.

        """

        self.requestgroup = self._build_payload(request)

    def _build_payload(self, request):
        """Payload json for NICER TOO requests.

        Parameters
        ----------
        request : skyportal.models.FollowupRequest
            The request to add to the queue and the SkyPortal database.

        Returns
        -------
        payload : dict
            payload for requests.
        """

        data = {
            "RPS_DHTML": "",
            "RPS_BEGIN": "",
            "COVER": "",
            "RPS_CLOSED_3": "",
            "RPS_END": "",
            "Urgency": request.payload["Urgency"],
            "NICER Proposal Number": request.payload.get("ProposalNumber", None),
            "Justification for Target of Opportunity": request.payload[
                "JustificationToO"
            ],
            "Target Name": request.obj.id,
            "Target Category": request.payload["TargetCategory"],
            "Right Ascension": request.obj.ra,
            "Declination": request.obj.dec,
            "Total Observation Time": request.payload["ObservationTime"],
            "Justification for Exposure": request.payload["JustificationExposure"],
            "Monitoring Program": request.payload["MonitoringProgram"],
            "Monitoring Criteria": request.payload.get("MonitoringCriteria", None),
            "Phase Dependent Observation": request.payload["PhaseDependentObservation"],
            "Phase Dependent Epoch": request.payload.get("PhaseDependentEpoch", None),
            "Phase Dependent Period": request.payload.get("PhaseDependentPeriod", None),
            "Minimum Phase": request.payload.get("PhaseMinimum", None),
            "Maximum Phase": request.payload.get("PhaseMaximum", None),
            "Phase Dependent Remarks": request.payload.get(
                "PhaseDependentRemarks", None
            ),
            "Specific Time Range Observation": request.payload[
                "SpecificTimeRangeObservation"
            ],
            "Specific Time Range Start": request.payload.get("TimeRangeStart", None),
            "Specific Time Range End": request.payload.get("TimeRangeEnd", None),
            "Specific Time Range Remarks": request.payload.get(
                "TimeRangeRemarks", None
            ),
            "Coordinated Observation": request.payload["CoordinatedObservation"],
            "Coordinating Observatory": request.payload.get(
                "CoordinatingObservatory", None
            ),
            "Coordinated Observation Description": request.payload.get(
                "CoordinatedObservationDescription", None
            ),
            "Uninterrupted Observation": request.payload["UninterruptedObservation"],
            "Uninterrupted Observation Justification": request.payload.get(
                "UninterruptedObservationJustification", None
            ),
            "Expected 0.3-10keV Count Rate": request.payload["ExpectedCountRate"],
        }

        if data["Phase Dependent Epoch"] is not None:
            data["Phase Dependent Epoch"] = Time(
                data["Phase Dependent Epoch"], format="isot"
            ).mjd
        if data["Specific Time Range Start"] is not None:
            data["Specific Time Range Start"] = Time(
                data["Specific Time Range Start"], format="isot"
            ).mjd
        if data["Specific Time Range End"] is not None:
            data["Specific Time Range End"] = Time(
                data["Specific Time Range End"], format="isot"
            ).mjd

        return data


class NICERAPI(FollowUpAPI):
    """An interface to NICER operations."""

    @staticmethod
    def submit(request, session, **kwargs):
        """Submit a follow-up request to NICER

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
            raise ValueError("Missing allocation information.")

        nicerreq = NICERRequest(request)
        data = nicerreq.requestgroup

        params = {
            "destination": urllib.parse.quote("/ark/user/", safe=""),
            "credential_0": request.allocation.altdata["username"],
            "credential_1": request.allocation.altdata["password"],
        }

        r_cred = requests.post(LOGIN_URL, params=params)
        for hist in r_cred.history:
            if len(hist.cookies) > 0:
                cookies = hist.cookies
                break

        cookie_string = "; ".join([str(x) + "=" + str(y) for x, y in cookies.items()])
        headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "en-US,en;q=0.9",
            "Cookie": cookie_string,
        }

        data_verify = {**data, "RPS_VERIFY.x": 49, "RPS_VERIFY.y": 15}
        r = requests.post(url=NICER_URL, data=data_verify, headers=headers)
        if "Attempted verification detected" in r.text:
            error_message = re.sub(
                CLEANR,
                "",
                r.text.split("Attempted verification detected")[1].split("</span>")[0],
            ).replace("\n", " ")
            request.status = f"rejected: {error_message}"
        elif "Form verified successfully" in r.text:
            data_submit = {
                **data,
                "RPS_VERIFIED": "",
                "RPS_SUBMIT.x": 45,
                "RPS_SUBMIT.y": 4,
                "RPS_OPENED_3": "",
            }
            r = requests.post(url=NICER_URL, data=data_submit, headers=headers)
            request.status = "submitted"

        transaction = FacilityTransaction(
            request=http.serialize_requests_request(r.request),
            response=http.serialize_requests_response(r),
            followup_request=request,
            initiator_id=request.last_modified_by_id,
        )

        session.add(transaction)

        if kwargs.get("refresh_source", False):
            flow = Flow()
            flow.push(
                "*",
                "skyportal/REFRESH_SOURCE",
                payload={"obj_key": request.obj.internal_key},
            )
        if kwargs.get("refresh_requests", False):
            flow = Flow()
            flow.push(
                request.last_modified_by_id,
                "skyportal/REFRESH_FOLLOWUP_REQUESTS",
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
                "Can't delete requests already sent successfully to NICER."
            )

        if kwargs.get("refresh_source", False):
            flow = Flow()
            flow.push(
                "*",
                "skyportal/REFRESH_SOURCE",
                payload={"obj_key": obj_internal_key},
            )
        if kwargs.get("refresh_requests", False):
            flow = Flow()
            flow.push(
                last_modified_by_id,
                "skyportal/REFRESH_FOLLOWUP_REQUESTS",
            )

    form_json_schema = {
        "type": "object",
        "properties": {
            "Urgency": {
                "type": "string",
                "enum": [
                    "Next Day",
                    "Next Business Day",
                    "Within a Week",
                    "One Month or Longer",
                ],
                "default": "Next Day",
                "title": "Urgency",
            },
            "ProposalNumber": {
                "title": "Proposal Number",
                "type": "string",
            },
            "JustificationToO": {
                "title": "Justification for Target of Opportunity",
                "type": "string",
            },
            "TargetCategory": {
                "type": "string",
                "enum": [
                    "Magnetars and Rotation-Powered Pulsars",
                    "X-Ray Binaries",
                    "White Dwarfs and Cataclysmic Variables",
                    "Non-Compact Stellar Objects",
                    "Supernova Remnants/Other Extended Galactic Sources",
                    "Normal Galaxies",
                    "Active Galaxies and Quasars",
                    "Galaxy Clusters and Extragalactic Extended Objects",
                    "Gravitational-Wave Sources",
                    "Solar System Objects",
                    "Other",
                ],
                "default": "Gravitational-Wave Sources",
                "title": "Target Category",
            },
            "ObservationTime": {
                "title": "Observation Time [kiloseconds]",
                "type": "number",
                "default": 10,
            },
            "JustificationExposure": {
                "title": "Justification for Exposure Time",
                "type": "string",
            },
            "ExpectedCountRate": {
                "title": "Expected 0.3-10keV Count Rate",
                "type": "number",
            },
            "MonitoringProgram": {
                "type": "string",
                "enum": [
                    "Y",
                    "N",
                ],
                "default": "N",
                "title": "Monitoring Program?",
            },
            "PhaseDependentObservation": {
                "type": "string",
                "enum": [
                    "Y",
                    "N",
                ],
                "default": "N",
                "title": "Phase Dependent Observation?",
            },
            "SpecificTimeRangeObservation": {
                "type": "string",
                "enum": [
                    "N",
                    "Y",
                ],
                "default": "N",
                "title": "Specific Time Range?",
            },
            "CoordinatedObservation": {
                "type": "string",
                "enum": [
                    "N",
                    "Y",
                ],
                "default": "N",
                "title": "Coordinated Observations?",
            },
            "UninterruptedObservation": {
                "type": "string",
                "enum": [
                    "N",
                    "Y",
                ],
                "default": "N",
                "title": "Uninterrupted Observations?",
            },
        },
        "required": [
            "Urgency",
            "JustificationToO",
            "TargetCategory",
            "ObservationTime",
            "JustificationExposure",
            "ExpectedCountRate",
            "MonitoringProgram",
            "PhaseDependentObservation",
            "SpecificTimeRangeObservation",
            "CoordinatedObservation",
            "UninterruptedObservation",
        ],
        "dependencies": {
            "CoordinatedObservation": {
                "oneOf": [
                    {
                        "properties": {
                            "CoordinatedObservation": {
                                "enum": ["Y"],
                            },
                            "CoordinatingObservatory": {
                                "title": "Coordinating Observatory",
                                "type": "string",
                            },
                            "CoordinatedObservationDescription": {
                                "title": "Coordinated Observation Description",
                                "type": "string",
                            },
                        },
                    },
                    {
                        "properties": {
                            "CoordinatedObservation": {
                                "enum": ["N"],
                            },
                        }
                    },
                ],
            },
            "UninterruptedObservation": {
                "oneOf": [
                    {
                        "properties": {
                            "UninterruptedObservation": {
                                "enum": ["Y"],
                            },
                            "UninterruptedObservationJustification": {
                                "title": "Uninterrupted Observation Justification",
                                "type": "string",
                            },
                        }
                    },
                    {
                        "properties": {
                            "UninterruptedObservation": {
                                "enum": ["N"],
                            },
                        }
                    },
                ]
            },
            "SpecificTimeRangeObservation": {
                "oneOf": [
                    {
                        "properties": {
                            "SpecificTimeRangeObservation": {
                                "enum": ["Y"],
                            },
                            "TimeRangeStart": {
                                "type": "string",
                                "default": str(datetime.utcnow()),
                                "title": "Time Range Start (UT)",
                            },
                            "TimeRangeEnd": {
                                "type": "string",
                                "title": "Time Range End (UT)",
                                "default": str(datetime.utcnow() + timedelta(days=7)),
                            },
                        }
                    },
                    {
                        "properties": {
                            "SpecificTimeRangeObservation": {
                                "enum": ["N"],
                            },
                        }
                    },
                ]
            },
            "PhaseDependentObservation": {
                "oneOf": [
                    {
                        "properties": {
                            "PhaseDependentObservation": {
                                "enum": ["Y"],
                            },
                            "PhaseDependentEpoch": {
                                "type": "string",
                                "default": str(datetime.utcnow()),
                                "title": "Phase Dependent Epoch (UT)",
                            },
                            "PhaseDependentPeriod": {
                                "title": "Period [days]",
                                "type": "number",
                            },
                            "PhaseMinimum": {
                                "title": "Phase Minimum [days]",
                                "type": "number",
                            },
                            "PhaseMaximum": {
                                "title": "Phase Maximum [days]",
                                "type": "number",
                            },
                            "PhaseDependentRemarks": {
                                "title": "Phase Dependent Remarks",
                                "type": "string",
                            },
                        },
                    },
                    {
                        "properties": {
                            "PhaseDependentObservation": {
                                "enum": ["N"],
                            },
                        }
                    },
                ],
            },
            "MonitoringProgram": {
                "oneOf": [
                    {
                        "properties": {
                            "MonitoringProgram": {
                                "enum": ["Y"],
                            },
                            "MonitoringCriteria": {
                                "title": "Criteria for the Monitoring",
                                "type": "string",
                            },
                        },
                    },
                    {
                        "properties": {
                            "MonitoringProgram": {
                                "enum": ["N"],
                            },
                        }
                    },
                ],
            },
        },
    }

    form_json_schema_altdata = {
        "type": "object",
        "properties": {
            "username": {
                "type": "string",
                "title": "Username",
            },
            "password": {
                "type": "string",
                "title": "Password",
            },
        },
    }

    ui_json_schema = {}
