import json
import time
import urllib

import astropy
import requests
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
search_frontend_url = urllib.parse.urljoin(TNS_URL, 'search')


# we create a custom exception to be able to catch it and log the error message
# useful to make the difference between unexpected errors and errors that we expect
# and want to set as the status of the TNSRobotSubmission + notify the user
class TNSReportError(Exception):
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
                obj_id = submission_request.obj_id
                tnsrobot_id = submission_request.tnsrobot_id
                user_id = submission_request.user_id

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
                    raise TNSReportError(
                        f'No TNS API key found for TNSRobot {tnsrobot_id}.'
                    )

                # verify that the user is allowed to submit to TNS with this robot
                # for that, verify that there is a TNSRobotGroup which group_id is in the list of groups the user has access to
                tnsrobot_groups = tnsrobot.groups
                user_accessible_group_ids = [
                    group.id for group in user.accessible_groups
                ]
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
                                TNSRobotGroupAutoreporter.tnsrobot_group_id
                                == tnsrobot_group.id,
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

                    # we use the first remaining auto-report group to submit the object
                    tnsrobot_group = tnsrobot_groups_with_autoreport[0]
                else:
                    # we use the first remaining group to submit the object
                    tnsrobot_group = tnsrobot_groups[0]

                tns_headers = {
                    'User-Agent': f'tns_marker{{"tns_id":{tnsrobot.bot_id},"type":"bot", "name":"{tnsrobot.bot_name}"}}'
                }

                # if the bot is set up to only report objects to TNS if they are not already there,
                # we check if an object is already on TNS (within 2 arcsec of the object's position)
                # and if it is, we skip the submission
                # otherwise, we submit as long as there are no reports with the same internal source name
                # (i.e. the same obj_id from the same survey)
                _, existing_tns_name = get_IAUname(
                    altdata['api_key'], tns_headers, obj_id=obj_id
                )
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

                # Get the sources saved to the groups that have access to this TNS robot,
                # this is so if a user that has access to this robot saved the obj as a source before,
                # he is the first author when another user auto-submits the source
                source = session.scalar(
                    sa.select(Source)
                    .where(
                        Source.obj_id == obj_id,
                        Source.active.is_(True),
                        Source.group_id.in_(
                            [
                                tnsrobot_group.group_id
                                for tnsrobot_group in tnsrobot_groups
                            ]
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
                    authors = sorted(
                        authors, key=lambda author: author_ids.index(author.id)
                    )

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
                    submission_request.custom_reporting_string = reporters

                archival = submission_request.archival
                archival_comment = submission_request.archival_comment
                if archival and (archival_comment in [None, ""]):
                    raise TNSReportError(
                        f'Archival submission requested for {obj_id} but no archival_comment provided.'
                    )

                # for now we limit it to instruments and filters we have mapped to TNS
                all_tns_instruments = session.scalars(
                    Instrument.select(user).where(
                        sa.func.lower(Instrument.name).in_(
                            list(TNS_INSTRUMENT_IDS.keys())
                        )
                    )
                ).all()
                if len(all_tns_instruments) == 0:
                    raise TNSReportError(
                        'No instrument with known TNS IDs available or accessible to this user.'
                    )

                instrument_ids = [
                    instrument.id for instrument in tnsrobot.instruments
                ]  # noqa: E841
                stream_ids = [stream.id for stream in tnsrobot.streams]  # noqa: E841

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
                            f'No instruments specified for TNSRobot {tnsrobot_id} are accessible to group {tnsrobot_group.group_id}.'
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
                            f'No instruments specified for submission with TNSRobot {tnsrobot_id} are accessible to group {tnsrobot_group.group_id}.'
                        )

                # keep the intersection between the streams that this tns robot has access to (if specified) and the streams that this group has access to
                all_streams = tnsrobot.streams

                if len(stream_ids) > 0:
                    all_streams = [
                        stream for stream in all_streams if stream.id in stream_ids
                    ]
                    if len(all_streams) == 0:
                        raise TNSReportError(
                            f'No streams specified for TNSRobot {tnsrobot_id} are accessible to group {tnsrobot_group.group_id}.'
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
                            f'No streams specified for submission with TNSRobot {tnsrobot_id} are accessible to group {tnsrobot_group.group_id}.'
                        )

                # FETCH THE PHOTOMETRY
                instrument_ids = [instrument.id for instrument in all_tns_instruments]
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
                # we keep the photometry that is attached to no streams or to at least one of the streams that are in the list of all_streams
                stream_ids = [stream.id for stream in all_streams]
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
                        f'Need at least one detection for TNS report of {obj_id}.'
                    )

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
                instrument_first = TNS_INSTRUMENT_IDS[
                    detections[0]['instrument_name'].lower()
                ]

                time_last = detections[-1]['mjd']
                mag_last = detections[-1]['mag']
                magerr_last = detections[-1]['magerr']
                filt_last = SNCOSMO_TO_TNSFILTER[detections[-1]['filter']]
                instrument_last = TNS_INSTRUMENT_IDS[
                    detections[-1]['instrument_name'].lower()
                ]

                # remove non detections that are after the first detection
                non_detections = [
                    phot for phot in non_detections if phot['mjd'] < time_first
                ]

                if not archival and len(non_detections) == 0:
                    raise TNSReportError(
                        f'No non-detections found before first detection for TNS report of {obj_id}.'
                    )

                # we already filtered the non detections to only those that are before the first detection
                # so we can just take the last one
                if not archival:
                    time_last_nondetection = non_detections[-1]['mjd']
                    limmag_last_nondetection = non_detections[-1]['limiting_mag']
                    filt_last_nondetection = SNCOSMO_TO_TNSFILTER[
                        non_detections[-1]['filter']
                    ]
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
                        "obsdate": astropy.time.Time(
                            time_last_nondetection, format='mjd'
                        ).jd,
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
                    "groupid": tnsrobot_group.group_id,
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
                    "proprietary_period_groups": [tnsrobot_group.group_id],
                    "proprietary_period": proprietary_period,
                    "non_detection": non_detection,
                    "photometry": {
                        "photometry_group": {"0": phot_first, "1": phot_last}
                    },
                }

                report = {"at_report": {"0": at_report}}

                data = {
                    'api_key': altdata['api_key'],
                    'data': json.dumps(report),
                }

                if not tnsrobot.testing:
                    status_code = 0
                    n_retries = 0
                    status = None
                    submission_id = None
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
                    submission_request.status = (
                        f'error: {status}' if status_code != 200 else status
                    )
                    if submission_id is not None:
                        submission_request.submission_id = submission_id

                    if isinstance(r, requests.models.Response):
                        # we store the request's payload and TNS response in the database for bookkeeping and debugging
                        submission_request.payload = data['data']
                        submission_request.response = serialize_requests_response(r)

                else:
                    log(
                        f"TNS Robot {tnsrobot_id} is in testing mode, not submitting {obj_id} to TNS."
                    )
                    # we store the payload in the database for bookkeeping and debugging
                    submission_request.payload = data['data']
                    submission_request.status = 'testing mode, not submitted to TNS'

                session.commit()

            except Exception as e:
                if isinstance(e, TNSReportError):
                    # these errors are expected, we log, set the status, commit, and continue
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
                                'type': 'error',
                            },
                        )
                    except Exception:
                        pass
                else:
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
