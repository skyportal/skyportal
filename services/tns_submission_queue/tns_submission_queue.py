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
    Obj,
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

env, cfg = load_env()
log = make_log('tns_queue')

init_db(**cfg['database'])

Session = scoped_session(sessionmaker())

TNS_URL = cfg['app.tns.endpoint']
report_url = urllib.parse.urljoin(TNS_URL, 'api/bulk-report')
search_frontend_url = urllib.parse.urljoin(TNS_URL, 'search')


def tns_submission(
    obj_ids,
    tnsrobot_id,
    user_id,
    reporters="",
    archival=False,
    archival_comment="",
    instrument_ids=[],
    stream_ids=[],
    parent_session=None,
):
    """Submit objects to TNS.
    obj_ids : List[str]
        Object IDs
    tnsrobot_id : int
        TNSRobot ID
    user_id : int
        SkyPortal ID of User posting to TNS
    reporters : str
        Reporters to appear on TNS submission.
    archival : boolean
        Reporting the source as an archival source (i.e. no upperlimit).
    archival_comment : str
        Comment on archival source. Required if archival is True.
    instrument_ids : List[int]
        Instrument IDs to restrict photometry to.
    stream_ids : List[int]
        Stream IDs to restrict photometry to.
    parent_session : `sqlalchemy.orm.session.Session`
        Database session.
    """
    print(instrument_ids)
    print(stream_ids)

    if parent_session is None:
        if Session.registry.has():
            session = Session()
        else:
            session = Session(bind=DBSession.session_factory.kw["bind"])
    else:
        session = parent_session

    user = session.scalar(sa.select(User).where(User.id == user_id))

    flow = Flow()

    try:
        # for now we limit it to instruments and filters we have mapped to TNS
        instruments = session.scalars(
            Instrument.select(user).where(
                sa.func.lower(Instrument.name).in_(list(TNS_INSTRUMENT_IDS.keys()))
            )
        ).all()
        if len(instruments) == 0:
            raise ValueError('No instrument with known IDs available.')

        tnsrobot = session.scalars(
            TNSRobot.select(user).where(TNSRobot.id == tnsrobot_id)
        ).first()
        if tnsrobot is None:
            raise ValueError(f'No TNSRobot available with ID {tnsrobot_id}')

        altdata = tnsrobot.altdata
        if not altdata:
            raise ValueError('Missing TNS information.')
        if 'api_key' not in altdata:
            raise ValueError('Missing TNS API key.')

        if archival is True:
            if len(archival_comment) == 0:
                raise ValueError(
                    'If source flagged as archival, archival_comment is required'
                )

        tns_headers = {
            'User-Agent': f'tns_marker{{"tns_id":{tnsrobot.bot_id},"type":"bot", "name":"{tnsrobot.bot_name}"}}'
        }

        if len(instrument_ids) > 0 and not set(instrument_ids).issubset(
            {instrument.id for instrument in instruments}
        ):
            log(
                f'Not all instrument IDs {instrument_ids} are available for TNS submission.'
            )
            flow.push(
                user_id=user_id,
                action_type="baselayer/SHOW_NOTIFICATION",
                payload={
                    "note": f'Not all instrument IDs {instrument_ids} are available for TNS submission.',
                    "type": "warning",
                },
            )
            return

        for obj_id in obj_ids:
            obj = session.scalars(Obj.select(user).where(Obj.id == obj_id)).first()
            if obj is None:
                log(f'No object available with ID {obj_id}')
                continue

            if len(instrument_ids) == 0:
                photometry = session.scalars(
                    Photometry.select(user).where(
                        Photometry.obj_id == obj_id,
                        Photometry.instrument_id.in_(
                            [instrument.id for instrument in instruments]
                        ),
                    )
                ).all()
            else:
                photometry = session.scalars(
                    Photometry.select(user).where(
                        Photometry.obj_id == obj_id,
                        Photometry.instrument_id.in_(instrument_ids),
                    )
                ).all()

            if len(photometry) == 0:
                log(
                    f'No photometry that can be submitted to TNS is available for {obj_id}.'
                )
                flow.push(
                    user_id=user_id,
                    action_type="baselayer/SHOW_NOTIFICATION",
                    payload={
                        "note": f'No photometry that can be submitted to TNS is available for {obj_id}.',
                        "type": "warning",
                    },
                )
                continue

            if len(stream_ids) > 0:
                phot_to_keep = []
                for phot in photometry:
                    for stream in phot.streams:
                        if stream.id in stream_ids:
                            phot_to_keep.append(phot)
                            break

                if len(phot_to_keep) == 0:
                    log(
                        f'No photometry with streams {stream_ids} that can be submitted to TNS is available for {obj_id}.'
                    )
                    flow.push(
                        user_id=user_id,
                        action_type="baselayer/SHOW_NOTIFICATION",
                        payload={
                            "note": f'No photometry with streams {stream_ids} that can be submitted to TNS is available for {obj_id}.',
                            "type": "warning",
                        },
                    )
                    continue

                photometry = phot_to_keep

            photometry = [serialize(phot, 'ab', 'mag') for phot in photometry]

            _, tns_name = get_IAUname(altdata['api_key'], tns_headers, obj_id=obj_id)
            if tns_name is not None:
                log(f'{obj_id} already posted to TNS as {tns_name}.')
                flow.push(
                    user_id=user_id,
                    action_type="baselayer/SHOW_NOTIFICATION",
                    payload={
                        "note": f'{obj_id} already posted to TNS as {tns_name}.',
                        "type": "warning",
                    },
                )
                continue

            time_first = mag_first = magerr_first = filt_first = instrument_first = None
            time_last = mag_last = magerr_last = filt_last = instrument_last = None
            time_last_nondetection = (
                limmag_last_nondetection
            ) = filt_last_nondetection = instrument_last_nondetection = None

            # split the photometry into detections and non-detections
            # non detections are those with mag=None
            detections, non_detections = [], []

            for phot in photometry:
                if phot['mag'] is None:
                    non_detections.append(phot)
                else:
                    detections.append(phot)

            if len(detections) == 0:
                log(f'Need at least one detection for TNS report of {obj_id}')
                flow.push(
                    user_id=user_id,
                    action_type="baselayer/SHOW_NOTIFICATION",
                    payload={
                        "note": f'Need at least one detection for TNS report of {obj_id}',
                        "type": "warning",
                    },
                )
                continue

            if len(non_detections) == 0 and not archival:
                log(
                    f'Need at least one non-detection for non-archival TNS report of {obj_id}'
                )
                flow.push(
                    user_id=user_id,
                    action_type="baselayer/SHOW_NOTIFICATION",
                    payload={
                        "note": f'Need at least one non-detection for non-archival TNS report of {obj_id}',
                        "type": "warning",
                    },
                )
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

            # find the the last non-detection that is before the first detection
            for phot in non_detections:
                if phot['mjd'] < time_first:
                    time_last_nondetection = phot['mjd']
                    limmag_last_nondetection = phot['limiting_mag']
                    filt_last_nondetection = SNCOSMO_TO_TNSFILTER[phot['filter']]
                    instrument_last_nondetection = TNS_INSTRUMENT_IDS[
                        phot['instrument_name'].lower()
                    ]

            if not archival:
                if time_last_nondetection is None:
                    log(
                        f'No non-detections found before first detection, cannot submit {obj_id} to TNS'
                    )
                    continue

            proprietary_period = {
                "proprietary_period_value": 0,
                "proprietary_period_units": "years",
            }
            if archival:
                non_detection = {"archiveid": "0", "archival_remarks": archival_comment}
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
                "ra": {"value": obj.ra},
                "dec": {"value": obj.dec},
                "groupid": tnsrobot.source_group_id,
                "internal_name_format": {
                    "prefix": instrument_first,
                    "year_format": "YY",
                    "postfix": "",
                },
                "internal_name": obj.id,
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

            data = {
                'api_key': altdata['api_key'],
                'data': json.dumps(report),
            }

            r = requests.post(report_url, headers=tns_headers, data=data)
            if r.status_code == 200:
                tns_id = r.json()['data']['report_id']
                log(f'Successfully submitted {obj_id} to TNS with request ID {tns_id}')
            else:
                log(f'Failed to submit {obj_id} to TNS: {r.content}')

    except Exception as e:
        log(f"Unable to generate TNS reports for {','.join(obj_ids)}: {e}")
    finally:
        if parent_session is None:
            session.close()
            Session.remove()


