import json
import time
import urllib

import astropy
import requests
from skyportal.models.stream import Stream
import sqlalchemy as sa
from sqlalchemy.orm import scoped_session, sessionmaker

from baselayer.app.env import load_env
from baselayer.app.models import init_db
from baselayer.log import make_log

from baselayer.app.flow import Flow
from skyportal.handlers.api.photometry import serialize
from skyportal.models import (
    DBSession,
    Instrument,
    Photometry,
    TNSRobot,
    TNSRobotGroupAutoreporter,
    TNSRobotSubmission,
    User,
    Source,
    GroupUser,
)
from skyportal.utils.tns import (
    SNCOSMO_TO_TNSFILTER,
    TNS_INSTRUMENT_IDS,
    get_IAUname,
    get_internal_names,
)
from skyportal.utils.http import serialize_requests_response
from skyportal.utils.services import check_loaded

env, cfg = load_env()
log = make_log('tns_queue')

init_db(**cfg['database'])

Session = scoped_session(sessionmaker())

TNS_URL = cfg['app.tns.endpoint']
report_url = urllib.parse.urljoin(TNS_URL, 'api/bulk-report')
print(f"REPORT URL: {report_url}")
search_frontend_url = urllib.parse.urljoin(TNS_URL, 'search')


# we create a custom exception to be able to catch it and log the error message
# useful to make the difference between unexpected errors and errors that we expect
# and want to set as the status of the TNSRobotSubmission + notify the user
class TNSReportError(Exception):
    pass


def find_accessible_tnsrobot_groups(submission_request, tnsrobot, user, session):
    """Verify that the user is allowed to submit to TNS with this robot, and return the TNSRobotGroups that the user is allowed to submit from.

    Parameters
    ----------
    tnsrobot : `~skyportal.models.TNSRobot`
        The TNSRobot to submit with.
    user : `~skyportal.models.User`
        The user submitting the report.
    submission_request : `~skyportal.models.TNSRobotSubmission`
        The submission request.
    session : `~sqlalchemy.orm.Session`
        The database session to use.

    Returns
    -------
    tnsrobot_groups : list of `~skyportal.models.TNSRobotGroup`
        The TNSRobotGroups that the user is allowed to submit to with this robot.
    """
    tnsrobot_id = tnsrobot.id
    user_id = user.id

    tnsrobot_groups = tnsrobot.groups
    user_accessible_group_ids = [group.id for group in user.accessible_groups]
    tnsrobot_groups = [
        tnsrobot_group
        for tnsrobot_group in tnsrobot_groups
        if tnsrobot_group.group_id in user_accessible_group_ids
    ]

    if len(tnsrobot_groups) == 0:
        raise TNSReportError(
            f'User {user_id} does not have access to any group with TNSRobot {tnsrobot_id}.'
        )

    # if this is an auto_submission, we need to check if the group has auto-report enabled
    # and if the user is an auto-reporter for that group
    if submission_request.auto_submission:
        tnsrobot_groups_with_autoreport = [
            tnsrobot_group
            for tnsrobot_group in tnsrobot_groups
            if tnsrobot_group.auto_report is True
        ]
        if len(tnsrobot_groups_with_autoreport) == 0:
            raise TNSReportError(
                f'No group with TNSRobot {tnsrobot_id} set to auto-report.'
            )

        # we filter out the groups that this user is not an auto-reporter for
        tnsrobot_groups_with_autoreport = [
            tnsrobot_group
            for tnsrobot_group in tnsrobot_groups_with_autoreport
            if session.scalar(
                sa.select(TNSRobotGroupAutoreporter).where(
                    TNSRobotGroupAutoreporter.tnsrobot_group_id == tnsrobot_group.id,
                    TNSRobotGroupAutoreporter.group_user_id.in_(
                        sa.select(GroupUser.id).where(
                            GroupUser.user_id == user_id,
                            GroupUser.group_id == tnsrobot_group.group_id,
                        )
                    ),
                )
            )
        ]

        if len(tnsrobot_groups_with_autoreport) == 0:
            raise TNSReportError(
                f'User {user_id} is not an auto-reporter for any group with TNSRobot {tnsrobot_id} set to auto-report.'
            )

    return tnsrobot_groups


