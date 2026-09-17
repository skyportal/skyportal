"""Submitting linked moving-object tracks to the Minor Planet Center.

An MPC submission describes a track rather than a detection: one ADES document
carries every epoch as its own observation line under a single ``trkSub``. That
differs from TNS and Hermes, where one object is one report, so the submission
row hangs off the track's anchor Obj and the remaining epochs create nothing.
"""

import requests
import sqlalchemy as sa

from baselayer.log import make_log

from ..models import ObjToSuperObj, SharingServiceSubmission, SuperObj

log = make_log("mpc_submission")

# Minimum epochs before a group of Objs is a track worth submitting. A single
# detection is a known body the MPC already has, or a linkage of one, and
# either way there is no orbit to report.
MIN_TRACK_EPOCHS = 2

# Digest2 score at or above which the MPC wants the NEO submission route.
NEO_DIGEST2_THRESHOLD = 65.0

# The annotation BOOM writes on a track's earliest epoch, carrying the orbit.
TRACK_ANNOTATION_ORIGIN = "boom:track"

MPC_SUBMIT_URL = "https://minorplanetcenter.net/submit_xml"
MPC_TIMEOUT = 120  # seconds


def track_for_obj(session, obj_id):
    """The moving-object track this Obj belongs to, or None.

    Only a multi-epoch ``is_roid`` SuperObj counts: the single-epoch ones are
    known bodies recorded by the solar-system ingest, which the MPC already has.
    """
    super_objs = (
        session.scalars(
            sa.select(SuperObj)
            .join(ObjToSuperObj, ObjToSuperObj.super_obj_id == SuperObj.id)
            .where(ObjToSuperObj.obj_id == obj_id, SuperObj.is_roid.is_(True))
        )
        .unique()
        .all()
    )
    for super_obj in super_objs:
        if len(super_obj.objs) >= MIN_TRACK_EPOCHS:
            return super_obj
    return None


def track_anchor_obj_id(super_obj):
    """The Obj a track's submission and annotation hang off.

    The earliest epoch, matching where BOOM writes its ``boom:track``
    annotation. Tracks are built forward in time and extended, so this does not
    move once the track exists.
    """
    objs = sorted(
        super_obj.objs, key=lambda o: (o.created_at is None, o.created_at, o.id)
    )
    return objs[0].id if objs else None


def existing_track_submission(session, super_obj, sharing_service_id):
    """An MPC submission already filed for any epoch of this track, or None.

    Checked across every member rather than the anchor alone. The auto-publisher
    fires once per saved source, so a reviewer saving the five epochs of a track
    would otherwise file five MPC submissions for one object. The anchor is also
    not necessarily the epoch saved first, so checking it alone would miss.
    """
    obj_ids = [obj.id for obj in super_obj.objs]
    if not obj_ids:
        return None
    return session.scalars(
        sa.select(SharingServiceSubmission).where(
            SharingServiceSubmission.sharing_service_id == sharing_service_id,
            SharingServiceSubmission.obj_id.in_(obj_ids),
            SharingServiceSubmission.publish_to_mpc.is_(True),
        )
    ).first()


def track_orbit(super_obj):
    """The orbit BOOM fitted for this track, from the anchor's annotation.

    Returns an empty dict when absent, so a caller can report a track whose
    orbit did not survive rather than failing on the lookup.
    """
    anchor_id = track_anchor_obj_id(super_obj)
    for obj in super_obj.objs:
        if obj.id != anchor_id:
            continue
        for annotation in obj.annotations or []:
            if annotation.origin == TRACK_ANNOTATION_ORIGIN:
                return annotation.data or {}
    return {}


def is_neo_candidate(orbit):
    """Whether the MPC's NEO submission route applies, from the digest2 score."""
    score = (orbit or {}).get("digest2")
    try:
        return float(score) >= NEO_DIGEST2_THRESHOLD
    except (TypeError, ValueError):
        return False


def ades_for_track(broker, session, super_obj):
    """The ADES document for a whole track, rendered by the broker.

    Asked for rather than built here: the format carries version-2017 header
    blocks, fixed column widths and a per-survey observatory code, and the
    ``trkSub`` that links a track's observations has to match the one the broker
    assigned when it found the linkage. Two renderings would drift.
    """
    from ..broker_apis.boom import _request

    obj_ids = [obj.id for obj in super_obj.objs]
    return _request(
        broker,
        "POST",
        "tracks/ades",
        json={"obj_ids": obj_ids, "super_obj_id": super_obj.id},
    )


def submit_track(broker, session, super_obj, submission, dry_run=True):
    """File a track with the Minor Planet Center, or rehearse filing it.

    ``dry_run`` defaults to true and a caller has to ask for a live submission:
    a report goes out under a named person, is visible to the whole field and is
    awkward to retract, so the safe direction for a mistake is not submitting.
    """
    ades = ades_for_track(broker, session, super_obj)
    submission.mpc_payload = {"ades": ades, "dry_run": bool(dry_run)}

    if dry_run:
        submission.mpc_status = "dry run"
        log(
            f"MPC dry run for SuperObj {super_obj.id}: "
            f"{len(super_obj.objs)} epochs, nothing submitted"
        )
        return submission

    altdata = getattr(broker, "mpc_altdata", None) or {}
    acknowledgement_address = altdata.get("ack_email")
    if not acknowledgement_address:
        raise ValueError(
            "No ack_email in the sharing service's mpc_altdata. The MPC files a "
            "submission under a named person, so it has to be configured rather "
            "than defaulted to whoever happens to be running the service."
        )

    neo = is_neo_candidate(track_orbit(super_obj))
    fields = {
        "ack": (None, "NEO CANDIDATE" if neo else "ZTF observation"),
        "ac2": (None, acknowledgement_address),
        "source": (None, ades),
    }
    if neo:
        fields["obj_type"] = (None, "NEO")

    response = requests.post(MPC_SUBMIT_URL, files=fields, timeout=MPC_TIMEOUT)
    submission.mpc_response = {
        "status_code": response.status_code,
        "text": response.text[:4000],
    }
    if response.status_code >= 400:
        submission.mpc_status = f"Error: HTTP {response.status_code}"
        log(
            f"MPC submission failed for SuperObj {super_obj.id}: "
            f"HTTP {response.status_code}"
        )
    else:
        submission.mpc_status = "submitted"
        log(
            f"Submitted SuperObj {super_obj.id} to the MPC as "
            f"{'an NEO candidate' if neo else 'a regular observation'}"
        )
    return submission
