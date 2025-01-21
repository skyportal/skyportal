import traceback
from datetime import datetime, timedelta
from json import JSONDecodeError

import arrow
import requests

from baselayer.app.env import load_env
from baselayer.app.flow import Flow
from baselayer.log import make_log

from ..utils import http
from ..utils.calculations import deg2dms, deg2hms
from ..utils.offset import (
    _calculate_best_position_for_offset_stars,
    get_nearby_offset_stars,
)
from . import FollowUpAPI

env, cfg = load_env()

# Submission URL
API_URL = f"{cfg['app.gemini.protocol']}://{cfg['app.gemini.host']}:{cfg['app.gemini.port']}/too"

log = make_log("facility_apis/gemini")


class GeminiRequest:
    def __init__(self, request, session):
        self.payload = self._build_payload(request, session)

    def _get_guide_star(self, request, session):
        from ..models import Photometry

        best_ra, best_dec = request.obj.ra, request.obj.dec

        photometry = session.scalars(
            Photometry.select(session.user_or_token).where(
                Photometry.obj_id == request.obj.id,
                Photometry.origin.not_in(["alert_fp", "fp"]),
                Photometry.flux.is_not(None),
                Photometry.fluxerr.is_not(None),
                Photometry.ra.is_not(None),
                Photometry.dec.is_not(None),
            )
        ).all()

        if len(photometry) == 0:
            log(
                f"No photometry found for {request.obj.id}, defaulting to object position"
            )
        else:
            try:
                best_ra, best_dec = _calculate_best_position_for_offset_stars(
                    photometry,
                    fallback=(best_ra, best_dec),
                    how="snr2",
                )
            except JSONDecodeError:
                log(
                    f"Error calculating best position for {request.obj.id}, defaulting to object position"
                )
                best_ra, best_dec = request.obj.ra, request.obj.dec

        start_date = request.payload.get("start_date")
        end_date = request.payload.get("end_date")

        try:
            start_date = arrow.get(start_date)
            end_date = arrow.get(end_date)
        except Exception:
            raise ValueError("Invalid start_date or end_date")

        duration = (end_date - start_date).seconds

        obstime = start_date + timedelta(
            seconds=duration / 2
        )  # middle of the observation window
        obstime = obstime.strftime("%Y-%m-%d %H:%M:%S")

        offset_stars, _, _, _, _ = get_nearby_offset_stars(
            source_ra=best_ra,
            source_dec=best_dec,
            source_name=request.obj.id,
            how_many=1,
            radius_degrees=2 / 60,
            mag_limit=18,
            mag_min=10,
            min_sep_arcsec=2,
            obstime=obstime,
            use_source_pos_in_starlist=False,
        )
        if len(offset_stars) == 0:
            return None, None, None, None, None

        name = offset_stars[0]["name"]
        ra = offset_stars[0]["ra"]
        dec = offset_stars[0]["dec"]
        mag = round(offset_stars[0]["mag"], 1)
        pa = offset_stars[0]["pa"]

        return name, ra, dec, f"{mag:.1f}/UC/Vega", pa

    def _build_payload(self, request, session):
        altdata = request.allocation.altdata
        if not altdata:
            raise ValueError("No altdata provided")

        user_email = altdata.get("user_email")
        programid = altdata.get("programid")
        user_password = altdata.get("user_password")

        if user_email is None or programid is None or user_password is None:
            raise ValueError("user_email, user_password, and programid are required")

        # create the group str from the allocation's group nickname, PI, and id
        allocation_group_name = (
            request.allocation.group.nickname
            if request.allocation.group.nickname
            else request.allocation.group.name
        )
        allocation_group_name = allocation_group_name.replace(" ", "")
        allocation_group_pi = request.allocation.pi.replace(" ", "")
        allocation_id = request.allocation.id
        group = f"{allocation_group_name}_{allocation_group_pi}_{allocation_id}"
        group = str(group.replace(" ", "_")).strip()

        obsid = request.payload.get("template_id")
        # it needs to be castable to an int
        try:
            obsid = int(obsid)
        except Exception:
            raise ValueError("Invalid template ID")

        if (
            isinstance(altdata.get("template_ids"), str | list)
            and len(altdata.get("template_ids")) > 0
        ):
            template_ids = []
            try:
                if isinstance(altdata.get("template_ids"), str):
                    template_ids = altdata.get("template_ids").split(",")
                template_ids = [int(i) for i in template_ids]
            except Exception:
                raise ValueError("Invalid template IDs specified in altdata")
            if len(template_ids) > 0 and obsid not in template_ids:
                raise ValueError(
                    f"Invalid template ID, must be one of: {str(template_ids)}"
                )

        obsnum = str(obsid).strip()
        target = request.obj.id
        ra, dec = request.obj.ra, request.obj.dec
        # the ra dec are in deg, we need them in hms dms
        ra, dec = deg2hms(ra), deg2dms(dec)

        # target brightness
        # TODO: query the photometry of the object, get the latest detection
        # and build a string like: mag/filter/magsys
        # smags = "20.0/r/AB"
        # (it's optional, so let's ignore it for now, for simplicity sake)

        l_exptime = request.payload.get(
            "l_exptime", 0
        )  # exposure time [seconds], if 0 then use the value in the template. Integer
        if l_exptime < 0 or l_exptime > 1200:
            raise ValueError("Exposure time must be between 0 and 1200 seconds")

        start_date = request.payload.get("start_date", "")
        end_date = request.payload.get("end_date", "")
        # make sure it's a valid readable datetime
        try:
            start_date = arrow.get(start_date)
            end_date = arrow.get(end_date)
        except Exception:
            raise ValueError("Invalid start_date or end_date")

        l_wDate = start_date.format(
            "YYYY-MM-DD"
        )  # UTC date YYYY-MM-DD for timing window
        l_wTime = start_date.format("HH:mm")  # UTC time HH:MM for timing window
        l_wDur = str(
            (end_date - start_date).seconds // 3600
        )  # Timing window duration, integer hours

        l_elmin = str(
            request.payload.get("l_elmin", 1.0)
        ).strip()  # minimum airmass value
        l_elmax = str(
            request.payload.get("l_elmax", 1.6)
        ).strip()  # maximum airmass value

        notetitle = request.payload.get("notetitle")  # optional
        note = request.payload.get("note")  # optional

        if notetitle:
            notetitle = str(notetitle).strip()
        if note:
            note = str(note).strip()

        # Guide star selection
        gstarg, gsra, gsdec, gsmag, gspa = self._get_guide_star(request, session)

        if gstarg is None:
            raise ValueError("No guide star found")

        spa = str(gspa).strip()
        sgsmag = str(gsmag).strip() + "/UC/Vega"

        payload = {
            "prog": programid,
            "email": user_email,
            "password": user_password,
            "obsnum": obsnum,
            "target": target,
            "ra": ra,
            "dec": dec,
            "posangle": spa,
            "noteTitle": notetitle,
            "note": note,
            "ready": True,
            "windowDate": l_wDate,
            "windowTime": l_wTime,
            "windowDuration": l_wDur,
            "elevationType": "airmass",
            "elevationMin": str(l_elmin).strip(),
            "elevationMax": str(l_elmax).strip(),
            "gstarg": gstarg,
            "gsra": gsra,
            "gsdec": gsdec,
            "gsmag": sgsmag,
            "gsprobe": "OIWFS",
            "group": group,
        }

        if round(l_exptime) != 0:
            payload.update({"exptime": round(l_exptime)})

        return payload