def apply_existing_tnsreport_rules(tns_headers, tnsrobot, submission_request, session):
    """Apply the rules for existing TNS reports to the submission request.

    Parameters
    ----------
    tns_headers : dict
        The headers to use for TNS requests.
    tnsrobot : `~skyportal.models.TNSRobot`
        The TNSRobot to submit with.
    submission_request : `~skyportal.models.TNSRobotSubmission`
        The submission request.
    session : `~sqlalchemy.orm.Session`
        The database session to use.
    """
    # if the bot is set up to only report objects to TNS if they are not already there,
    # we check if an object is already on TNS (within 2 arcsec of the object's position)
    # and if it is, we skip the submission
    # otherwise, we submit as long as there are no reports with the same internal source name
    # (i.e. the same obj_id from the same survey)
    altdata = tnsrobot.altdata
    obj_id = submission_request.obj_id

    _, existing_tns_name = get_IAUname(altdata['api_key'], tns_headers, obj_id=obj_id)
    if existing_tns_name is not None:
        if not tnsrobot.report_existing:
            raise TNSReportError(
                f'{obj_id} already posted to TNS as {existing_tns_name}.'
            )
        else:
            # look if the object on TNS has already been reported by the same survey (same internal name, here being the obj_id)
            internal_names = get_internal_names(
                altdata['api_key'], tns_headers, tns_name=existing_tns_name
            )
            if len(internal_names) > 0 and obj_id in internal_names:
                raise TNSReportError(
                    f'{obj_id} already posted to TNS with the same internal source name.'
                )


def find_source_to_submit(submission_request, tnsrobot_groups, session):
    """Find the source to submit to TNS.

    Parameters
    ----------
    submission_request : `~skyportal.models.TNSRobotSubmission`
        The submission request.
    tnsrobot_groups : list of `~skyportal.models.TNSRobotGroup`
        The TNSRobotGroups that the user is allowed to submit to with this robot.
    session : `~sqlalchemy.orm.Session`
        The database session to use.

    Returns
    -------
    source : `~skyportal.models.Source`
        The source to submit.
    """
    # Get the sources saved to the groups that have access to this TNS robot,
    # this is so if a user that has access to this robot saved the obj as a source before,
    # he is the first author when another user auto-submits the source
    tnsrobot_id = submission_request.tnsrobot_id
    obj_id = submission_request.obj_id
    source = session.scalar(
        sa.select(Source)
        .where(
            Source.obj_id == obj_id,
            Source.active.is_(True),
            Source.group_id.in_(
                [tnsrobot_group.group_id for tnsrobot_group in tnsrobot_groups]
            ),
        )
        .order_by(Source.saved_at.asc())
    )

    if source is None:
        if submission_request.auto_submission:
            raise TNSReportError(
                f'No source {obj_id} saved to any group with TNSRobot {tnsrobot_id}.'
            )
        else:
            raise TNSReportError(
                f'No source {obj_id} saved to group with TNSRobot {tnsrobot_id}.'
            )

    return source


def build_reporters_string(submission_request, source, tnsrobot, session):
    """Build the reporters string for the TNS report.

    Parameters
    ----------
    submission_request : `~skyportal.models.TNSRobotSubmission`
        The submission request.
    source : `~skyportal.models.Source`
        The source to submit.
    tnsrobot : `~skyportal.models.TNSRobot`
        The TNSRobot to submit with.
    session : `~sqlalchemy.orm.Session`
        The database session to use.

    Returns
    -------
    reporters : str
        The reporters string.
    """
    tnsrobot_id = submission_request.tnsrobot_id
    user_id = submission_request.user_id
    obj_id = submission_request.obj_id
    if submission_request.custom_reporting_string not in [None, ""]:
        reporters = submission_request.custom_reporting_string
    else:
        # if the user that first ever saved this source to a group that have access to this
        # tnsrobot is not the user that is submitting, we make them the first author
        # and the submitter the second author
        author_ids = []
        if (
            submission_request.auto_submission
            and source.saved_by_id is not None
            and source.saved_by_id != user_id
        ):
            author_ids.append(source.saved_by_id)
        author_ids.append(user_id)

        coauthor_ids = [coauthor.user_id for coauthor in tnsrobot.coauthors]
        for coauthor_id in coauthor_ids:
            if coauthor_id not in author_ids:
                author_ids.append(coauthor_id)

        authors = (
            session.scalars(sa.select(User).where(User.id.in_(author_ids)))
            .unique()
            .all()
        )
        # reorder the authors to match the order of the author_ids
        authors = sorted(authors, key=lambda author: author_ids.index(author.id))

        if len(authors) == 0:
            raise TNSReportError(
                f'No authors found for tnsrobot {tnsrobot_id} and source {obj_id}, cannot report to TNS.'
            )
        # if any of the users are missing an affiliation, we don't submit
        authors_with_missing_affiliations = [
            author for author in authors if len(author.affiliations) == 0
        ]
        if len(authors_with_missing_affiliations) > 0:
            raise TNSReportError(
                f'One or more authors are missing an affiliation: {", ".join([author.username for author in authors_with_missing_affiliations])}, cannot report {obj_id} to TNS.'
            )

        reporters = ', '.join(
            [
                f'{author.first_name} {author.last_name} ({author.affiliations[0]})'
                for author in authors
            ]
        )
        if tnsrobot.acknowledgments in [None, ""]:
            raise TNSReportError(
                f'No acknowledgments found for tnsrobot {tnsrobot_id}, cannot report {obj_id} to TNS.'
            )

        reporters += f' {str(tnsrobot.acknowledgments).strip()}'

    return reporters


