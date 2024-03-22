import json
import re
import time
import urllib
import traceback

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
from skyportal.handlers.api.tns import (
    validate_photometry_options as _validate_photometry_options,
)
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
    TNS_SOURCE_GROUP_NAMING_CONVENTIONS,
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
search_frontend_url = urllib.parse.urljoin(TNS_URL, 'search')


# we create a custom exception to be able to catch it and log the error message
# useful to make the difference between unexpected errors and errors that we expect
# and want to set as the status of the TNSRobotSubmission + notify the user
class TNSReportError(Exception):
    pass


def validate_photometry_options(submission_request, tnsrobot):
    """Validate the photometry options for a TNSRobot.

    Parameters
    ----------
    submission_request : `~skyportal.models.TNSRobotSubmission`
        The submission request's photometry options to validate.
    tns_robot : `~skyportal.models.TNSRobot`
        The TNSRobot to validate the photometry options for.

    Returns
    -------
    dict
        The validated photometry options.

    Raises
    ------
    TNSReportError
        If the photometry options are not valid.
    """
    try:
        return _validate_photometry_options(
            getattr(submission_request, 'photometry_options', {}),
            getattr(tnsrobot, 'photometry_options', {}),
        )
    except ValueError as e:
        raise TNSReportError(str(e))


def validate_obj_id(obj_id, tns_source_group_id):
    """Validate that the object ID is valid for submission to TNS with the given TNS source group ID.

    Parameters
    ----------
    obj_id : str
        The object ID to validate.
    tns_source_group_id : int
        The TNS source group ID to validate the object ID for.

    Raises
    ------
    TNSReportError
        If the object ID is not valid for submission to TNS with the given TNS source group ID.
    """
    if tns_source_group_id not in TNS_SOURCE_GROUP_NAMING_CONVENTIONS:
        raise TNSReportError(
            f'Unknown naming convention for TNS source group ID {tns_source_group_id}, cannot validate object ID.'
        )
    regex_pattern = TNS_SOURCE_GROUP_NAMING_CONVENTIONS[tns_source_group_id]
    if not re.match(regex_pattern, obj_id):
        raise TNSReportError(
            f"Object ID {obj_id} does not match the expected naming convention for TNS source group ID {tns_source_group_id}."
        )


def find_accessible_tnsrobot_groups(submission_request, tnsrobot, user, session):
    """Find the TNSRobotGroups that the user is allowed to submit from.

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
    warning : str
        Any warning (e.g., if the original source saver had no affiliation and was ignored).
    """
    warning = None

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
            # verify that this user has an affiliation
            source_saver = session.scalar(
                sa.select(User).where(User.id == source.saved_by_id)
            )
            if len(source_saver.affiliations) == 0:
                warning = f'original source saver {source_saver.username} had no affiliation, ignored as the first author.'
            else:
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

        # if any of the users are missing first/last names, we don't submit
        authors_with_missing_names = [
            author
            for author in authors
            if author.first_name in [None, ""] or author.last_name in [None, ""]
        ]
        if len(authors_with_missing_names) > 0:
            raise TNSReportError(
                f'One or more authors are missing a first or last name: {", ".join([author.username for author in authors_with_missing_names])}, cannot report {obj_id} to TNS.'
            )
        # if any of the users are missing an affiliation, we don't submit
        authors_with_missing_affiliations = [
            author
            for author in authors
            if len(author.affiliations) == 0
            or all([affiliation in [None, ""] for affiliation in author.affiliations])
        ]
        if len(authors_with_missing_affiliations) > 0:
            raise TNSReportError(
                f'One or more authors are missing an affiliation: {", ".join([author.username for author in authors_with_missing_affiliations])}, cannot report {obj_id} to TNS.'
            )

        reporters = []
        for author in authors:
            # filter out empty affiliations
            affiliations = [
                affiliation
                for affiliation in author.affiliations
                if affiliation not in [None, ""]
            ]
            # we already verified that there is at least one affiliation earlier, so no need to check here
            #
            # capitalize the first letter of each affiliation
            affiliations = [
                affiliation[0].upper() + affiliation[1:]
                if len(affiliation) > 1
                else affiliation[0].upper()
                for affiliation in affiliations
            ]

            # sort alphabetically (A -> Z) to ensure consistent ordering
            affiliations = sorted(affiliations)

            affiliations = ", ".join(affiliations)
            reporters.append(f'{author.first_name} {author.last_name} ({affiliations})')

        reporters = ", ".join(reporters)

        # acknowledgments are added to the end of the reporters string if they exist (optional)
        if tnsrobot.acknowledgments not in [None, ""]:
            reporters += f' {str(tnsrobot.acknowledgments).strip()}'

        reporters = reporters.strip()

    return reporters, warning