def service():
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

                tns_robot = session.scalar(
                    sa.select(TNSRobot).where(TNSRobot.id == tnsrobot_id)
                )

                # we look for the first group that has the robot, set to auto-report, and that first saved
                tnsrobot_group = session.scalar(
                    sa.select(TNSRobotGroup)
                    .join(Source, Source.group_id == TNSRobotGroup.group_id)
                    .where(TNSRobotGroup.tnsrobot_id == tnsrobot_id)
                    .where(TNSRobotGroup.auto_report.is_(True))
                    .where(Source.active.is_(True))
                    .order_by(Source.created_at.asc())
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

                instrument_ids = [
                    instrument.id for instrument in tns_robot.auto_report_instruments
                ] # noqa: E841
                stream_ids = [
                    stream.id for stream in tns_robot.auto_report_streams
                ] # noqa: E841

                # DEBUG ONLY, NOT ACTUALLY SUBMITTING TO TNS
                # tns_submission(
                #     [obj_id],
                #     tnsrobot_id,
                #     user_id,
                #     reporters=reporters,
                #     archival=archival,
                #     archival_comment=archival_comment,
                #     instrument_ids=instrument_ids,
                #     stream_ids=stream_ids,
                #     parent_session=session,
                # )
                submission_request.status = 'submitted'
                session.commit()
                log(
                    f'Successfully submitted {obj_id} to TNS using TNSRobot with bot_id {tns_robot.bot_id}'
                )
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