def find_accessible_instrument_ids(submission_request, tnsrobot, user, session):
    """Find the instrument IDs accessible to the TNSRobot whem submitting photometry.

    Parameters
    ----------
    submission_request : `~skyportal.models.TNSRobotSubmission`
        The submission request.
    tnsrobot : `~skyportal.models.TNSRobot`
        The TNSRobot to submit with.
    user : `~skyportal.models.User`
        The user submitting the request.
    session : `~sqlalchemy.orm.Session`
        The database session to use.

    Returns
    -------
    instrument_ids : list of int
        The instrument IDs accessible to the TNSRobot.
    """
    tnsrobot_id = tnsrobot.id
    # for now we limit it to instruments and filters we have mapped to TNS
    all_tns_instruments = session.scalars(
        Instrument.select(user).where(
            sa.func.lower(Instrument.name).in_(list(TNS_INSTRUMENT_IDS.keys()))
        )
    ).all()
    if len(all_tns_instruments) == 0:
        raise TNSReportError(
            'No instrument with known TNS IDs available or accessible to this user.'
        )

    instrument_ids = [instrument.id for instrument in tnsrobot.instruments]

    # keep the instruments from all_tns_instruments that are in the list of instruments this robot is allowed to use
    # unless no instruments are specified, in which case we use all instruments
    if len(instrument_ids) > 0:
        all_tns_instruments = [
            instrument
            for instrument in all_tns_instruments
            if instrument.id in instrument_ids
        ]
        if len(all_tns_instruments) == 0:
            raise TNSReportError(
                f'No instruments specified for TNSRobot {tnsrobot_id} are accessible.'
            )

    # if the submission has a list of instrument_ids to use, we only use those
    if (
        submission_request.instrument_ids is not None
        and len(submission_request.instrument_ids) > 0
    ):
        all_tns_instruments = [
            instrument
            for instrument in all_tns_instruments
            if instrument.id in submission_request.instrument_ids
        ]
        if len(all_tns_instruments) == 0:
            raise TNSReportError(
                f'No instruments specified for submission with TNSRobot {tnsrobot_id} are accessible.'
            )

    instrument_ids = [instrument.id for instrument in all_tns_instruments]
    return instrument_ids


def find_accessible_stream_ids(submission_request, tnsrobot, user, session):
    """Find the stream IDs accessible to the TNSRobot when submitting photometry.

    Parameters
    ----------
    submission_request : `~skyportal.models.TNSRobotSubmission`
        The submission request.
    tnsrobot : `~skyportal.models.TNSRobot`
        The TNSRobot to submit with.
    user : `~skyportal.models.User`
        The user submitting the request.
    session : `~sqlalchemy.orm.Session`
        The database session to use.

    Returns
    -------
    stream_ids : list of int
        The stream IDs accessible to the TNSRobot.
    """
    tnsrobot_id = tnsrobot.id

    stream_ids = [stream.id for stream in tnsrobot.streams]

    all_streams = session.scalars(Stream.select(user))

    if len(stream_ids) > 0:
        all_streams = [stream for stream in all_streams if stream.id in stream_ids]
        if len(all_streams) == 0:
            raise TNSReportError(
                f'No streams specified for TNSRobot {tnsrobot_id} are accessible'
            )

    # if the submission has a list of stream_ids to use, we only use those
    if (
        submission_request.stream_ids is not None
        and len(submission_request.stream_ids) > 0
    ):
        all_streams = [
            stream
            for stream in all_streams
            if stream.id in submission_request.stream_ids
        ]
        if len(all_streams) == 0:
            raise TNSReportError(
                f'No streams specified for submission with TNSRobot {tnsrobot_id} are accessible.'
            )

    stream_ids = [stream.id for stream in all_streams]
    return stream_ids


