import requests
import arrow
import traceback
from json import JSONDecodeError
from datetime import datetime, timedelta

from baselayer.app.env import load_env
from baselayer.app.flow import Flow
from baselayer.log import make_log

from ..utils.calculations import deg2hms, deg2dms
from ..utils.offset import (
    _calculate_best_position_for_offset_stars,
    get_nearby_offset_stars,
)
from ..utils import http


from . import FollowUpAPI

env, cfg = load_env()

# Submission URL
API_URL = f"{cfg['app.gemini.protocol']}://{cfg['app.gemini.host']}:{cfg['app.gemini.port']}/too"

log = make_log('facility_apis/gemini')


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

        start_date = request.payload.get('start_date')
        end_date = request.payload.get('end_date')

        try:
            start_date = arrow.get(start_date)
            end_date = arrow.get(end_date)
        except Exception:
            raise ValueError('Invalid start_date or end_date')

        duration = (end_date - start_date).seconds

        obstime = start_date + timedelta(
            seconds=duration / 2
        )  # middle of the observation window
        obstime = obstime.strftime('%Y-%m-%d %H:%M:%S')

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

        name = offset_stars[0]['name']
        ra = offset_stars[0]['ra']
        dec = offset_stars[0]['dec']
        mag = round(offset_stars[0]['mag'], 1)
        pa = offset_stars[0]['pa']

        return name, ra, dec, f'{mag:.1f}/UC/Vega', pa

    def _build_payload(self, request, session):
        altdata = request.allocation.altdata
        if not altdata:
            raise ValueError('No altdata provided')

        email = altdata.get('email')

        programid = altdata.get('progid')
        programkey = altdata.get('progkey')

        if email is None:
            raise ValueError('Email is required')

        if programid is None or programkey is None:
            raise ValueError('Program id and key are required')

        obsid = 1  # TODO: investigate what this should be set to
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
            'l_exptime', 0
        )  # exposure time [seconds], if 0 then use the value in the template. Integer
        if l_exptime < 0 or l_exptime > 1200:
            raise ValueError('Exposure time must be between 0 and 1200 seconds')

        start_date = request.payload.get('start_date', '')
        end_date = request.payload.get('end_date', '')
        # make sure it's a valid readable datetime
        try:
            start_date = arrow.get(start_date)
            end_date = arrow.get(end_date)
        except Exception:
            raise ValueError('Invalid start_date or end_date')

        l_wDate = start_date.format(
            'YYYY-MM-DD'
        )  # UTC date YYYY-MM-DD for timing window
        l_wTime = start_date.format('HH:mm')  # UTC time HH:MM for timing window
        l_wDur = str(
            (end_date - start_date).seconds // 3600
        )  # Timing window duration, integer hours

        l_elmin = str(
            request.payload.get('l_elmin', 1.0)
        ).strip()  # minimum airmass value
        l_elmax = str(
            request.payload.get('l_elmax', 1.6)
        ).strip()  # maximum airmass value

        notetitle = request.payload.get('notetitle')  # optional
        note = request.payload.get('note')  # optional
        group = request.payload.get('group')  # optional

        if notetitle:
            notetitle = str(notetitle).strip()
        if note:
            note = str(note).strip()
        if group:
            group = str(group).strip()

        # Guide star selection
        gstarg, gsra, gsdec, gsmag, gspa = self._get_guide_star(request, session)

        if gstarg is None:
            raise ValueError('No guide star found')

        spa = str(gspa).strip()
        sgsmag = str(gsmag).strip() + '/UC/Vega'

        payload = {
            'prog': programid,
            'password': programkey,
            'email': email,
            'obsnum': obsnum,
            'target': target,
            'ra': ra,
            'dec': dec,
            'posangle': spa,  # 'mags': smags,
            'noteTitle': notetitle,
            'note': note,
            'ready': True,
            'windowStart': l_wDate,
            'windowStartUT': l_wTime,
            'windowDuration': l_wDur,
            'elevationType': 'airmass',
            'elevationMin': str(l_elmin).strip(),
            'elevationMax': str(l_elmax).strip(),
            'gstarg': gstarg,
            'gsra': gsra,
            'gsdec': gsdec,
            'gsmag': sgsmag,
        }

        if round(l_exptime) != 0:
            payload.update({'exptime': round(l_exptime)})

        if isinstance(group, str) and group.strip() != '':
            payload.update({'group': group.strip()})

        return payload


class GEMINIAPI(FollowUpAPI):
    @staticmethod
    def submit(request, session, **kwargs):
        """
        Submit a request to the Gemini Observatory
        """

        from ..models import FacilityTransaction

        altdata = request.allocation.altdata
        if not altdata:
            raise ValueError('Missing allocation information.')

        try:
            gemini_request = GeminiRequest(request, session)
        except Exception as e:
            traceback.print_exc()
            raise ValueError(f'Error building Gemini request: {e}')

        r = requests.post(API_URL, verify=False, params=gemini_request.payload)

        if r.status_code == 200:
            request.status = 'submitted'
        else:
            request.status = f'rejected: {r.content}'
            log(
                f'Failed to submit Gemini request for {request.id} (obj {request.obj.id}): {r.content}'
            )
            try:
                flow = Flow()
                flow.push(
                    request.last_modified_by_id,
                    'baselayer/SHOW_NOTIFICATION',
                    payload={
                        'message': f'Failed to submit Gemini request: {r.content}',
                        'type': 'error',
                    },
                )
            except Exception as e:
                log(f'Failed to send notification: {e}')
                pass

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
        'type': 'object',
        'properties': {
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
            'l_exptime': {
                'title': 'Exposure Time',
                'type': 'number',
                'description': '(if left at 0, the value in the template will be used)',
                'default': 0,
            },
            'l_elmin': {'title': 'Minimum airmass', 'type': 'number', 'default': 1.0},
            'l_elmax': {'title': 'Maximum airmass', 'type': 'number', 'default': 1.6},
            'notetitle': {
                'title': 'Note Title (optional)',
                'type': 'string',
            },
            'note': {
                'title': 'Note Content (optional)',
                'type': 'string',
            },
            'group': {
                'title': 'Group (optional)',
                'type': 'string',
            },
        },
        'required': ['l_exptime', 'l_elmin', 'l_elmax', 'start_date', 'end_date'],
    }

    form_json_schema_altdata = {
        "type": "object",
        "properties": {
            "email": {"type": "string", "title": "Email"},
            "progid": {
                "type": "string",
                "title": "Program ID",
                "description": "CAUTION: Gemini North and South have different program IDs, starting with GN or GS respectively. So, make sure to use the correct one for the instrument you've selected.",
            },
            "progkey": {"type": "string", "title": "Program Key (of the user)"},
        },
    }

    ui_json_schema = {}
