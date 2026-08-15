from collections import defaultdict

import astropy.units as u
import sqlalchemy as sa
from astropy.time import Time
from sqlalchemy.orm import aliased, joinedload, selectinload

from baselayer.app.access import auth_or_token
from baselayer.log import make_log

from ....models import (
    Allocation,
    Annotation,
    ClassicalAssignment,
    Comment,
    FollowupRequest,
    GcnEventObj,
    Obj,
    ObjToSuperObj,
    ObservingRun,
    Photometry,
    Source,
)
from ....models.phot_stat import PHOT_DETECTION_THRESHOLD
from ....models.scan_report.scan_report_item import ScanReportItem
from ....utils.gcn_crossmatch import ANNOTATION_ORIGIN as GCN_CROSSMATCH_ORIGIN
from ....utils.parse import safe_round
from ...base import BaseHandler

log = make_log("api/scan_report_item")

# Datalab crossmatch catalogs are posted as Annotations with origin
# "<catalog>-<source_id>" (see DatalabQueryHandler); DESI catalogs are all
# named "desi_*" (e.g. "desi_dr1").
DESI_ORIGIN_PREFIX = "desi_"


def _survey_of(band):
    """Map a band name to its survey label for the detections summary."""
    if not band:
        return None
    b = band.lower()
    if b.startswith("ztf"):
        return "ZTF"
    if b.startswith("lsst"):
        return "LSST"
    return band


def _followup_request_type(allocation, instrument, payload=None):
    """Classify a follow-up request as forced photometry, spectroscopy or photometry."""
    if allocation and allocation.types and "forced_photometry" in allocation.types:
        return "forced_photometry"
    if instrument and instrument.name == "SEDM":
        # SEDM is an "imaging spectrograph" but most of its request modes
        # (e.g. "3-shot (gri)") are pure photometry; only modes that include
        # the IFU are spectroscopy.
        payload = payload or {}
        observation_type = payload.get("observation_type") or ""
        observation_choices = payload.get("observation_choices") or []
        if "IFU" in observation_type or "IFU" in observation_choices:
            return "spectroscopy"
        return "photometry"
    if instrument and instrument.type in ("spectrograph", "imaging spectrograph"):
        return "spectroscopy"
    return "photometry"


def _host_offset(obj):
    """Angular (arcsec) and physical (kpc) separation from the obj to its host galaxy."""
    if not obj.host:
        return None, None
    arcsec = None
    kpc = None
    try:
        sep = obj.host_offset
        arcsec = safe_round(sep.arcsec, 3) if sep is not None else None
    except Exception:
        arcsec = None
    try:
        dist = obj.host_distance
        kpc = safe_round(dist.to(u.kpc).value, 3) if dist is not None else None
    except Exception:
        kpc = None
    return arcsec, kpc


