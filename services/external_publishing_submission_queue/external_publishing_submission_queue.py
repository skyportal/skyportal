import datetime
import time
import traceback
import uuid
from threading import Thread

import requests
import sqlalchemy as sa
from sqlalchemy import and_, or_

from baselayer.app.env import load_env
from baselayer.app.flow import Flow
from baselayer.app.models import init_db, session_context_id
from baselayer.log import make_log
from skyportal.models import (
    DBSession,
    ExternalPublishingBot,
    ExternalPublishingBotCoauthor,
    ExternalPublishingSubmission,
    Obj,
    User,
)
from skyportal.utils.data_access import (
    get_publishable_source_and_photometry,
    validate_photometry_options,
)
from skyportal.utils.hermes_submission import submit_to_hermes
from skyportal.utils.services import check_loaded
from skyportal.utils.tns_submission import check_at_report, submit_to_tns

env, cfg = load_env()

init_db(**cfg["database"])

log = make_log("external_publishing_queue")

tns_retrieval_microservice_url = f"http://127.0.0.1:{cfg['ports.tns_retrieval_queue']}"


def build_reporters_and_remarks_string(
    submission_request, source, acknowledgments, session
):
    """Build the reporters string and remarks for external publishing.

    Parameters
    ----------
    submission_request : `~skyportal.models.ExternalPublishingSubmission`
        The submission request.
    source : `~skyportal.models.Source`
        The source to submit.
    acknowledgments : str or None
        The acknowledgments to include in the reporters string. (optional)
    session : `~sqlalchemy.orm.Session`
        The database session to use.

    Returns
    -------
    reporters : str
        The reporters string.
    remarks : str
        The remarks string.
    warning : str
        Any warning (e.g., if the original source saver had no affiliation and was ignored).
    """
    bot_id = submission_request.external_publishing_bot_id
    user_id = submission_request.user_id
    obj_id = submission_request.obj_id
    remarks = []
    warning = None

    if submission_request.custom_publishing_string:
        reporters = submission_request.custom_publishing_string
    else:
        author_ids = []

        # Add source saver as first author if valid and different from submitter
        if (
            submission_request.auto_submission
            and source.saved_by_id is not None
            and source.saved_by_id != user_id
        ):
            source_saver = session.scalar(
                sa.select(User).where(User.id == source.saved_by_id)
            )
            if not source_saver.affiliations:
                warning = f"original source saver {source_saver.username} had no affiliation, ignored as the first author."
            elif source_saver.is_bot and not (source_saver.bio or "").strip():
                warning = f"original source saver {source_saver.username} is a bot with no bio, ignored as the first author."
            else:
                author_ids.append(source.saved_by_id)
        author_ids.append(user_id)

        coauthor_ids = session.scalars(
            sa.select(ExternalPublishingBotCoauthor.user_id).where(
                ExternalPublishingBotCoauthor.external_publishing_bot_id == bot_id
            )
        ).all()
        author_ids += [uid for uid in coauthor_ids if uid not in author_ids]

        authors = (
            session.scalars(sa.select(User).where(User.id.in_(author_ids)))
            .unique()
            .all()
        )

        if not authors:
            raise ValueError(
                f"ExternalPublishingError: No authors found for publishing bot {bot_id} and source {obj_id}, cannot publish"
            )

        # Sort authors by appearance order
        authors.sort(key=lambda author: author_ids.index(author.id))

        missing_names = [
            a.username for a in authors if not a.first_name or not a.last_name
        ]
        if missing_names:
            raise ValueError(
                f"ExternalPublishingWarning: Missing first or last name: {', '.join(missing_names)}, cannot publish {obj_id}."
            )

        missing_affiliation = [a.username for a in authors if not any(a.affiliations)]
        if missing_affiliation:
            raise ValueError(
                f"ExternalPublishingWarning: Missing affiliation: {', '.join(missing_affiliation)}, cannot publish {obj_id}."
            )

        invalid_bio_bots = [
            a.username
            for a in authors
            if a.is_bot and not (10 <= len((a.bio or "").strip()) <= 1000)
        ]
        if invalid_bio_bots:
            raise ValueError(
                f"ExternalPublishingWarning: Invalid bio (missing, too short, or too long) for bot(s): {', '.join(invalid_bio_bots)}, cannot publish {obj_id}."
            )

        reporters = []
        for author in authors:
            affiliations = [
                a.strip()[0].upper() + a.strip()[1:]
                for a in author.affiliations
                if a and a.strip()
            ]

            # sort alphabetically (A -> Z)
            affiliations.sort()

            reporters.append(
                f"{author.first_name} {author.last_name} ({', '.join(affiliations)})"
            )

            if author.is_bot:
                bio = author.bio.strip()
                if bio and bio[-1] not in ".!?":
                    bio += "."
                remarks.append(bio[0].upper() + bio[1:])

        # avoid duplicates in the reporters, only keep the first occurrence of each reporter
        reporters = ", ".join(list(dict.fromkeys(reporters)))
        remarks = " ".join(remarks)

        if acknowledgments:
            reporters += f" {acknowledgments.strip()}"

        reporters = reporters.strip()
        remarks = remarks.strip()

    if submission_request.custom_remarks_string:
        remarks = submission_request.custom_remarks_string

    return reporters, remarks, warning


