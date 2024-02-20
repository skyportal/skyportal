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

# from baselayer.app.flow import Flow
from skyportal.handlers.api.photometry import serialize
from skyportal.models import (
    DBSession,
    Instrument,
    Photometry,
    TNSRobot,
    TNSRobotSubmission,
    TNSRobotCoAuthor,
    TNSRobotGroup,
    User,
    Source,
)
from skyportal.utils.tns import (
    SNCOSMO_TO_TNSFILTER,
    TNS_INSTRUMENT_IDS,
    get_IAUname,
)
from skyportal.utils.services import check_loaded

env, cfg = load_env()
log = make_log('tns_queue')

init_db(**cfg['database'])

Session = scoped_session(sessionmaker())

TNS_URL = cfg['app.tns.endpoint']
report_url = urllib.parse.urljoin(TNS_URL, 'api/bulk-report')
search_frontend_url = urllib.parse.urljoin(TNS_URL, 'search')


@check_loaded(logger=log)
def service(*args, **kwargs):
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
                    error_msg = f'No user found with ID {user_id}.'
                    log(error_msg)
                    submission_request.status = f'error: {error_msg}'
                    session.commit()
                    continue

                tns_robot = session.scalar(
                    sa.select(TNSRobot).where(TNSRobot.id == tnsrobot_id)
                )
                if tns_robot is None:
                    error_msg = f'No TNSRobot found with ID {tnsrobot_id}.'
                    log(error_msg)
                    submission_request.status = f'error: {error_msg}'
                    session.commit()
                    continue

                altdata = tns_robot.altdata
                if not altdata or 'api_key' not in altdata:
                    error_msg = f'No TNS API key found for TNSRobot {tnsrobot_id}.'
                    log(error_msg)
                    submission_request.status = f'error: {error_msg}'
                    session.commit()
                    continue

                tns_headers = {
                    'User-Agent': f'tns_marker{{"tns_id":{tns_robot.bot_id},"type":"bot", "name":"{tns_robot.bot_name}"}}'
                }

                _, existing_tns_name = get_IAUname(
                    altdata['api_key'], tns_headers, obj_id=obj_id
                )
                if existing_tns_name is not None:
                    error_msg = (
                        f'{obj_id} already posted to TNS as {existing_tns_name}.'
                    )
                    log(error_msg)
                    submission_request.status = f'skipped: {error_msg}'
                    session.commit()
                    continue

                # we look for the first group that has the robot, set to auto-report,
                # and that this object was first saved to as a source
                tnsrobot_group = session.scalar(
                    sa.select(TNSRobotGroup)
                    .join(Source, Source.group_id == TNSRobotGroup.group_id)
                    .where(TNSRobotGroup.tnsrobot_id == tnsrobot_id)
                    .where(TNSRobotGroup.auto_report.is_(True))
                    .where(Source.active.is_(True))
                    .order_by(Source.created_at.asc())
                    .limit(1)
                )
                if tnsrobot_group is None:
                    error_msg = f'No group with TNSRobot {tnsrobot_id} set to auto-report and with {obj_id} saved to it.'
                    log(error_msg)
                    submission_request.status = f'error: {error_msg}'
                    session.commit()
                    continue
                source = session.scalar(
                    sa.select(Source).where(
                        Source.obj_id == obj_id,
                        Source.active.is_(True),
                        Source.group_id == tnsrobot_group.group_id,
                    )
                )
                if source is None:
                    error_msg = (
                        f'No source {obj_id} saved to group {tnsrobot_group.group_id}.'
                    )
                    log(error_msg)
                    submission_request.status = f'error: {error_msg}'
                    session.commit()
                    continue

                if submission_request.custom_reporting_string not in [None, ""]:
                    reporters = submission_request.custom_reporting_string
                else:
                    # unless a specific reporting string is provided for this request
                    # we find which user saved the obj to that group and use their name
                    # and first affiliations as main author of the report
                    # if the user that first saved the obj to a group of that tnsrobot is not
                    # the same user that is submitting the report, we add the user that is submitting
                    # as the second author
                    author_ids = []
                    author_ids.append(source.saved_by_id)
                    if source.saved_by_id != user_id:
                        author_ids.append(user_id)
                    coauthor_ids = [
                        coauthor.user_id
                        for coauthor in session.scalars(
                            sa.select(TNSRobotCoAuthor).where(
                                TNSRobotCoAuthor.tnsrobot_id == tnsrobot_id
                            )
                        )
                    ]
                    author_ids = list(set(author_ids + coauthor_ids))
                    authors = (
                        session.scalars(sa.select(User).where(User.id.in_(author_ids)))
                        .unique()
                        .all()
                    )
                    if len(authors) == 0:
                        error_msg = f'No authors found for tnsrobot {tnsrobot_id} and source {obj_id}, cannot report to TNS.'
                        log(error_msg)
                        submission_request.status = f'error: {error_msg}'
                        session.commit()
                        continue
                    # if any of the users are missing an affiliation, we don't submit
                    if any([len(author.affiliations) == 0 for author in authors]):
                        error_msg = f'One or more authors are missing an affiliation, cannot report {obj_id} to TNS.'
                        log(error_msg)
                        submission_request.status = f'error: {error_msg}'
                        session.commit()
                        continue
                    reporters = ', '.join(
                        [
                            f'{author.first_name} {author.last_name} ({author.affiliations[0]})'
                            for author in authors
                        ]
                    )
                    if tns_robot.acknowledgments in [None, ""]:
                        error_msg = f'No acknowledgments found for tnsrobot {tnsrobot_id}, cannot report {obj_id} to TNS.'
                        log(error_msg)
                        submission_request.status = f'error: {error_msg}'
                        session.commit()
                        continue
                    reporters += f' {tns_robot.acknowledgments}'

                archival = submission_request.archival
                archival_comment = submission_request.archival_comment
                if archival and (archival_comment in [None, ""]):
                    error_msg = f'Archival submission requested for {obj_id} but no archival_comment provided.'
                    log(error_msg)
                    submission_request.status = f'error: {error_msg}'
                    session.commit()
                    continue

                # for now we limit it to instruments and filters we have mapped to TNS
                all_tns_instruments = session.scalars(
                    Instrument.select(user).where(
                        sa.func.lower(Instrument.name).in_(
                            list(TNS_INSTRUMENT_IDS.keys())
                        )
                    )
                ).all()
                if len(all_tns_instruments) == 0:
                    raise ValueError(
                        'No instrument with known TNS IDs available or accessible to this user.'
                    )

                instrument_ids = [
                    instrument.id for instrument in tns_robot.auto_report_instruments
                ]  # noqa: E841
                stream_ids = [
                    stream.id for stream in tns_robot.auto_report_streams
                ]  # noqa: E841

                # keep the instruments from all_tns_instruments that are in the list of instruments this robot is set to auto-report
                # unless no instruments are set to auto-report, in which case we use all instruments
                if len(instrument_ids) > 0:
                    all_tns_instruments = [
                        instrument
                        for instrument in all_tns_instruments
                        if instrument.id in instrument_ids
                    ]
                    if len(all_tns_instruments) == 0:
                        error_msg = f'No instruments set to auto-report for TNSRobot {tnsrobot_id} have known TNS IDs.'
                        log(error_msg)
                        submission_request.status = f'error: {error_msg}'
                        session.commit()
                        continue

                # keep the intersection between the streams that this tns group is set to auto-report and the streams that this group has access to
                all_streams = tnsrobot_group.group.streams

                if len(stream_ids) > 0:
                    all_streams = [
                        stream for stream in all_streams if stream.id in stream_ids
                    ]
                    if len(all_streams) == 0:
                        error_msg = f'No streams set to auto-report for TNSRobot {tnsrobot_id} are accessible to group {tnsrobot_group.group_id}.'
                        log(error_msg)
                        submission_request.status = f'error: {error_msg}'
                        session.commit()
                        continue

                # FETCH THE PHOTOMETRY
                instrument_ids = [instrument.id for instrument in all_tns_instruments]
                photometry = session.scalars(
                    Photometry.select(user).where(
                        Photometry.obj_id == obj_id,
                        Photometry.instrument_id.in_(instrument_ids),
                    )
                ).all()

                if len(photometry) == 0:
                    error_msg = f'No photometry available for {obj_id} with instruments {instrument_ids}.'
                    log(error_msg)
                    submission_request.status = f'error: {error_msg}'
                    session.commit()
                    continue

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
                        error_msg = f'No photometry with streams {stream_ids} available for {obj_id}.'
                        log(error_msg)
                        submission_request.status = f'error: {error_msg}'
                        session.commit()
                        continue
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
                    error_msg = (
                        f'Need at least one detection for TNS report of {obj_id}.'
                    )
                    log(error_msg)
                    submission_request.status = f'error: {error_msg}'
                    session.commit()
                    continue

                if len(non_detections) == 0 and not archival:
                    error_msg = f'Need at least one non-detection for non-archival TNS report of {obj_id}.'
                    log(error_msg)
                    submission_request.status = f'error: {error_msg}'
                    session.commit()
                    continue

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
                    error_msg = f'No non-detections found before first detection, cannot submit {obj_id} to TNS.'
                    log(error_msg)
                    submission_request.status = f'error: {error_msg}'
                    session.commit()
                    continue

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

                # DEBUG ONLY, PRINTING REQUEST
                log(
                    f"DEBUG: TNS request data for obj {obj_id} and TNSRobot {tnsrobot_id}:"
                )
                log(str(data))

                # DEBUG ONLY, PRINTING URL
                log(f"\nDEBUG: TNS URL for obj {obj_id} and TNSRobot {tnsrobot_id}:")
                log(str(report_url))

                # DEBUG ONLY, NOT SENDING
                status_code = 0
                n_retries = 0
                status = None
                submission_id = None
                while (
                    n_retries < 6
                ):  # 6 * 10 seconds = 1 minute, which is when the TNS API limit resets
                    r = requests.post(report_url, headers=tns_headers, data=data)
                    status_code = r.status_code
                    # DEBUG ONLY, PRINTING STATUS CODE
                    log(
                        f"DEBUG: TNS status code for obj {obj_id} and TNSRobot {tnsrobot_id}:"
                    )
                    log(str(status_code))
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
                    else:
                        status = f"Failed to submit {obj_id} to TNS with TNSRobot {tnsrobot_id}: {r.content}"
                    break

                if status_code == 429:
                    error_msg = f"{error_msg}, and exceeded number of retries (6)"
                submission_request.status = (
                    f'error: {status}' if status_code != 200 else status
                )
                if submission_id is not None:
                    submission_request.submission_id = submission_id

                session.commit()

                # DEBUG ONLY, PRINTING RESPONSE
                log(
                    f"\nDEBUG: TNS response for obj {obj_id} and TNSRobot {tnsrobot_id}:"
                )
                log(str(r.content))
            except Exception as e:
                try:
                    session.rollback()
                except Exception as e:
                    log(f"Error rolling back session: {str(e)}")
                finally:
                    try:
                        log(
                            f"Error processing TNS request for object {obj_id} and TNSRobot {tnsrobot_id}: {str(e)}"
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
                    finally:
                        continue


if __name__ == "__main__":
    try:
        service()
    except Exception as e:
        log(f"Error starting TNS submission queue: {str(e)}")
        raise e