def _build_scan_report_item(
    report,
    obj,
    sources,
    followup_requests,
    assignment_rows,
    comment,
    now_mjd,
    gcn_match=None,
    desi_annotation=None,
    associated_objs=None,
    previous=None,
):
    """Build a report item from data already fetched for this obj (no queries)."""
    if obj.photstats:
        current_filter = obj.photstats[0].last_detected_filter
        current_mag = obj.photstats[0].last_detected_mag
        current_mjd = obj.photstats[0].last_detected_mjd
        current_age = now_mjd - obj.photstats[0].first_detected_mjd
        dm = obj.dm
        abs_mag = current_mag - dm if dm else None
    else:
        current_filter = None
        current_mag = None
        current_mjd = None
        current_age = None
        abs_mag = None

    classifications = None
    if obj.classifications:
        classifications = [
            {
                "probability": classification.probability,
                "classification": classification.classification,
                "ml": classification.ml,
                "created_at": classification.created_at.isoformat(),
            }
            for classification in obj.classifications
        ]

    saved_info = None
    if sources:
        saved_info = [
            {
                "saved_at": source.saved_at.isoformat(),
                "saved_by": {
                    "first_name": source.saved_by.first_name,
                    "last_name": source.saved_by.last_name,
                },
                "group": source.group.name,
            }
            for source in sources
        ]

    # Every follow-up request is kept (newest first) with its requester, so scanners
    # can see who requested what, where and at which priority.
    followups = [
        {
            "instrument": followup.instrument.name,
            "type": _followup_request_type(
                followup.allocation, followup.instrument, followup.payload
            ),
            "priority": (followup.payload or {}).get("priority"),
            "start_date": (followup.payload or {}).get("start_date"),
            "end_date": (followup.payload or {}).get("end_date"),
            "status": followup.status,
            "requester": followup.requester.username if followup.requester else None,
        }
        for followup in followup_requests
    ] or None

    assignments = [
        {
            "instrument": assignment.run.instrument.name,
            "run_date": (
                assignment.run.calendar_date.isoformat()
                if assignment.run.calendar_date
                else None
            ),
            "priority": assignment.priority,
            "status": assignment.status,
            "requester": (
                assignment.requester.username if assignment.requester else None
            ),
        }
        for assignment in assignment_rows
    ] or None

    # First and peak detection per survey, read from the (already-loaded) PhotStat so
    # we don't scan raw photometry (which doesn't scale to long report windows).
    # PhotStat carries the global first detection and the peak per filter; a report is
    # generated per single-survey group, so the global first is that survey's first,
    # and peak per survey is the brightest across the survey's filters.
    detections_by_survey = {}
    if obj.photstats:
        ps = obj.photstats[0]

        def _entry(mjd, mag, filt, fp=None):
            if mjd is None:
                return None
            entry = {
                "mag": safe_round(mag, 3),
                "mjd": safe_round(mjd, 5),
                "filter": filt,
                "days_ago": safe_round(now_mjd - mjd, 2),
            }
            if fp is not None:
                entry["fp"] = fp
            return entry

        # The global first detection can be a forced-photometry point; PhotStat
        # separately tracks the first non-forced-phot detection, which is >= it
        # (a strict superset filtered down), so a mismatch means the true first
        # detection was FP.
        is_first_fp = ps.first_detected_mjd is not None and (
            ps.first_detected_no_forced_phot_mjd is None
            or ps.first_detected_no_forced_phot_mjd > ps.first_detected_mjd
        )
        first_entry = _entry(
            ps.first_detected_mjd,
            ps.first_detected_mag,
            ps.first_detected_filter,
            fp=is_first_fp,
        )
        first_survey = _survey_of(ps.first_detected_filter)

        # If the first detection is FP, also surface the first "real" (non-FP)
        # detection so scanners aren't misled by an FP-only rise.
        first_real_entry = None
        first_real_survey = None
        if is_first_fp:
            first_real_entry = _entry(
                ps.first_detected_no_forced_phot_mjd,
                ps.first_detected_no_forced_phot_mag,
                ps.first_detected_no_forced_phot_filter,
                fp=False,
            )
            first_real_survey = _survey_of(ps.first_detected_no_forced_phot_filter)

        # survey -> (mag, mjd, filter), brightest (min mag) across the survey's filters
        peak_by_survey = {}
        peak_mjd_per_filter = ps.peak_mjd_per_filter or {}
        for band, mag in (ps.peak_mag_per_filter or {}).items():
            if mag is None:
                continue
            survey = _survey_of(band)
            current = peak_by_survey.get(survey)
            if current is None or mag < current[0]:
                peak_by_survey[survey] = (
                    mag,
                    peak_mjd_per_filter.get(band),
                    band,
                )

        surveys = (
            set(peak_by_survey)
            | ({first_survey} if first_survey else set())
            | ({first_real_survey} if first_real_survey else set())
        )
        for survey in surveys:
            peak = peak_by_survey.get(survey)
            detections_by_survey[survey] = {
                "first": first_entry if survey == first_survey else None,
                "first_real": (
                    first_real_entry if survey == first_real_survey else None
                ),
                "peak": _entry(peak[1], peak[0], peak[2]) if peak else None,
            }
    detections_by_survey = detections_by_survey or None

    host_offset_arcsec, host_offset_kpc = _host_offset(obj)

    return ScanReportItem(
        obj_id=obj.id,
        scan_report=report,
        data={
            "tns_name": obj.tns_name,
            # Other Objs (e.g. an LSST detection) linked to this one via a shared
            # SuperObj, each with its own aliases, if any.
            "associated_objs": associated_objs,
            "comment": comment.text if comment else None,
            "host_redshift": obj.redshift,
            # Spectroscopic redshift from a DESI crossmatch, when one exists.
            "desi_redshift": (desi_annotation.data or {}).get("z")
            if desi_annotation
            else None,
            "offset": (
                {"arcsec": host_offset_arcsec, "kpc": host_offset_kpc}
                if host_offset_arcsec is not None or host_offset_kpc is not None
                else None
            ),
            "current_filter": current_filter,
            "abs_mag": safe_round(abs_mag, 3),
            "current_mag": safe_round(current_mag, 3),
            "current_mjd": safe_round(current_mjd, 5),
            "current_age": safe_round(current_age, 2),
            # The detection immediately before the current one, in the same filter.
            "previous_mag": safe_round((previous or {}).get("mag"), 3),
            "previous_mjd": safe_round((previous or {}).get("mjd"), 5),
            "previous_filter": (previous or {}).get("filter"),
            "classifications": classifications,
            "saved_info": saved_info,
            "followups": followups,
            "assignments": assignments,
            "detections_by_survey": detections_by_survey,
            # Present only for an event-scoped report: how this object relates to
            # the event, and the scanner's verdict on it.
            "gcn_match": gcn_match,
        },
    )