def process_submission_request(submission_request, session):
    """Process a TNS submission request.

    Parameters
    ----------
    submission_request : `~skyportal.models.ExternalPublishingSubmission`
        The submission request.
    session : `~sqlalchemy.orm.Session`
        The database session to use.
    """
    obj_id = submission_request.obj_id
    publishing_bot_id = submission_request.external_publishing_bot_id
    user_id = submission_request.user_id

    try:
        if (
            not submission_request.publish_to_tns
            and not submission_request.publish_to_hermes
        ):
            raise ValueError(
                "Submission request is not set to publish to TNS or Hermes, skipping."
            )

        user = session.scalar(sa.select(User).where(User.id == user_id))
        if user is None:
            raise ValueError(f"No user found with ID {user_id}.")

        publishing_bot = session.scalar(
            ExternalPublishingBot.select(user).where(
                ExternalPublishingBot.id == publishing_bot_id
            )
        )
        if publishing_bot is None:
            raise ValueError(
                f"No publishing bot found with ID {publishing_bot_id} or user {user_id} does not have access to it."
            )

        photometry_options = validate_photometry_options(
            getattr(submission_request, "photometry_options", {}),
            getattr(publishing_bot, "photometry_options", {}),
        )

        source, photometry, stream_ids = get_publishable_source_and_photometry(
            session,
            user,
            publishing_bot.id,
            obj_id,
            submission_request.instrument_ids,
            submission_request.stream_ids,
            photometry_options,
            submission_request.auto_submission,
        )

        reporters, remarks, warning = build_reporters_and_remarks_string(
            submission_request, source, publishing_bot.acknowledgments, session
        )
        # set it now, so we already have it if we need to reprocess the request
        submission_request.custom_publishing_string = reporters
        submission_request.custom_remarks_string = remarks

    except ValueError as e:
        log(str(e))
        try:
            flow = Flow()
            flow.push(
                user_id=submission_request.user_id,
                action_type="baselayer/SHOW_NOTIFICATION",
                payload={
                    "note": f"Error processing external publishing request: {str(e)}",
                    "type": "error",
                    "duration": 8000,
                },
            )
        except Exception:
            pass
        raise

    if submission_request.hermes_status == "processing":
        submit_to_hermes(
            submission_request, publishing_bot, user, photometry, reporters, session
        )

    if submission_request.tns_status == "processing":
        submit_to_tns(
            submission_request,
            publishing_bot,
            photometry,
            photometry_options,
            stream_ids,
            reporters,
            remarks,
            warning,
            session,
        )


def process_submission_requests():
    """
    Service to publish data to external services, such as TNS and Hermes,
    by processing the ExternalPublishingSubmission table.
    """
    session_context_id.set(uuid.uuid4().hex)

    while True:
        with DBSession() as session:
            try:
                submission_request = session.scalar(
                    sa.select(ExternalPublishingSubmission)
                    .where(
                        or_(
                            and_(
                                ExternalPublishingSubmission.publish_to_tns == True,
                                ExternalPublishingSubmission.tns_status.in_(
                                    ["pending", "processing"]
                                ),
                                ExternalPublishingSubmission.tns_submission_id.is_(
                                    None
                                ),
                            ),
                            and_(
                                ExternalPublishingSubmission.publish_to_hermes == True,
                                ExternalPublishingSubmission.hermes_status.in_(
                                    ["pending", "processing"]
                                ),
                            ),
                        )
                    )
                    .order_by(ExternalPublishingSubmission.created_at.asc())
                )
                if submission_request is None:
                    time.sleep(5)
                    continue
                else:
                    if submission_request.publish_to_hermes:
                        submission_request.hermes_status = "processing"
                    if submission_request.publish_to_tns:
                        submission_request.tns_status = "processing"
                    session.commit()
            except Exception as e:
                log(f"Error getting external publishing submission request: {str(e)}")
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
                            f"Error processing external publishing submission request {submission_request_id}: {str(e)}"
                        )
                        submission_request = session.scalar(
                            sa.select(ExternalPublishingSubmission).where(
                                ExternalPublishingSubmission.id == submission_request_id
                            )
                        )
                        if submission_request.publish_to_hermes:
                            submission_request.hermes_status = f"Error: {str(e)}"
                        if submission_request.publish_to_tns:
                            submission_request.tns_status = f"Error: {str(e)}"
                        session.commit()
                        flow = Flow()
                        flow.push(
                            "*",
                            "skyportal/REFRESH_EXTERNAL_PUBLISHING_SUBMISSIONS",
                            payload={
                                "external_publishing_bot_id": submission_request.external_publishing_bot_id
                            },
                        )
                    except Exception as e:
                        log(
                            f"Error updating external publishing submission request status: {str(e)}"
                        )