def build_at_report(
    submission_request, tnsrobot, source, reporters, photometry, session
):
    """Build the AT report for a TNSRobot submission.

    Parameters
    ----------
    submission_request : `~skyportal.models.TNSRobotSubmission`
        The submission request.
    tnsrobot : `~skyportal.models.TNSRobot`
        The TNSRobot to submit with.
    source : `~skyportal.models.Source`
        The source to submit.
    reporters : str
        The reporters to use for the submission.
    photometry : list of `~skyportal.models.Photosometry`
        The photometry to submit.
    session : `~sqlalchemy.orm.Session`
        The database session to use.

    Returns
    -------
    at_report : dict
        The AT report to submit.
    """
    obj_id = submission_request.obj_id
    archival = submission_request.archival
    archival_comment = submission_request.archival_comment
    # SPLIT THE PHOTOMETRY INTO DETECTIONS AND NON-DETECTIONS
    time_first, mag_first, magerr_first, filt_first, instrument_first = (
        None,
        None,
        None,
        None,
        None,
    )
    time_last, mag_last, magerr_last, filt_last, instrument_last = (
        None,
        None,
        None,
        None,
        None,
    )
    (
        time_last_nondetection,
        limmag_last_nondetection,
        filt_last_nondetection,
        instrument_last_nondetection,
    ) = (None, None, None, None)

    # non detections are those with mag=None
    detections, non_detections = [], []

    for phot in photometry:
        if phot['mag'] in [None, '', 'None', 'nan']:
            non_detections.append(phot)
        else:
            detections.append(phot)

    if len(detections) == 0:
        raise TNSReportError(f'Need at least one detection for TNS report of {obj_id}.')

    if len(non_detections) == 0 and not archival:
        raise TNSReportError(
            f'Need at least one non-detection for non-archival TNS report of {obj_id}.'
        )

    # sort each by mjd ascending
    non_detections = sorted(non_detections, key=lambda k: k['mjd'])
    detections = sorted(detections, key=lambda k: k['mjd'])

    time_first = detections[0]['mjd']
    mag_first = detections[0]['mag']
    magerr_first = detections[0]['magerr']
    filt_first = SNCOSMO_TO_TNSFILTER[detections[0]['filter']]
    instrument_first = TNS_INSTRUMENT_IDS[detections[0]['instrument_name'].lower()]

    time_last = detections[-1]['mjd']
    mag_last = detections[-1]['mag']
    magerr_last = detections[-1]['magerr']
    filt_last = SNCOSMO_TO_TNSFILTER[detections[-1]['filter']]
    instrument_last = TNS_INSTRUMENT_IDS[detections[-1]['instrument_name'].lower()]

    # remove non detections that are after the first detection
    non_detections = [phot for phot in non_detections if phot['mjd'] < time_first]

    if not archival and len(non_detections) == 0:
        raise TNSReportError(
            f'No non-detections found before first detection for TNS report of {obj_id}.'
        )

    # we already filtered the non detections to only those that are before the first detection
    # so we can just take the last one
    if not archival:
        time_last_nondetection = non_detections[-1]['mjd']
        limmag_last_nondetection = non_detections[-1]['limiting_mag']
        filt_last_nondetection = SNCOSMO_TO_TNSFILTER[non_detections[-1]['filter']]
        instrument_last_nondetection = TNS_INSTRUMENT_IDS[
            non_detections[-1]['instrument_name'].lower()
        ]

    proprietary_period = {
        "proprietary_period_value": 0,
        "proprietary_period_units": "years",
    }

    if archival:
        non_detection = {
            "archiveid": "0",
            "archival_remarks": archival_comment,
        }
    else:
        non_detection = {
            "obsdate": astropy.time.Time(time_last_nondetection, format='mjd').jd,
            "limiting_flux": limmag_last_nondetection,
            "flux_units": "1",
            "filter_value": filt_last_nondetection,
            "instrument_value": instrument_last_nondetection,
        }

    phot_first = {
        "obsdate": astropy.time.Time(time_first, format='mjd').jd,
        "flux": mag_first,
        "flux_err": magerr_first,
        "flux_units": "1",
        "filter_value": filt_first,
        "instrument_value": instrument_first,
    }

    phot_last = {
        "obsdate": astropy.time.Time(time_last, format='mjd').jd,
        "flux": mag_last,
        "flux_err": magerr_last,
        "flux_units": "1",
        "filter_value": filt_last,
        "instrument_value": instrument_last,
    }

    at_report = {
        "ra": {"value": source.obj.ra},
        "dec": {"value": source.obj.dec},
        "reporting_group_id": tnsrobot.source_group_id,
        "discovery_data_source_id": tnsrobot.source_group_id,
        "internal_name_format": {
            "prefix": instrument_first,
            "year_format": "YY",
            "postfix": "",
        },
        "internal_name": obj_id,
        "reporter": reporters,
        "discovery_datetime": astropy.time.Time(
            time_first, format='mjd'
        ).datetime.strftime('%Y-%m-%d %H:%M:%S.%f'),
        "at_type": 1,  # allow other options?
        "proprietary_period_groups": [tnsrobot.source_group_id],
        "proprietary_period": proprietary_period,
        "non_detection": non_detection,
        "photometry": {"photometry_group": {"0": phot_first, "1": phot_last}},
    }

    report = {"at_report": {"0": at_report}}

    return report


