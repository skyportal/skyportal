import json
from datetime import timedelta

import aiohttp
import sqlalchemy as sa
from sqlalchemy.orm import selectinload

from baselayer.app.env import load_env
from baselayer.app.flow import Flow
from baselayer.log import make_log

from ..utils import http
from ..utils.naive_datetime import utcnow_naive
from . import FollowUpAPI

env, cfg = load_env()

requestpath = f"{cfg['app.lco_protocol']}://{cfg['app.lco_host']}:{cfg['app.lco_port']}/api/requestgroups/"

log = make_log("facility_apis/soar")


class SOAR_GHTS_IMAGER_Request:
    """A JSON structure for SOAR GHTS IMAGER requests."""

    def __init__(self, request):
        """Initialize SOAR GHTS REDCAM request.

        Parameters
        ----------

        request: skyportal.models.FollowupRequest
            The request to add to the queue and the SkyPortal database.

        """

        self.requestgroup = self._build_payload(request)

    def _build_payload(self, request):
        """Payload json for SOAR GHTS IMAGER queue requests.

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
            "max_airmass": request.payload["maximum_airmass"],
            "min_lunar_distance": request.payload["minimum_lunar_distance"],
        }

        # The target of the observation
        target = {
            "name": request.obj.id,
            "type": "ICRS",
            "ra": request.obj.ra,
            "dec": request.obj.dec,
            "proper_motion_ra": 0,
            "proper_motion_dec": 0,
            "parallax": 0,
            "epoch": 2000,
        }

        exp_time = request.payload["exposure_time"]
        exp_count = int(request.payload["exposure_counts"])

        if request.payload["instrument_type"] == "SOAR_GHTS_BLUECAM_IMAGER":
            instrument_mode = "GHTS_B_Image_2x2"
        elif request.payload["instrument_type"] == "SOAR_GHTS_REDCAM_IMAGER":
            instrument_mode = "GHTS_R_Image_2x2"

        configurations = []
        for filt in request.payload["observation_choices"]:
            configurations.append(
                {
                    "type": "EXPOSE",
                    "instrument_type": request.payload["instrument_type"],
                    "constraints": constraints,
                    "target": target,
                    "acquisition_config": {"mode": "MANUAL", "extra_params": {}},
                    "guiding_config": {
                        "mode": "ON",
                        "optional": True,
                        "extra_params": {},
                    },
                    "instrument_configs": [
                        {
                            "exposure_time": exp_time,
                            "exposure_count": exp_count,
                            "mode": instrument_mode,
                            "extra_params": {
                                "offset_ra": 0,
                                "offset_dec": 0,
                                "defocus": 0,
                                "rotator_angle": 0,
                            },
                            "optical_elements": {"filter": f"{filt}"},
                        }
                    ],
                }
            )

        tstart = request.payload["start_date"]
        tend = request.payload["end_date"]

        windows = [{"start": tstart, "end": tend}]

        # The telescope class that should be used for this observation
        location = {"telescope_class": "4m0"}

        altdata = request.allocation.altdata

        # The full RequestGroup, with additional meta-data
        requestgroup = {
            "name": f"{request.obj.id}",  # The title
            "proposal": altdata["PROPOSAL_ID"],
            "ipp_value": request.payload["priority"],
            "operator": "SINGLE",
            "observation_type": request.payload["observation_mode"],
            "requests": [
                {
                    "configurations": configurations,
                    "windows": windows,
                    "location": location,
                }
            ],
        }

        return requestgroup


class SOAR_GHTS_Request:
    """A JSON structure for SOAR GHTS requests."""

    def __init__(self, request):
        """Initialize SOAR GHTS request.

        Parameters
        ----------

        request: skyportal.models.FollowupRequest
            The request to add to the queue and the SkyPortal database.

        """

        self.requestgroup = self._build_payload(request)

    def _build_payload(self, request):
        """Payload header for SOAR GHTS queue requests.

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
            "max_airmass": request.payload["maximum_airmass"],
            "min_lunar_distance": request.payload["minimum_lunar_distance"],
        }

        arc_constraints = {
            "max_airmass": 2 * request.payload["maximum_airmass"],
            "min_lunar_distance": request.payload["minimum_lunar_distance"],
        }

        # The target of the observation
        target = {
            "name": request.obj.id,
            "type": "ICRS",
            "ra": request.obj.ra,
            "dec": request.obj.dec,
            "proper_motion_ra": 0,
            "proper_motion_dec": 0,
            "parallax": 0,
            "epoch": 2000,
        }

        # The telescope class that should be used for this observation
        location = {"telescope_class": "4m0"}

        exp_time = request.payload["exposure_time"]
        exp_count = int(request.payload["exposure_counts"])

        arc_exposure_time = {
            "GHTS_B_400m1_2x2": 0.5,
            "GHTS_R_2100_6507A_1x2_slit0p45": 0.5,
            "GHTS_R_400m1_2x2": 0.5,
            "GHTS_R_400m2_2x2": 0.5,
            "GHTS_R_1200_CaNIR_1x2_slit0p8": 0.5,
            "GHTS_R_2100_5000A_1x2_slit1p0": 0.5,
        }

        configurations = [
            {
                "type": "SPECTRUM",
                "instrument_type": request.payload["instrument_type"],
                "constraints": constraints,
                "target": target,
                "acquisition_config": {"mode": "MANUAL"},
                "guiding_config": {"mode": "ON", "optional": False},
                "instrument_configs": [
                    {
                        "exposure_time": exp_time,
                        "exposure_count": exp_count,
                        "mode": request.payload["instrument_mode"],
                        "rotator_mode": "SKY",
                        "extra_params": {
                            "offset_ra": 0,
                            "offset_dec": 0,
                            "rotator_angle": 0,
                        },
                        "optical_elements": {},
                    }
                ],
            },
        ]
        if request.payload.get("include_calibrations", False):
            arcs = [
                {
                    "type": "ARC",
                    "instrument_type": request.payload["instrument_type"],
                    "instrument_configs": [
                        {
                            "exposure_count": 3,
                            "exposure_time": arc_exposure_time[
                                request.payload["instrument_mode"]
                            ],
                            "mode": request.payload["instrument_mode"],
                            "rotator_mode": "SKY",
                            "extra_params": {
                                "offset_ra": 0,
                                "offset_dec": 0,
                                "rotator_angle": 0,
                            },
                            "optical_elements": {},
                        }
                    ],
                    "acquisition_config": {"mode": "OFF", "extra_params": {}},
                    "guiding_config": {},
                    "target": target,
                    "constraints": arc_constraints,
                },
            ]
            configurations = arcs + configurations + arcs

        tstart = request.payload["start_date"]
        tend = request.payload["end_date"]

        windows = [{"start": tstart, "end": tend}]

        altdata = request.allocation.altdata

        # The full RequestGroup, with additional meta-data
        requestgroup = {
            "name": f"{request.obj.id}",  # The title
            "proposal": altdata["PROPOSAL_ID"],
            "ipp_value": request.payload["priority"],
            "operator": "SINGLE",
            "observation_type": request.payload["observation_mode"],
            "requests": [
                {
                    "configurations": configurations,
                    "windows": windows,
                    "location": location,
                }
            ],
        }

        return requestgroup