def validate_submission_requests():
    """Service to query TNS for the status of submitted AT reports and update the ExternalPublishingSubmission table."""
    session_context_id.set(uuid.uuid4().hex)
    while True:
        time.sleep(5)
        with DBSession() as session:
            # we look for TNS submissions with a 504 status (meaning the processing or validation failed at some point)
            # and re-set them as pending if they failed more than 5 minutes ago, confirmed if they were reported,
            # and label them appropriately if a more recent submission request successfully publish the object with the same bot
            try:
                failed_submission_requests = session.scalars(
                    sa.select(ExternalPublishingSubmission).where(
                        ExternalPublishingSubmission.tns_status.ilike(
                            "%504 - Gateway Time-out%"
                        ),
                        ExternalPublishingSubmission.modified
                        < datetime.datetime.utcnow() - datetime.timedelta(minutes=5),
                    )
                ).all()
                log(
                    f"Found {len(failed_submission_requests)} failed TNS submission requests to re-set..."
                )
                for submission_request in failed_submission_requests:
                    # check if there is a more recent submission request for the same object and bot that is submitted or confirmed,
                    # in which case we don't want to re-set the status of this one but label it appropriately
                    recent_submission_request = session.scalar(
                        sa.select(ExternalPublishingSubmission).where(
                            ExternalPublishingSubmission.obj_id
                            == submission_request.obj_id,
                            ExternalPublishingSubmission.external_publishing_bot_id
                            == submission_request.external_publishing_bot_id,
                            ExternalPublishingSubmission.created_at
                            > submission_request.created_at,
                            sa.or_(
                                ExternalPublishingSubmission.tns_status.ilike(
                                    "%submitted%"
                                ),
                                ExternalPublishingSubmission.tns_status.ilike(
                                    "%confirmed%"
                                ),
                            ),
                        )
                    )
                    if recent_submission_request is not None:
                        submission_request.tns_status = "Error: TNS was unresponsive at some point during processing, but a more recent submission request (from the same bot) reported the object since."
                        continue

                    # let's check if the object is already on TNS and submitted by this bot, in which case we can mark the submission request as confirmed
                    obj = session.scalar(
                        sa.select(Obj).where(Obj.id == submission_request.obj_id)
                    )
                    if (
                        obj.tns_name is not None
                        and isinstance(obj.tns_info, dict)
                        and obj.tns_info.get("reporterid") is not None
                        and obj.tns_info.get("reporterid")
                        == submission_request.external_publishing_bot.bot_id
                        and isinstance(obj.tns_info.get("reporting_group", {}), dict)
                        and obj.tns_info.get("reporting_group", {}).get("group_id")
                        is not None
                        and obj.tns_info.get("reporting_group", {}).get("group_id")
                        == submission_request.external_publishing_bot.source_group_id
                        and obj.tns_info.get("discoverer") is not None
                        and (
                            (
                                submission_request.tns_payload is not None
                                and isinstance(submission_request.tns_payload, dict)
                                and obj.tns_info.get("discoverer")
                                == submission_request.tns_payload.get("reporter")
                            )
                            or (
                                submission_request.custom_publishing_string is not None
                                and obj.tns_info.get("discoverer")
                                == submission_request.custom_publishing_string
                            )
                        )
                    ):
                        log(
                            f"TNS submission request {submission_request.id} for object {submission_request.obj_id} seems to have been successful, setting as confirmed"
                        )
                        submission_request.tns_status = "confirmed"
                        continue

                    # not reported on TNS by this bot yet, re-set the submission request to pending
                    log(
                        f"Re-setting failed TNS submission request {submission_request.id} for object {submission_request.obj_id}"
                    )
                    submission_request.tns_status = "pending"
                if len(failed_submission_requests) > 0:
                    session.commit()
            except Exception as e:
                log(f"Error re-setting failed TNS submission requests: {e}")
                session.rollback()

            try:
                # grab the first TNS bot submission request that has a submission ID that's not null
                submission_request = session.scalar(
                    sa.select(ExternalPublishingSubmission)
                    .where(
                        ExternalPublishingSubmission.tns_status.like("submitted"),
                        ExternalPublishingSubmission.tns_submission_id.isnot(None),
                        ExternalPublishingSubmission.external_publishing_bot_id.notin_(
                            sa.select(ExternalPublishingBot.id).where(
                                ExternalPublishingBot.testing.is_(True)
                            )
                        ),
                    )
                    .order_by(ExternalPublishingSubmission.created_at.asc())
                )
                if submission_request is None:
                    # here we add an extra sleep to avoid hammering the TNS API
                    print("Waiting for TNS submission requests to validate...")
                    time.sleep(25)
                    continue

                log(
                    f"Checking TNS submission request {submission_request.id} for object {submission_request.obj_id}"
                )

                tns_submission_id = submission_request.tns_submission_id

                publishing_bot = session.scalar(
                    sa.select(ExternalPublishingBot).where(
                        ExternalPublishingBot.id
                        == submission_request.external_publishing_bot_id
                    )
                )
                if publishing_bot is None:
                    log("Could not find publishing bot for this submission request")
                    continue

                tns_source, serialized_response, err = check_at_report(
                    tns_submission_id, publishing_bot
                )
                if (
                    not err
                    and not tns_source
                    and serialized_response
                    and "An identical AT report" in str(serialized_response)
                ):
                    submission_request.tns_status = "complete"
                    submission_request.tns_response = serialized_response
                    session.merge(submission_request)
                    session.commit()
                    log(
                        f"AT report of {submission_request.obj_id} already exists on TNS"
                    )
                elif not err and tns_source and serialized_response:
                    # we may have warnings after the "submitted" status, so we keep them in the "complete" status
                    existing_tns_status = (
                        str(submission_request.tns_status).strip().split(" ")
                    )
                    if existing_tns_status and existing_tns_status[0] == "submitted":
                        submission_request.tns_status = (
                            f"complete {' '.join(existing_tns_status[1:])}"
                        )
                    else:
                        submission_request.tns_status = "complete"
                    submission_request.tns_response = serialized_response
                    session.merge(submission_request)
                    session.commit()
                    log(
                        f"AT report of {submission_request.obj_id} submitted to TNS as {tns_source}"
                    )
                    try:
                        requests.post(
                            tns_retrieval_microservice_url,
                            json={"tns_source": tns_source},
                        )
                    except Exception as e:
                        log(f"Error submitting TNS name to retrieval queue: {e}")
                    try:
                        flow = Flow()
                        flow.push(
                            user_id=submission_request.user_id,
                            action_type="baselayer/SHOW_NOTIFICATION",
                            payload={
                                "note": f"AT report of {submission_request.obj_id} posted to TNS on {tns_source}",
                                "type": "info",
                                "duration": 8000,
                            },
                        )
                    except Exception:
                        pass
                elif err == "report not found":
                    # Sometimes TNS accepts a report but it disappears.
                    # If it's been <1 min since last update, wait; otherwise, mark as pending to retry.
                    if (
                        datetime.datetime.utcnow() - submission_request.modified
                    ).total_seconds() > 60:
                        submission_request.tns_status = "pending"
                        submission_request.tns_submission_id = None
                        session.merge(submission_request)
                        session.commit()
                        log(
                            f"AT report submission of {submission_request.obj_id} not found on TNS, retrying"
                        )
                elif err is not None and serialized_response is not None:
                    submission_request.tns_status = f"Error: {err}"
                    submission_request.response = serialized_response
                    session.merge(submission_request)
                    session.commit()
                    log(f"Error checking TNS report: {err}")
                else:
                    log(
                        f"Error checking TNS report - source {tns_source}, response {serialized_response}, err {err}"
                    )
            except Exception as e:
                if "ExternalPublishingError" in str(e):
                    log(f"ExternalPublishingError: {str(e)}")
                    session.rollback()
                    continue
                session.rollback()
                traceback.print_exc()
                log(f"Unexpected error checking TNS report: {str(e)}")
                continue


@check_loaded(logger=log)
def service(*args, **kwargs):
    t = Thread(target=process_submission_requests)
    t2 = Thread(target=validate_submission_requests)
    t.start()
    t2.start()
    while True:
        log("External publishing submission queue heartbeat")
        time.sleep(120)


if __name__ == "__main__":
    try:
        service()
    except Exception as e:
        log(f"Error starting external publishing submission queue: {str(e)}")
        raise e