def send_at_report(submission_request, tnsrobot, report, tns_headers):
    """Send an AT report to TNS.

    Parameters
    ----------
    submission_request : `~skyportal.models.SubmissionRequest`
        The submission request to send to TNS.
    tnsrobot : `~skyportal.models.TNSRobot`
        The TNSRobot to use for sending the report.
    report : dict
        The AT report to send to TNS.
    tns_headers : dict
        The headers to use for the TNS API request.
    """
    obj_id = submission_request.obj_id
    tnsrobot_id = tnsrobot.id
    data = {
        'api_key': tnsrobot.altdata['api_key'],
        'data': json.dumps(report),
    }

    status = None
    submission_id = None
    serialized_response = None

    if not tnsrobot.testing:
        status_code = 0
        n_retries = 0
        r = None
        while n_retries < 24:  # 6 * 4 * 10 seconds = 4 minutes of retries
            r = requests.post(report_url, headers=tns_headers, data=data)
            status_code = r.status_code
            if status_code == 429:
                status = f"Exceeded TNS API rate limit when submitting {obj_id} to TNS with TNSRobot {tnsrobot_id}"
                log(f"{status}, waiting 10 seconds before retrying...")
                time.sleep(10)
                n_retries += 1
                continue
            if status_code == 200:
                tns_id = r.json()['data']['report_id']
                log(
                    f'Successfully submitted {obj_id} to TNS with request ID {tns_id} for TNSRobot {tnsrobot_id}'
                )
                submission_id = tns_id
                status = 'submitted'
            elif status_code == 401:
                status = f"Unauthorized to submit {obj_id} to TNS with TNSRobot {tnsrobot_id}, credentials may be invalid"
            else:
                status = f"Failed to submit {obj_id} to TNS with TNSRobot {tnsrobot_id}: {r.content}"
            break

        if status_code == 429:
            status = f"{status}, and exceeded number of retries (6)"
        submission_request.status = f'error: {status}' if status_code != 200 else status

        if submission_id is not None:
            submission_id = submission_id

        if isinstance(r, requests.models.Response):
            # we store the request's TNS response in the database for bookkeeping and debugging
            serialized_response = serialize_requests_response(r)

    else:
        log(
            f"TNS Robot {tnsrobot_id} is in testing mode, not submitting {obj_id} to TNS."
        )
        status = 'testing mode, not submitted to TNS'

    return status, submission_id, serialized_response