def find_accessible_instrument_ids(submission_request, tnsrobot, user, session):
    """Find the instrument IDs to use when querying for photometry to submit to TNS.

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

    # when it comes to instruments, we only want to submit photometry for instruments that
    # the TNSRobot has access to, so we only consider instruments from the submission that
    # are a subset of the TNSRobot's instruments
    instrument_ids = [instrument.id for instrument in tnsrobot.instruments]
    if len(instrument_ids) == 0:
        raise TNSReportError(
            f'Must specify instruments for TNSRobot {tnsrobot_id} to submit sources to TNS.'
        )

    if (
        submission_request.instrument_ids is not None
        and len(submission_request.instrument_ids) > 0
    ):
        # union with the robot's instrument_ids
        instrument_ids = list(
            set(submission_request.instrument_ids) & set(instrument_ids)
        )
        if len(instrument_ids) == 0:
            raise TNSReportError(
                f'None of the instruments specified for the submission request are accessible to TNSRobot {tnsrobot_id}.'
            )

    # fetch the full list of instruments in the database that we have TNS IDs for
    tns_instruments = session.scalars(
        Instrument.select(user).where(
            sa.func.lower(Instrument.name).in_(list(TNS_INSTRUMENT_IDS.keys()))
        )
    ).all()
    if len(tns_instruments) == 0:
        raise TNSReportError(
            'No instrument with known TNS IDs available or accessible to this user.'
        )

    # keep the instruments from all_tns_instruments that are in the list of instruments to use for this submission
    tns_instruments = [
        instrument for instrument in tns_instruments if instrument.id in instrument_ids
    ]
    if len(tns_instruments) == 0:
        raise TNSReportError(
            f"None of the instrument(s) for submission {submission_request.id} with TNS robot {tnsrobot.id} have known TNS IDs."
        )

    return [instrument.id for instrument in tns_instruments]


def find_accessible_stream_ids(submission_request, tnsrobot, user, session):
    """Find the stream IDs to use when querying for photometry to submit to TNS.

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

    # compared to the instruments, we do allow overwriting the TNSRobot's streams
    # so here, if no streams are specified for the submission, we use all of the TNSRobot's streams
    # otherwise, we only use the streams specified in the submission
    #
    # streams are also optional except for auto-submissions
    stream_ids = [stream.id for stream in tnsrobot.streams]

    # if it is an auto_submission, we require streams to be specified for the TNSRobot
    if len(stream_ids) == 0 and submission_request.auto_submission is True:
        raise TNSReportError(
            f'Must specify streams for TNSRobot {tnsrobot_id} when to automatically submit sources to TNS.'
        )

    if (
        submission_request.stream_ids is not None
        and len(submission_request.stream_ids) > 0
    ):
        stream_ids = submission_request.stream_ids

    # specifying streams to use being optional, we return None if no streams are specified
    if len(stream_ids) == 0:
        return None
    else:
        # verify that the streams are accessible to the user that is submitting the request
        # use the intersection of the stream_ids and the user's accessible streams
        all_streams = session.scalars(Stream.select(user)).all()
        all_streams = [stream for stream in all_streams if stream.id in stream_ids]
        if len(all_streams) == 0:
            raise TNSReportError(
                f'No streams specified for submission {submission_request.id} with TNS robot {tnsrobot_id} are accessible to this user'
            )

        return [stream.id for stream in all_streams]