async def create_scan_report_items(
    session, report, sources_by_objs, gcn_event_dateobs=None
):
    """Build report items for many objects with a constant number of queries.

    Each data type (Obj, Source, FollowupRequest, ClassicalAssignment, Photometry,
    Comment) is fetched once for every object and grouped by obj_id, rather than
    querying once per object.

    Parameters
    ----------
    session: sqlalchemy.orm.Session
    report: skyportal.model.ScanReport
    sources_by_objs: list of tuples (obj_id, source_ids)
    Returns
    -------
    list of skyportal.model.ScanReportItem
    """
    valid = [
        (obj_id, source_ids)
        for obj_id, source_ids in sources_by_objs
        if obj_id and source_ids
    ]
    if not valid:
        return []

    user_or_token = session.user_or_token

    # For an event-scoped report, snapshot each object's relation to the event:
    # the crossmatch's own measurements plus the scanner's verdict so far.
    gcn_match_by_obj = {}
    if gcn_event_dateobs is not None:
        obj_ids = [obj_id for obj_id, _ in valid]
        verdicts = (
            await session.scalars(
                GcnEventObj.select(user_or_token).where(
                    GcnEventObj.obj_id.in_(obj_ids),
                    GcnEventObj.dateobs == gcn_event_dateobs,
                )
            )
        ).all()
        annotations = (
            await session.scalars(
                Annotation.select(user_or_token).where(
                    Annotation.obj_id.in_(obj_ids),
                    Annotation.origin == GCN_CROSSMATCH_ORIGIN,
                )
            )
        ).all()
        measured = {}
        want = gcn_event_dateobs.isoformat()
        for annotation in annotations:
            for payload in (annotation.data or {}).values():
                if isinstance(payload, dict) and payload.get("dateobs") == want:
                    measured[annotation.obj_id] = payload
        for verdict in verdicts:
            entry = dict(measured.pop(verdict.obj_id, {}))
            entry.update(
                {
                    "status": verdict.status,
                    "explanation": verdict.explanation,
                    "notes": verdict.notes,
                }
            )
            gcn_match_by_obj[verdict.obj_id] = entry
        # matched by the crossmatch but with no verdict row yet
        for obj_id, payload in measured.items():
            gcn_match_by_obj[obj_id] = {**payload, "status": "pending"}

    objs = {}
    sources_by_obj = defaultdict(list)
    followups_by_obj = defaultdict(list)
    assignments_by_obj = defaultdict(list)
    comment_by_obj = {}  # obj_id -> most recent non-bot scanner comment
    desi_by_obj = {}  # obj_id -> most recent DESI crossmatch Annotation
    associated_by_obj = defaultdict(dict)  # obj_id -> {assoc_obj_id: aliases}
    previous_by_obj = {}  # obj_id -> {mag, mjd, filter} of the detection before the last

    # Fetch in chunks of objects: a single ``obj_id IN (...)`` over a long report
    # window (thousands of objects) pushes the planner off the obj_id index onto a
    # seq scan of these large tables, which times out. Chunking keeps every query on
    # the index. Access rules are still applied per model.
    for chunk in (valid[i : i + 500] for i in range(0, len(valid), 500)):
        chunk_obj_ids = [obj_id for obj_id, _ in chunk]
        chunk_source_ids = [sid for _, sids in chunk for sid in sids]

        for obj in (
            await session.scalars(
                Obj.select(user_or_token, mode="read")
                .options(
                    selectinload(Obj.photstats),
                    selectinload(Obj.classifications),
                    selectinload(Obj.host),
                )
                .where(Obj.id.in_(chunk_obj_ids))
            )
        ).all():
            objs[obj.id] = obj

        # The detection immediately before each obj's current (last-detected) one,
        # in that same filter. PhotStat only tracks first/last/peak, not the
        # runner-up, so this needs raw Photometry -- ranked via a window function
        # and filtered to rn == 2 in SQL so only that one row per (obj, filter)
        # pair is ever pulled back, not the object's full photometry history.
        pairs = [
            (obj_id, objs[obj_id].photstats[0].last_detected_filter)
            for obj_id in chunk_obj_ids
            if objs.get(obj_id)
            and objs[obj_id].photstats
            and objs[obj_id].photstats[0].last_detected_filter
        ]
        if pairs:
            ranked = (
                Photometry.select(user_or_token, mode="read")
                .where(
                    sa.tuple_(Photometry.obj_id, Photometry.filter).in_(pairs),
                    Photometry.snr > PHOT_DETECTION_THRESHOLD,
                )
                .add_columns(
                    Photometry.mag.label("mag"),
                    sa.func.row_number()
                    .over(
                        partition_by=Photometry.obj_id,
                        order_by=Photometry.mjd.desc(),
                    )
                    .label("rn"),
                )
                .subquery()
            )
            for obj_id, filt, mjd, mag in await session.execute(
                sa.select(
                    ranked.c.obj_id, ranked.c.filter, ranked.c.mjd, ranked.c.mag
                ).where(ranked.c.rn == 2)
            ):
                previous_by_obj[obj_id] = {"mag": mag, "mjd": mjd, "filter": filt}

        for source in (
            await session.scalars(
                Source.select(user_or_token, mode="read")
                .options(selectinload(Source.saved_by), selectinload(Source.group))
                .where(
                    Source.obj_id.in_(chunk_obj_ids),
                    Source.id.in_(chunk_source_ids),
                )
            )
        ).all():
            sources_by_obj[source.obj_id].append(source)

        for followup in (
            await session.scalars(
                FollowupRequest.select(user_or_token, mode="read")
                .options(
                    joinedload(FollowupRequest.allocation).joinedload(
                        Allocation.instrument
                    ),
                    joinedload(FollowupRequest.requester),
                )
                .where(FollowupRequest.obj_id.in_(chunk_obj_ids))
                .order_by(FollowupRequest.created_at.desc())
            )
        ).all():
            followups_by_obj[followup.obj_id].append(followup)

        for assignment in (
            await session.scalars(
                ClassicalAssignment.select(user_or_token, mode="read")
                .options(
                    joinedload(ClassicalAssignment.run).joinedload(
                        ObservingRun.instrument
                    ),
                    joinedload(ClassicalAssignment.requester),
                )
                .where(ClassicalAssignment.obj_id.in_(chunk_obj_ids))
                .order_by(ClassicalAssignment.created_at.desc())
            )
        ).all():
            assignments_by_obj[assignment.obj_id].append(assignment)

        for comment in (
            await session.scalars(
                Comment.select(user_or_token, mode="read")
                .where(
                    Comment.obj_id.in_(chunk_obj_ids),
                    Comment.author_id == report.author_id,
                    Comment.bot.is_(False),
                )
                .order_by(Comment.created_at.desc())
            )
        ).all():
            comment_by_obj.setdefault(comment.obj_id, comment)

        for annotation in (
            await session.scalars(
                Annotation.select(user_or_token, mode="read")
                .where(
                    Annotation.obj_id.in_(chunk_obj_ids),
                    Annotation.origin.startswith(DESI_ORIGIN_PREFIX),
                )
                .order_by(Annotation.created_at.desc())
            )
        ).all():
            desi_by_obj.setdefault(annotation.obj_id, annotation)

        # Objs sharing a SuperObj with one of this chunk's objs (e.g. the LSST
        # detection linked to a ZTF one), via a self-join on the link table.
        # Joined against the access-controlled Obj select so an associated obj
        # the user can't read is silently dropped, not leaked.
        accessible_objs = Obj.select(user_or_token, mode="read").subquery()
        o2s_this = aliased(ObjToSuperObj)
        o2s_other = aliased(ObjToSuperObj)
        for obj_id, assoc_obj_id, assoc_alias in await session.execute(
            sa.select(o2s_this.obj_id, accessible_objs.c.id, accessible_objs.c.alias)
            .select_from(o2s_this)
            .join(o2s_other, o2s_other.super_obj_id == o2s_this.super_obj_id)
            .join(accessible_objs, accessible_objs.c.id == o2s_other.obj_id)
            .where(
                o2s_this.obj_id.in_(chunk_obj_ids),
                o2s_other.obj_id != o2s_this.obj_id,
            )
        ):
            associated_by_obj[obj_id][assoc_obj_id] = assoc_alias

    now_mjd = Time.now().mjd
    items = []
    for obj_id, _source_ids in valid:
        obj = objs.get(obj_id)
        if obj is None:
            continue
        items.append(
            _build_scan_report_item(
                report,
                obj,
                sources_by_obj.get(obj_id, []),
                followups_by_obj.get(obj_id, []),
                assignments_by_obj.get(obj_id, []),
                comment_by_obj.get(obj_id),
                now_mjd,
                gcn_match=gcn_match_by_obj.get(obj_id),
                desi_annotation=desi_by_obj.get(obj_id),
                previous=previous_by_obj.get(obj_id),
                associated_objs=[
                    {"obj_id": assoc_obj_id, "aliases": aliases}
                    for assoc_obj_id, aliases in associated_by_obj.get(
                        obj_id, {}
                    ).items()
                ]
                or None,
            )
        )
    return items