def process_submission_request(submission_request, session):
    """Process a TNS submission request.

    Parameters
    ----------
    submission_request : `~skyportal.models.TNSRobotSubmission`
        The submission request.
    session : `~sqlalchemy.orm.Session`
        The database session to use.
    """
    obj_id = submission_request.obj_id
    tnsrobot_id = submission_request.tnsrobot_id
    user_id = submission_request.user_id
    try:
        user = session.scalar(sa.select(User).where(User.id == user_id))
        if user is None:
            raise TNSReportError(f'No user found with ID {user_id}.')

        tnsrobot = session.scalar(
            TNSRobot.select(user).where(TNSRobot.id == tnsrobot_id)
        )
        if tnsrobot is None:
            raise TNSReportError(
                f'No TNSRobot found with ID {tnsrobot_id} or user {user_id} does not have access to it.'
            )
        altdata = tnsrobot.altdata
        if not altdata or 'api_key' not in altdata:
            raise TNSReportError(f'No TNS API key found for TNSRobot {tnsrobot_id}.')

        tnsrobot_groups = find_accessible_tnsrobot_groups(
            submission_request, tnsrobot, user, session
        )

        tns_headers = {
            'User-Agent': f'tns_marker{{"tns_id":{tnsrobot.bot_id},"type":"bot", "name":"{tnsrobot.bot_name}"}}'
        }

        apply_existing_tnsreport_rules(
            tns_headers, tnsrobot, submission_request, session
        )

        source = find_source_to_submit(submission_request, tnsrobot_groups, session)

        reporters = build_reporters_string(
            submission_request, source, tnsrobot, session
        )

        # set it now, so we already have it if we need to reprocess the request
        submission_request.custom_reporting_string = reporters

        archival = submission_request.archival
        archival_comment = submission_request.archival_comment
        if archival and (archival_comment in [None, ""]):
            raise TNSReportError(
                f'Archival submission requested for {obj_id} but no archival_comment provided.'
            )

        instrument_ids = find_accessible_instrument_ids(
            submission_request, tnsrobot, user, session
        )
        stream_ids = find_accessible_stream_ids(
            submission_request, tnsrobot, user, session
        )

        # FETCH THE PHOTOMETRY (FILTERED BY INSTRUMENTS)
        photometry = session.scalars(
            Photometry.select(user).where(
                Photometry.obj_id == obj_id,
                Photometry.instrument_id.in_(instrument_ids),
            )
        ).all()

        if len(photometry) == 0:
            raise TNSReportError(
                f'No photometry available for {obj_id} with instruments {instrument_ids}.'
            )

        # FILTER THE PHOTOMETRY BY STREAMS
        if len(stream_ids) > 0:
            phot_to_keep = []
            for phot in photometry:
                for stream in phot.streams:
                    if stream.id in stream_ids:
                        phot_to_keep.append(phot)
                        break
            if len(phot_to_keep) == 0:
                raise TNSReportError(
                    f'No photometry with streams {stream_ids} available for {obj_id}.'
                )
            photometry = phot_to_keep

        # SERIALIZE THE PHOTOMETRY
        photometry = [serialize(phot, 'ab', 'mag') for phot in photometry]

        # MAKE THE AT REPORT
        report = build_at_report(
            submission_request, tnsrobot, source, reporters, photometry, session
        )

        submission_request.payload = json.dumps(report)

        # SUBMIT THE REPORT TO TNS
        status, submission_id, serialized_response = send_at_report(
            submission_request, tnsrobot, report, tns_headers
        )

        submission_request.status = status
        submission_request.submission_id = submission_id
        submission_request.response = serialized_response
        session.commit()

    except TNSReportError as e:
        log(str(e))
        submission_request.status = f'error: {str(e)}'
        session.commit()
        try:
            flow = Flow()
            flow.push(
                user_id=submission_request.user_id,
                action_type='baselayer/SHOW_NOTIFICATION',
                payload={
                    'note': f"Error submitting {submission_request.obj_id} to TNS: {str(e)}",
                    'type': 'error' if 'already posted' not in str(e) else 'warning',
                },
            )
        except Exception:
            pass


@check_loaded(logger=log)
def service(*args, **kwargs):
    """Service to submit AT reports for sources to TNS, processing the TNSRobotSubmission table."""
    while True:
        with DBSession() as session:
            try:
                submission_request = session.scalar(
                    sa.select(TNSRobotSubmission)
                    .where(TNSRobotSubmission.status.in_(['pending', 'processing']))
                    .order_by(TNSRobotSubmission.created_at.asc())
                )
                if submission_request is None:
                    time.sleep(5)
                    continue
                else:
                    submission_request.status = 'processing'
                    session.commit()
            except Exception as e:
                log(f"Error getting TNS submission request: {str(e)}")
                continue

            submission_request_id = submission_request.id

            try:
                process_submission_request(submission_request, session)
            except Exception as e:
                try:
                    session.rollback()
                except Exception as e:
                    log(f"Error rolling back session: {str(e)}")
                else:
                    try:
                        log(
                            f"Error processing TNS request {submission_request_id}: {str(e)}"
                        )
                        submission_request = session.scalar(
                            sa.select(TNSRobotSubmission).where(
                                TNSRobotSubmission.id == submission_request_id
                            )
                        )
                        submission_request.status = f'error: {str(e)}'
                        session.commit()
                    except Exception as e:
                        log(f"Error updating TNS request status: {str(e)}")


if __name__ == "__main__":
    try:
        service()
    except Exception as e:
        log(f"Error starting TNS submission queue: {str(e)}")
        raise e