def build_at_report(
    submission_request,
    tnsrobot,
    source,
    reporters,
    photometry,
    photometry_options,
    session,
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
        raise TNSReportError(
            f'Need at least one detection to report with TNS robot {tnsrobot.id}.'
        )

    # if we require both first and last detections, we need at least two detections
    if photometry_options['first_and_last_detections'] is True and len(detections) < 2:
        raise TNSReportError(
            f'TNS robot {tnsrobot.id} requires both first and last detections, but only one detection is available.'
        )

    # if we require a last detection and it's not an archival submission, we need at least one non-detection
    if len(non_detections) == 0 and not archival:
        raise TNSReportError(
            f'TNS robot {tnsrobot.id} cannot send a non-archival report to TNS without any non-detections before the first detection.'
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

    # if we require a last detection and it's not an archival submission, we need at least one non-detection
    if len(non_detections) == 0 and not archival:
        raise TNSReportError(
            f'TNS robot {tnsrobot.id} cannot send a non-archival report to TNS without any non-detections before the first detection.'
        )

    # we already filtered the non detections to only those that are before the first detection
    # so we can just take the last one since they are sorted by mjd
    if not archival:
        time_last_nondetection = non_detections[-1]['mjd']
        limmag_last_nondetection = non_detections[-1]['limiting_mag']
        filt_last_nondetection = SNCOSMO_TO_TNSFILTER[non_detections[-1]['filter']]
        instrument_last_nondetection = TNS_INSTRUMENT_IDS[
            non_detections[-1]['instrument_name'].lower()
        ]

        non_detection = {
            "obsdate": astropy.time.Time(time_last_nondetection, format='mjd').jd,
            "limiting_flux": limmag_last_nondetection,
            "flux_units": "1",
            "filter_value": filt_last_nondetection,
            "instrument_value": instrument_last_nondetection,
        }
    else:
        non_detection = {
            "archiveid": "0",
            "archival_remarks": archival_comment,
        }

    phot_first = None
    phot_last = None
    # if we have both first and last detections, we can submit them
    if len(detections) > 1:
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
    # else we only submit one (the first detection)
    else:
        phot_first = {
            "obsdate": astropy.time.Time(time_first, format='mjd').jd,
            "flux": mag_first,
            "flux_err": magerr_first,
            "flux_units": "1",
            "filter_value": filt_first,
            "instrument_value": instrument_first,
        }

    proprietary_period = {
        "proprietary_period_value": 0,
        "proprietary_period_units": "years",
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

    # pop out the last detection if it is None
    if phot_last is None:
        at_report['photometry']['photometry_group'].pop('1')

    return {"at_report": {"0": at_report}}


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
    warning = None

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

        photometry_options = validate_photometry_options(submission_request, tnsrobot)

        validate_obj_id(obj_id, tnsrobot.source_group_id)

        apply_existing_tnsreport_rules(
            tns_headers, tnsrobot, submission_request, session
        )

        source = find_source_to_submit(submission_request, tnsrobot_groups, session)

        reporters, warning = build_reporters_string(
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

        # FETCH THE PHOTOMETRY (FILTERED BY INSTRUMENTS, NO FP)
        photometry = session.scalars(
            Photometry.select(user).where(
                Photometry.obj_id == obj_id,
                Photometry.instrument_id.in_(instrument_ids),
                # make sure that the origin does not contain 'fp' (for forced photometry)
                ~Photometry.origin.ilike('%fp%'),
            )
        ).all()

        if len(photometry) == 0:
            raise TNSReportError(
                f'No photometry available for {obj_id} with instruments {instrument_ids}.'
            )

        # FILTER THE PHOTOMETRY BY STREAMS
        if stream_ids is not None and len(stream_ids) > 0:
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
            submission_request,
            tnsrobot,
            source,
            reporters,
            photometry,
            photometry_options,
            session,
        )

        submission_request.payload = json.dumps(report)

        # SUBMIT THE REPORT TO TNS
        status, submission_id, serialized_response = send_at_report(
            submission_request, tnsrobot, report, tns_headers
        )
        if status in [
            'submitted',
            'testing mode, not submitted to TNS',
        ] and warning not in [None, ""]:
            status = f'{status} (warning: {warning})'
        submission_request.status = status
        submission_request.submission_id = submission_id
        submission_request.response = serialized_response
        session.commit()

        # if the submission was successful, send a notification
        if status in ['submitted', 'testing mode, not submitted to TNS']:
            note = f"Successfully submitted {submission_request.obj_id} to TNS."
            if status == 'testing mode, not submitted to TNS':
                note = f"Successfully created report for {submission_request.obj_id} (testing mode, not sent to TNS)."
            if warning not in [None, ""]:
                note += f'\nWarning: {warning}'
            try:
                flow = Flow()
                flow.push(
                    user_id=submission_request.user_id,
                    action_type='baselayer/SHOW_NOTIFICATION',
                    payload={
                        'note': note,
                        'type': 'info',
                    },
                )
            except Exception:
                pass

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
                        traceback.print_exc()
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