class ScanReportItemHandler(BaseHandler):
    @auth_or_token
    async def patch(self, report_id: int, item_id: int):
        """
        ---
        summary: Update an item from a scanning report
        tags:
          - report item
        parameters:
          - in: path
            name: report_id
            required: true
            schema:
              type: integer
            description: ID of the report where the item is located
          - in: path
            name: item_id
            required: true
            schema:
              type: integer
            description: ID of the report item to update
        requestBody:
          content:
            application/json:
              schema:
                type: object
                properties:
                  comment:
                    type: string
        responses:
          200:
            content:
              application/json:
                schema:
                  allOf:
                    - $ref: '#/components/schemas/Success'
                    - type: object
                      properties:
                        data:
                          $ref: '#/components/schemas/ScanReportItem'
          400:
            content:
              application/json:
                schema: Error
        """
        data = self.get_json()
        try:
            report_id = int(report_id)
            item_id = int(item_id)
        except (TypeError, ValueError):
            return self.error(f"Invalid report_id/item_id: {report_id}/{item_id}")

        async with self.AsyncSession() as session:
            item = await session.scalar(
                ScanReportItem.select(session.user_or_token, mode="read").where(
                    ScanReportItem.id == item_id,
                    ScanReportItem.scan_report_id == report_id,
                )
            )
            if item is None:
                return self.error("Report item not found")

            item.data = {
                **item.data,
                "comment": data.get("comment"),
            }

            await session.commit()

            self.push_all(
                action="skyportal/REFRESH_SCAN_REPORT_ITEM",
                payload={"report_id": report_id},
            )
            return self.success()

    @auth_or_token
    async def get(self, report_id: int, _):
        """
        ---
        summary: Retrieve all items in a scanning report
        tags:
          - report item
        parameters:
          - in: path
            name: report_id
            required: true
            schema:
              type: integer
            description: ID of the report to retrieve items from
        responses:
          200:
            content:
              application/json:
                schema: ArrayOfScanReportItems
          400:
            content:
              application/json:
                schema: Error
        """
        try:
            report_id = int(report_id)
        except (TypeError, ValueError):
            return self.error(f"Invalid report_id: {report_id}")
        async with self.AsyncSession() as session:
            result = await session.scalars(
                ScanReportItem.select(session.user_or_token, mode="read").where(
                    ScanReportItem.scan_report_id == report_id
                )
            )
            return self.success(data=result.all())