class SOAR_TripleSpec_Request:
    """A JSON structure for SOAR TripleSpec requests."""

    def __init__(self, request):
        """Initialize SOAR TripleSpec request.

        Parameters
        ----------

        request: skyportal.models.FollowupRequest
            The request to add to the queue and the SkyPortal database.

        """

        self.requestgroup = self._build_payload(request)

    def _build_payload(self, request):
        """Payload header for SOAR TripleSpec queue requests.

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
            "max_airmass": request.payload["maximum_airmass"],
            "min_lunar_distance": request.payload["minimum_lunar_distance"],
        }

        # The target of the observation
        target = {
            "name": request.obj.id,
            "type": "ICRS",
            "ra": request.obj.ra,
            "dec": request.obj.dec,
            "proper_motion_ra": 0,
            "proper_motion_dec": 0,
            "parallax": 0,
            "epoch": 2000,
        }

        # The telescope class that should be used for this observation
        location = {"telescope_class": "4m0"}

        exp_time = request.payload["exposure_time"]
        exp_count = int(request.payload["exposure_counts"])

        configurations = [
            {
                "type": "SPECTRUM",
                "instrument_type": "SOAR_TRIPLESPEC",
                "constraints": constraints,
                "target": target,
                "acquisition_config": {"mode": "MANUAL"},
                "guiding_config": {"mode": "ON", "optional": False},
                "instrument_configs": [
                    {
                        "exposure_time": exp_time,
                        "exposure_count": exp_count,
                        "mode": request.payload["instrument_mode"],
                        "rotator_mode": "SKY",
                        "extra_params": {
                            "offset_ra": 0,
                            "offset_dec": 0,
                            "rotator_angle": 90,
                        },
                        "optical_elements": {},
                    }
                ],
            },
        ]

        tstart = request.payload["start_date"]
        tend = request.payload["end_date"]

        windows = [{"start": tstart, "end": tend}]

        altdata = request.allocation.altdata

        # The full RequestGroup, with additional meta-data
        requestgroup = {
            "name": f"{request.obj.id}",  # The title
            "proposal": altdata["PROPOSAL_ID"],
            "ipp_value": request.payload["priority"],
            "operator": "SINGLE",
            "observation_type": request.payload["observation_mode"],
            "requests": [
                {
                    "configurations": configurations,
                    "windows": windows,
                    "location": location,
                }
            ],
        }

        return requestgroup


class SOARAPI(FollowUpAPI):
    """An interface to SOAR operations."""

    @staticmethod
    async def delete(request, session, **kwargs):
        """Delete a follow-up request from SOAR queue (all instruments).

        Parameters
        ----------
        request: skyportal.models.FollowupRequest
            The request to delete from the queue and the SkyPortal database.
        session: sqlalchemy.Session
            Database session for this transaction
        """

        from ..models import Allocation, FacilityTransaction, FollowupRequest

        # Reload with the lazy chains this method walks eager-loaded, since
        # async sessions raise on implicit lazy loads. Returns the same
        # identity-mapped object, so later request.status mutations persist.
        request = await session.scalar(
            sa.select(FollowupRequest)
            .where(FollowupRequest.id == request.id)
            .options(
                selectinload(FollowupRequest.allocation).selectinload(
                    Allocation.instrument
                ),
                selectinload(FollowupRequest.obj),
                selectinload(FollowupRequest.transactions),
            )
        )

        last_modified_by_id = request.last_modified_by_id
        obj_internal_key = request.obj.internal_key

        if len(request.transactions) == 0:
            await session.execute(
                sa.delete(FollowupRequest).where(FollowupRequest.id == request.id)
            )
            await session.commit()
        else:
            altdata = request.allocation.altdata

            if not altdata:
                raise ValueError("Missing allocation information.")

            content = request.transactions[0].response["content"]
            content = json.loads(content)

            if "id" in content:
                uid = content["id"]

                url = f"{requestpath}{uid}/cancel/"
                headers = {"Authorization": f"Token {altdata['API_TOKEN']}"}

                async with aiohttp.ClientSession() as http_session:
                    async with http_session.post(url, headers=headers) as r:
                        content = await r.text()
                        status = r.status

                if status >= 400:
                    raise ValueError(
                        f"Error cancelling request: status {status}: {content}"
                    )

                request.status = "deleted"

                transaction = FacilityTransaction(
                    request=http.serialize_aiohttp_request("POST", url, headers),
                    response=await http.serialize_aiohttp_response(r, content),
                    followup_request=request,
                    initiator_id=request.last_modified_by_id,
                )

                session.add(transaction)

            else:
                await session.execute(
                    sa.delete(FollowupRequest).where(FollowupRequest.id == request.id)
                )
                await session.commit()

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

    form_json_schema_altdata = {
        "type": "object",
        "properties": {
            "API_TOKEN": {
                "type": "string",
                "title": "API Token for SOAR",
            },
            "PROPOSAL_ID": {
                "type": "string",
                "title": "Proposal ID",
            },
        },
        "required": ["API_TOKEN", "PROPOSAL_ID"],
    }


class SOARGHTSIMAGERAPI(SOARAPI):
    """An interface to SOAR GHTS IMAGER operations."""

    # subclasses *must* implement the method below
    @staticmethod
    async def submit(request, session, **kwargs):
        """Submit a follow-up request to SOAR's GHTS REDCAM IMAGER.

        Parameters
        ----------
        request: skyportal.models.FollowupRequest
            The request to add to the queue and the SkyPortal database.
        session: sqlalchemy.Session
            Database session for this transaction
        """

        from ..models import Allocation, FacilityTransaction, FollowupRequest

        # Reload with the lazy chains the payload builder and this method walk
        # eager-loaded, since async sessions raise on implicit lazy loads.
        # Returns the same identity-mapped object, so status mutations persist.
        request = await session.scalar(
            sa.select(FollowupRequest)
            .where(FollowupRequest.id == request.id)
            .options(
                selectinload(FollowupRequest.allocation).selectinload(
                    Allocation.instrument
                ),
                selectinload(FollowupRequest.obj),
            )
        )

        altdata = request.allocation.altdata
        if not altdata:
            raise ValueError("Missing allocation information.")

        soarreq = SOAR_GHTS_IMAGER_Request(request)
        requestgroup = soarreq.requestgroup

        url = requestpath
        headers = {"Authorization": f"Token {altdata['API_TOKEN']}"}

        async with aiohttp.ClientSession() as http_session:
            async with http_session.post(url, headers=headers, json=requestgroup) as r:
                content = await r.text()
                status = r.status

        if status == 201:
            request.status = "submitted"
        else:
            request.status = content

        transaction = FacilityTransaction(
            request=http.serialize_aiohttp_request("POST", url, headers, requestgroup),
            response=await http.serialize_aiohttp_response(r, content),
            followup_request=request,
            initiator_id=request.last_modified_by_id,
        )

        session.add(transaction)
        await session.commit()

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

    form_json_schema = {
        "type": "object",
        "properties": {
            "observation_mode": {
                "type": "string",
                "enum": ["NORMAL", "RAPID_RESPONSE", "TIME_CRITICAL"],
                "default": "NORMAL",
            },
            "instrument_type": {
                "type": "string",
                "enum": ["SOAR_GHTS_BLUECAM_IMAGER", "SOAR_GHTS_REDCAM_IMAGER"],
                "default": "SOAR_GHTS_REDCAM_IMAGER",
                "title": "Instrument Type",
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
                "default": utcnow_naive().isoformat(),
                "title": "Start Date (UT)",
            },
            "end_date": {
                "type": "string",
                "title": "End Date (UT)",
                "default": (utcnow_naive() + timedelta(days=7)).isoformat(),
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
        "dependencies": {
            "instrument_type": {
                "oneOf": [
                    {
                        "properties": {
                            "instrument_type": {
                                "enum": ["SOAR_GHTS_BLUECAM_IMAGER"],
                            },
                            "observation_choices": {
                                "type": "array",
                                "title": "Desired Observations",
                                "items": {
                                    "type": "string",
                                    "enum": ["g-SDSS", "r-SDSS", "i-SDSS", "cn"],
                                },
                                "uniqueItems": True,
                                "minItems": 1,
                            },
                        }
                    },
                    {
                        "properties": {
                            "instrument_type": {
                                "enum": ["SOAR_GHTS_REDCAM_IMAGER"],
                            },
                            "observation_choices": {
                                "type": "array",
                                "title": "Desired Observations",
                                "items": {
                                    "type": "string",
                                    "enum": ["g-SDSS", "r-SDSS", "i-SDSS", "z-SDSS"],
                                },
                                "uniqueItems": True,
                                "minItems": 1,
                            },
                        }
                    },
                ],
            }
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


class SOARGHTSAPI(SOARAPI):
    """An interface to SOAR's GHTS operations."""

    # subclasses *must* implement the method below
    @staticmethod
    async def submit(request, session, **kwargs):
        """Submit a follow-up request to SOAR's GHTS.

        Parameters
        ----------
        request: skyportal.models.FollowupRequest
            The request to add to the queue and the SkyPortal database.
        session: sqlalchemy.Session
            Database session for this transaction
        """

        from ..models import Allocation, FacilityTransaction, FollowupRequest

        # Reload with the lazy chains the payload builder and this method walk
        # eager-loaded, since async sessions raise on implicit lazy loads.
        # Returns the same identity-mapped object, so status mutations persist.
        request = await session.scalar(
            sa.select(FollowupRequest)
            .where(FollowupRequest.id == request.id)
            .options(
                selectinload(FollowupRequest.allocation).selectinload(
                    Allocation.instrument
                ),
                selectinload(FollowupRequest.obj),
            )
        )

        altdata = request.allocation.altdata
        if not altdata:
            raise ValueError("Missing allocation information.")

        soarreq = SOAR_GHTS_Request(request)
        requestgroup = soarreq.requestgroup

        url = requestpath
        headers = {"Authorization": f"Token {altdata['API_TOKEN']}"}

        async with aiohttp.ClientSession() as http_session:
            async with http_session.post(url, headers=headers, json=requestgroup) as r:
                content = await r.text()
                status = r.status

        if status == 201:
            request.status = "submitted"
        else:
            request.status = content

        transaction = FacilityTransaction(
            request=http.serialize_aiohttp_request("POST", url, headers, requestgroup),
            response=await http.serialize_aiohttp_response(r, content),
            followup_request=request,
            initiator_id=request.last_modified_by_id,
        )

        session.add(transaction)
        await session.commit()

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

    form_json_schema = {
        "type": "object",
        "properties": {
            "observation_mode": {
                "type": "string",
                "enum": ["NORMAL", "RAPID_RESPONSE", "TIME_CRITICAL"],
                "default": "NORMAL",
            },
            "instrument_type": {
                "type": "string",
                "enum": ["SOAR_GHTS_BLUECAM", "SOAR_GHTS_REDCAM"],
                "default": "SOAR_GHTS_REDCAM",
                "title": "Instrument Type",
            },
            "include_calibrations": {
                "title": "Include calibrations?",
                "type": "boolean",
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
                "default": utcnow_naive().isoformat(),
                "title": "Start Date (UT)",
            },
            "end_date": {
                "type": "string",
                "title": "End Date (UT)",
                "default": (utcnow_naive() + timedelta(days=7)).isoformat(),
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
        "dependencies": {
            "instrument_type": {
                "oneOf": [
                    {
                        "properties": {
                            "instrument_type": {
                                "enum": ["SOAR_GHTS_BLUECAM"],
                            },
                            "instrument_mode": {
                                "type": "string",
                                "enum": [
                                    "GHTS_B_400m1_2x2",
                                ],
                                "default": "GHTS_B_400m1_2x2",
                                "title": "Instrument Mode",
                            },
                        }
                    },
                    {
                        "properties": {
                            "instrument_type": {
                                "enum": ["SOAR_GHTS_REDCAM"],
                            },
                            "instrument_mode": {
                                "type": "string",
                                "enum": [
                                    "GHTS_R_400m2_2x2",
                                    "GHTS_R_2100_6507A_1x2_slit0p45",
                                    "GHTS_R_400m1_2x2",
                                    "GHTS_R_1200_CaNIR_1x2_slit0p8",
                                    "GHTS_R_2100_5000A_1x2_slit1p0",
                                ],
                                "default": "GHTS_R_400m1_2x2",
                                "title": "Instrument Mode",
                            },
                        }
                    },
                ],
            }
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


class SOARTSPECAPI(SOARAPI):
    """An interface to SOAR's TripleSpec operations."""

    # subclasses *must* implement the method below
    @staticmethod
    async def submit(request, session, **kwargs):
        """Submit a follow-up request to SOAR's TripleSpec.

        Parameters
        ----------
        request: skyportal.models.FollowupRequest
            The request to add to the queue and the SkyPortal database.
        session: sqlalchemy.Session
            Database session for this transaction
        """

        from ..models import Allocation, FacilityTransaction, FollowupRequest

        # Reload with the lazy chains the payload builder and this method walk
        # eager-loaded, since async sessions raise on implicit lazy loads.
        # Returns the same identity-mapped object, so status mutations persist.
        request = await session.scalar(
            sa.select(FollowupRequest)
            .where(FollowupRequest.id == request.id)
            .options(
                selectinload(FollowupRequest.allocation).selectinload(
                    Allocation.instrument
                ),
                selectinload(FollowupRequest.obj),
            )
        )

        altdata = request.allocation.altdata
        if not altdata:
            raise ValueError("Missing allocation information.")

        soarreq = SOAR_TripleSpec_Request(request)
        requestgroup = soarreq.requestgroup

        url = requestpath
        headers = {"Authorization": f"Token {altdata['API_TOKEN']}"}

        async with aiohttp.ClientSession() as http_session:
            async with http_session.post(url, headers=headers, json=requestgroup) as r:
                content = await r.text()
                status = r.status

        if status == 201:
            request.status = "submitted"
        else:
            request.status = content

        transaction = FacilityTransaction(
            request=http.serialize_aiohttp_request("POST", url, headers, requestgroup),
            response=await http.serialize_aiohttp_response(r, content),
            followup_request=request,
            initiator_id=request.last_modified_by_id,
        )

        session.add(transaction)
        await session.commit()

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

    form_json_schema = {
        "type": "object",
        "properties": {
            "observation_mode": {
                "type": "string",
                "enum": ["NORMAL", "RAPID_RESPONSE", "TIME_CRITICAL"],
                "default": "NORMAL",
            },
            "instrument_mode": {
                "type": "string",
                "enum": [
                    "fowler16_coadds1",
                    "fowler1_coadds1",
                    "fowler8_coadds1",
                    "fowler4_coadds1",
                    "fowler1_coadds2",
                ],
                "default": "fowler16_coadds1",
                "title": "Instrument Mode",
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
                "default": utcnow_naive().isoformat(),
                "title": "Start Date (UT)",
            },
            "end_date": {
                "type": "string",
                "title": "End Date (UT)",
                "default": (utcnow_naive() + timedelta(days=7)).isoformat(),
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