class GEMINIAPI(FollowUpAPI):
    @staticmethod
    def validate_altdata(altdata, **kwargs):
        if not altdata:
            raise ValueError("Missing allocation information.")

        if not isinstance(altdata, dict):
            raise ValueError("Invalid altdata format")

        user_email = str(altdata.get("user_email")).strip()
        user_password = str(altdata.get("user_password")).strip()
        programid = str(altdata.get("programid")).strip()
        if not any(programid.startswith(x) for x in ["GN", "GS"]):
            raise ValueError("Invalid program ID, must start with GN or GS")

        instrument = kwargs.get("instrument")
        if instrument is None:
            raise ValueError("Instrument not provided, required for validation")

        instrument_name = str(instrument["name"]).lower().strip()
        if any(
            x in instrument_name for x in ["south", "gs"]
        ) and not programid.startswith("GS"):
            raise ValueError("Invalid program ID for Gemini South, must start with GS")
        elif any(
            x in instrument_name for x in ["north", "gn"]
        ) and not programid.startswith("GN"):
            raise ValueError("Invalid program ID for Gemini North, must start with GN")
        elif not any(x in instrument_name for x in ["north", "south", "gn", "gs"]):
            raise ValueError("Invalid instrument, must be Gemini North or South")

        if not user_email or not user_password or not programid:
            raise ValueError("user_email, user_password, and programid are required")

        template_ids = altdata.get("template_ids")
        if template_ids:
            if not isinstance(template_ids, str | list):
                raise ValueError("Invalid template IDs format")
            if isinstance(template_ids, str):
                template_ids = template_ids.split(",")
            try:
                template_ids = [int(i) for i in template_ids]
            except Exception:
                raise ValueError("Invalid template IDs format")
            if len(template_ids) > 0:
                altdata["template_ids"] = template_ids

        return altdata

    @staticmethod
    def submit(request, session, **kwargs):
        """
        Submit a request to the Gemini Observatory
        """

        from ..models import FacilityTransaction

        altdata = request.allocation.altdata
        if not altdata:
            raise ValueError("Missing allocation information.")

        try:
            gemini_request = GeminiRequest(request, session)
        except Exception as e:
            log(traceback.format_exc())
            raise ValueError(f"Error building Gemini request: {e}")

        r = requests.post(API_URL, verify=False, params=gemini_request.payload)

        if r.status_code == 200:
            request.status = "submitted"
        else:
            request.status = f"rejected: {r.content}"
            log(
                f"Failed to submit Gemini request for {request.id} (obj {request.obj.id}): {r.content}"
            )
            try:
                flow = Flow()
                flow.push(
                    request.last_modified_by_id,
                    "baselayer/SHOW_NOTIFICATION",
                    payload={
                        "note": f"Failed to submit Gemini request: {r.content}",
                        "type": "error",
                    },
                )
            except Exception as e:
                log(f"Failed to send notification: {e}")

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

    form_json_schema = {
        "type": "object",
        "properties": {
            "template_id": {
                "title": "Template ID",
                "type": "integer",
                "description": "The template ID is found on the program's page on the OT",
            },
            "start_date": {
                "title": "Start Date (UT)",
                "type": "string",
                "default": str(datetime.utcnow() - timedelta(days=7)).replace("T", ""),
            },
            "end_date": {
                "title": "End Date (UT)",
                "type": "string",
                "default": str(datetime.utcnow()).replace("T", ""),
            },
            "l_exptime": {
                "title": "Exposure Time",
                "type": "number",
                "description": "(if left at 0, the value in the template will be used)",
                "default": 0,
            },
            "l_elmin": {"title": "Minimum airmass", "type": "number", "default": 1.0},
            "l_elmax": {"title": "Maximum airmass", "type": "number", "default": 1.6},
            "notetitle": {
                "title": "Note Title (optional)",
                "type": "string",
            },
            "note": {
                "title": "Note Content (optional)",
                "type": "string",
            },
        },
        "required": [
            "l_exptime",
            "l_elmin",
            "l_elmax",
            "start_date",
            "end_date",
            "template_id",
        ],
    }

    form_json_schema_altdata = {
        "type": "object",
        "properties": {
            "user_email": {"type": "string", "title": "Email"},
            "user_password": {"type": "string", "title": "Password"},
            "programid": {
                "type": "string",
                "title": "Program ID",
                "description": "CAUTION: Gemini North and South have different program IDs, starting with GN or GS respectively. So, make sure to use the correct one for the instrument you've selected.",
            },
            "template_ids": {
                "type": "string",
                "title": "Template IDs",
                "description": "List of available templates, comma separated (optional)",
            },
        },
        "required": ["user_email", "user_password", "programid"],
    }

    ui_json_schema = {}
