from astropy.time import Time
import datetime
from json.decoder import JSONDecodeError
import astropy.units as u
from geojson import Point, Feature
import python_http_client.exceptions
from twilio.base.exceptions import TwilioException
from tornado.ioloop import IOLoop
import io
from dateutil.parser import isoparse
import sqlalchemy as sa
from sqlalchemy.orm import joinedload
from sqlalchemy import func, or_, distinct
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql.expression import cast
import arrow
from marshmallow import Schema, fields
from marshmallow.exceptions import ValidationError
import operator  # noqa: F401
import functools
import conesearch_alchemy as ca
import healpix_alchemy as ha
import time

from ...utils.UTCTZnaiveDateTime import UTCTZnaiveDateTime
from ...utils.sizeof import sizeof, SIZE_WARNING_THRESHOLD

from baselayer.app.access import permissions, auth_or_token
from baselayer.app.env import load_env
from baselayer.app.model_util import recursive_to_dict
from baselayer.app.flow import Flow
from baselayer.app.custom_exceptions import AccessError
from baselayer.log import make_log

from ..base import BaseHandler
from ...models import (
    Allocation,
    Annotation,
    Comment,
    Instrument,
    Obj,
    User,
    Source,
    Thumbnail,
    Token,
    Photometry,
    Group,
    FollowupRequest,
    ClassicalAssignment,
    ObservingRun,
    SourceNotification,
    Classification,
    Taxonomy,
    Localization,
    LocalizationTile,
    Listing,
    PhotStat,
    Spectrum,
    SourceView,
)
from ...utils.offset import (
    get_nearby_offset_stars,
    facility_parameters,
    source_image_parameters,
    get_finding_chart,
    _calculate_best_position_for_offset_stars,
)
from .candidate import (
    grab_query_results,
    update_redshift_history_if_relevant,
    update_healpix_if_relevant,
    add_linked_thumbnails_and_push_ws_msg,
    Session,
)
from .photometry import serialize
from .color_mag import get_color_mag

DEFAULT_SOURCES_PER_PAGE = 100
MAX_SOURCES_PER_PAGE = 500
MAX_NUM_DAYS_USING_LOCALIZATION = 31
_, cfg = load_env()
log = make_log('api/source')

MAX_LOCALIZATION_SOURCES = 50000


def get_source(
    obj_id,
    user_id,
    session,
    include_thumbnails=False,
    include_comments=False,
    include_photometry=False,
    include_photometry_exists=False,
    include_spectrum_exists=False,
    include_period_exists=False,
    include_detection_stats=False,
    is_token_request=False,
    include_requested=False,
    requested_only=False,
    include_color_mag=False,
):
    """Query source from database.
    obj_id: int
        Source ID
    user_id : int
        SkyPortal ID of User posting the GcnEvent
    session: sqlalchemy.Session
        Database session for this transaction
    See Source Handler for optional arguments
    """

    user = session.scalar(sa.select(User).where(User.id == user_id))

    options = []
    if include_thumbnails:
        options.append(joinedload(Obj.thumbnails))
    if include_detection_stats:
        options.append(joinedload(Obj.photstats))

    s = session.scalars(
        Obj.select(user, options=options).where(Obj.id == obj_id)
    ).first()
    if s is None:
        raise ValueError("Source not found")

    source_info = s.to_dict()
    source_info["followup_requests"] = session.scalars(
        FollowupRequest.select(
            user,
            options=[
                joinedload(FollowupRequest.allocation).joinedload(
                    Allocation.instrument
                ),
                joinedload(FollowupRequest.allocation).joinedload(Allocation.group),
                joinedload(FollowupRequest.requester),
            ],
        )
        .where(FollowupRequest.obj_id == obj_id)
        .where(FollowupRequest.status != "deleted")
    ).all()
    source_info["assignments"] = session.scalars(
        ClassicalAssignment.select(
            user,
            options=[
                joinedload(ClassicalAssignment.run)
                .joinedload(ObservingRun.instrument)
                .joinedload(Instrument.telescope)
            ],
        ).where(ClassicalAssignment.obj_id == obj_id)
    ).all()
    point = ca.Point(ra=s.ra, dec=s.dec)
    # Check for duplicates (within 4 arcsecs)
    duplicates = session.scalars(
        Obj.select(user).where(Obj.within(point, 4 / 3600)).where(Obj.id != s.id)
    ).all()
    if len(duplicates) > 0:
        source_info["duplicates"] = [dup.id for dup in duplicates]
    else:
        source_info["duplicates"] = None

    if is_token_request:
        # Logic determining whether to register front-end request as view lives in front-end
        sv = SourceView(
            obj_id=obj_id,
            username_or_token_id=user.id,
            is_token=True,
        )
        session.add(sv)
        # To keep loaded relationships from being cleared in verify_and_commit:
        source_info = recursive_to_dict(source_info)
        session.commit()

    if include_thumbnails:
        existing_thumbnail_types = [thumb.type for thumb in s.thumbnails]
        if "ps1" not in existing_thumbnail_types:
            IOLoop.current().run_in_executor(
                None,
                lambda: add_ps1_thumbnail_and_push_ws_msg(obj_id, user_id),
            )
        if (
            "sdss" not in existing_thumbnail_types
            or "ls" not in existing_thumbnail_types
        ):
            IOLoop.current().run_in_executor(
                None,
                lambda: add_linked_thumbnails_and_push_ws_msg(obj_id, user_id),
            )
    if include_comments:
        comments = (
            session.scalars(
                Comment.select(
                    user,
                    options=[
                        joinedload(Comment.author),
                        joinedload(Comment.groups),
                    ],
                ).where(Comment.obj_id == obj_id)
            )
            .unique()
            .all()
        )
        source_info["comments"] = sorted(
            (
                {
                    **{k: v for k, v in c.to_dict().items() if k != "attachment_bytes"},
                    "author": {
                        **c.author.to_dict(),
                        "gravatar_url": c.author.gravatar_url,
                    },
                }
                for c in comments
            ),
            key=lambda x: x["created_at"],
            reverse=True,
        )
    if include_period_exists:
        annotations = session.scalars(
            Annotation.select(user).where(Annotation.obj_id == obj_id)
        ).all()
        period_str_options = ['period', 'Period', 'PERIOD']
        source_info["period_exists"] = any(
            [
                isinstance(an.data, dict) and period_str in an.data
                for an in annotations
                for period_str in period_str_options
            ]
        )

    source_info["annotations"] = sorted(
        session.scalars(
            Annotation.select(user)
            .options(joinedload(Annotation.author))
            .where(Annotation.obj_id == obj_id)
        )
        .unique()
        .all(),
        key=lambda x: x.origin,
    )
    readable_classifications = (
        session.scalars(
            Classification.select(user).where(Classification.obj_id == obj_id)
        )
        .unique()
        .all()
    )

    readable_classifications_json = []
    for classification in readable_classifications:
        classification_dict = classification.to_dict()
        classification_dict['groups'] = [g.to_dict() for g in classification.groups]
        readable_classifications_json.append(classification_dict)

    source_info["classifications"] = readable_classifications_json
    source_info["gal_lat"] = s.gal_lat_deg
    source_info["gal_lon"] = s.gal_lon_deg
    source_info["luminosity_distance"] = s.luminosity_distance
    source_info["dm"] = s.dm
    source_info["angular_diameter_distance"] = s.angular_diameter_distance

    if include_photometry:
        photometry = session.scalars(
            Photometry.select(user).where(Photometry.obj_id == obj_id)
        ).all()
        source_info["photometry"] = [
            serialize(phot, 'ab', 'flux') for phot in photometry
        ]
    if include_photometry_exists:
        source_info["photometry_exists"] = (
            session.scalars(
                Photometry.select(user).where(Photometry.obj_id == obj_id)
            ).first()
            is not None
        )
    if include_spectrum_exists:
        source_info["spectrum_exists"] = (
            session.scalars(
                Spectrum.select(user).where(Spectrum.obj_id == obj_id)
            ).first()
            is not None
        )
    source_query = Source.select(user).where(Source.obj_id == source_info["id"])
    source_query = apply_active_or_requested_filtering(
        source_query, include_requested, requested_only
    )
    source_subquery = source_query.subquery()
    groups = session.scalars(
        Group.select(user).join(source_subquery, Group.id == source_subquery.c.group_id)
    ).all()
    source_info["groups"] = [g.to_dict() for g in groups]
    for group in source_info["groups"]:
        source_table_row = session.scalars(
            Source.select(user)
            .where(Source.obj_id == s.id)
            .where(Source.group_id == group["id"])
        ).first()
        if source_table_row is not None:
            group["active"] = source_table_row.active
            group["requested"] = source_table_row.requested
            group["saved_at"] = source_table_row.saved_at
            group["saved_by"] = (
                source_table_row.saved_by.to_dict()
                if source_table_row.saved_by is not None
                else None
            )
    if include_color_mag:
        source_info["color_magnitude"] = get_color_mag(source_info["annotations"])

    source_info = recursive_to_dict(source_info)
    return source_info


def create_annotations_query(
    session,
    annotations_filter_origin=None,
    annotations_filter_before=None,
    annotations_filter_after=None,
):

    annotations_query = Annotation.select(session.user_or_token)
    if annotations_filter_origin is not None:
        annotations_query = annotations_query.where(
            Annotation.origin.in_(annotations_filter_origin)
        )
    if annotations_filter_before:
        annotations_query = annotations_query.where(
            Annotation.created_at <= annotations_filter_before
        )
    if annotations_filter_after:
        annotations_query = annotations_query.where(
            Annotation.created_at >= annotations_filter_after
        )

    return annotations_query


def get_sources(
    user_id,
    session,
    include_thumbnails=False,
    include_comments=False,
    include_photometry_exists=False,
    include_spectrum_exists=False,
    include_period_exists=False,
    include_detection_stats=False,
    is_token_request=False,
    include_requested=False,
    requested_only=False,
    include_color_mag=False,
    remove_nested=False,
    first_detected_date=None,
    last_detected_date=None,
    has_tns_name=False,
    has_spectrum=False,
    has_followup_request=False,
    sourceID=None,
    ra=None,
    dec=None,
    radius=None,
    has_spectrum_before=None,
    has_spectrum_after=None,
    followup_request_status=None,
    saved_before=None,
    saved_after=None,
    created_or_modified_after=None,
    list_name=None,
    simbad_class=None,
    alias=None,
    origin=None,
    min_redshift=None,
    max_redshift=None,
    min_peak_magnitude=None,
    max_peak_magnitude=None,
    min_latest_magnitude=None,
    max_latest_magnitude=None,
    number_of_detections=None,
    classifications=None,
    nonclassifications=None,
    annotations_filter=None,
    annotations_filter_origin=None,
    annotations_filter_before=None,
    annotations_filter_after=None,
    comments_filter=None,
    comments_filter_author=None,
    comments_filter_before=None,
    comments_filter_after=None,
    localization_dateobs=None,
    localization_name=None,
    localization_cumprob=None,
    page_number=1,
    num_per_page=DEFAULT_SOURCES_PER_PAGE,
    sort_by=None,
    sort_order="asc",
    group_ids=None,
    user_accessible_group_ids=None,
    save_summary=False,
    total_matches=None,
    includeGeoJSON=False,
):
    """Query multiple sources from database.
    user_id : int
        SkyPortal ID of User posting the GcnEvent
    session: sqlalchemy.Session
        Database session for this transaction
    See Source Handler for optional arguments
    """

    user = session.scalar(sa.select(User).where(User.id == user_id))

    obj_query_options = []
    if include_thumbnails and not remove_nested:
        obj_query_options.append(joinedload(Obj.thumbnails))
    if include_detection_stats:
        obj_query_options.append(joinedload(Obj.photstats))

    if localization_dateobs is not None:
        obj_query = Obj.select(user, columns=[Obj.id])
    else:
        obj_query = Obj.select(user, options=obj_query_options)
    source_query = Source.select(user)

    if sourceID:
        obj_query = obj_query.where(
            func.lower(Obj.id).contains(func.lower(sourceID.strip()))
        )
    if any([ra, dec, radius]):
        if not all([ra, dec, radius]):
            raise ValueError(
                "If any of 'ra', 'dec' or 'radius' are "
                "provided, all three are required."
            )
        try:
            ra = float(ra)
            dec = float(dec)
            radius = float(radius)
        except ValueError:
            raise ValueError(
                "Invalid values for ra, dec or radius - could not convert to float"
            )
        other = ca.Point(ra=ra, dec=dec)
        obj_query = obj_query.where(Obj.within(other, radius))

    if first_detected_date:
        first_detected_date = arrow.get(first_detected_date).datetime
        photstat_subquery = (
            PhotStat.select(user)
            .where(PhotStat.first_detected_mjd >= Time(first_detected_date).mjd)
            .subquery()
        )
        obj_query = obj_query.join(
            photstat_subquery, Obj.id == photstat_subquery.c.obj_id
        )
    if last_detected_date:
        last_detected_date = arrow.get(last_detected_date).datetime
        photstat_subquery = (
            PhotStat.select(user)
            .where(PhotStat.last_detected_mjd <= Time(last_detected_date).mjd)
            .subquery()
        )
        obj_query = obj_query.join(
            photstat_subquery, Obj.id == photstat_subquery.c.obj_id
        )
    if number_of_detections:
        photstat_subquery = (
            PhotStat.select(user)
            .where(PhotStat.num_det_global >= number_of_detections)
            .subquery()
        )
        obj_query = obj_query.join(
            photstat_subquery, Obj.id == photstat_subquery.c.obj_id
        )
    if has_spectrum_after:
        try:
            has_spectrum_after = str(arrow.get(has_spectrum_after).datetime)
        except arrow.ParserError:
            raise arrow.ParserError(
                f"Invalid input for parameter hasSpectrumAfter:{has_spectrum_after}"
            )
        spectrum_subquery = (
            Spectrum.select(user)
            .where(Spectrum.observed_at >= has_spectrum_after)
            .subquery()
        )
        obj_query = obj_query.join(
            spectrum_subquery, Obj.id == spectrum_subquery.c.obj_id
        )
    if has_spectrum_before:
        try:
            has_spectrum_before = str(arrow.get(has_spectrum_before).datetime)
        except arrow.ParserError:
            raise arrow.ParserError(
                f"Invalid input for parameter hasSpectrumBefore:{has_spectrum_before}"
            )
        spectrum_subquery = (
            Spectrum.select(user)
            .where(Spectrum.observed_at <= has_spectrum_before)
            .subquery()
        )
        obj_query = obj_query.join(
            spectrum_subquery, Obj.id == spectrum_subquery.c.obj_id
        )
    if saved_before:
        source_query = source_query.where(Source.saved_at <= saved_before)
    if saved_after:
        source_query = source_query.where(Source.saved_at >= saved_after)
    if created_or_modified_after:
        try:
            created_or_modified_date = str(
                arrow.get(created_or_modified_after).datetime
            )
        except arrow.ParserError:
            raise arrow.ParserError("Invalid value provided for createdOrModifiedAfter")
        obj_query = obj_query.where(
            or_(
                Obj.created_at > created_or_modified_date,
                Obj.modified > created_or_modified_date,
            )
        )
    if list_name:
        listing_subquery = (
            Listing.select(user)
            .where(Listing.list_name == list_name)
            .where(Listing.user_id == user.id)
            .subquery()
        )
        obj_query = obj_query.join(
            listing_subquery, Obj.id == listing_subquery.c.obj_id
        )
    if simbad_class:
        obj_query = obj_query.where(
            func.lower(Obj.altdata['simbad']['class'].astext) == simbad_class.lower()
        )
    if alias is not None:
        obj_query = obj_query.where(Obj.alias.any(alias.strip()))
    if origin is not None:
        obj_query = obj_query.where(Obj.origin.contains(origin.strip()))
    if has_tns_name:
        obj_query = obj_query.where(Obj.altdata['tns']['name'].isnot(None))
    if has_spectrum:
        spectrum_subquery = Spectrum.select(user).subquery()
        obj_query = obj_query.join(
            spectrum_subquery, Obj.id == spectrum_subquery.c.obj_id
        )
    if has_followup_request:
        followup_request = FollowupRequest.select(user)
        if followup_request_status:
            followup_request = followup_request.where(
                FollowupRequest.status.contains(followup_request_status.strip())
            )
        followup_request_subquery = followup_request.subquery()
        obj_query = obj_query.join(
            followup_request_subquery, Obj.id == followup_request_subquery.c.obj_id
        )
    if min_redshift is not None:
        try:
            min_redshift = float(min_redshift)
        except ValueError:
            raise ValueError(
                "Invalid values for minRedshift - could not convert to float"
            )
        obj_query = obj_query.where(Obj.redshift >= min_redshift)
    if max_redshift is not None:
        try:
            max_redshift = float(max_redshift)
        except ValueError:
            raise ValueError(
                "Invalid values for maxRedshift - could not convert to float"
            )
        obj_query = obj_query.where(Obj.redshift <= max_redshift)

    if min_peak_magnitude is not None:
        try:
            min_peak_magnitude = float(min_peak_magnitude)
        except ValueError:
            raise ValueError(
                "Invalid values for minPeakMagnitude - could not convert to float"
            )
        min_peak_magnitude_subquery = (
            PhotStat.select(user)
            .where(PhotStat.peak_mag_global <= min_peak_magnitude)
            .subquery()
        )
        obj_query = obj_query.join(
            min_peak_magnitude_subquery, Obj.id == min_peak_magnitude_subquery.c.obj_id
        )
    if max_peak_magnitude is not None:
        try:
            max_peak_magnitude = float(max_peak_magnitude)
        except ValueError:
            raise ValueError(
                "Invalid values for maxPeakMagnitude - could not convert to float"
            )
        max_peak_magnitude_subquery = (
            PhotStat.select(user)
            .where(PhotStat.peak_mag_global >= max_peak_magnitude)
            .subquery()
        )
        obj_query = obj_query.join(
            max_peak_magnitude_subquery, Obj.id == max_peak_magnitude_subquery.c.obj_id
        )
    if min_latest_magnitude is not None:
        try:
            min_latest_magnitude = float(min_latest_magnitude)
        except ValueError:
            raise ValueError(
                "Invalid values for minLatestMagnitude - could not convert to float"
            )
        min_latest_magnitude_subquery = (
            PhotStat.select(user)
            .where(PhotStat.last_detected_mag <= min_latest_magnitude)
            .subquery()
        )
        obj_query = obj_query.join(
            min_latest_magnitude_subquery,
            Obj.id == min_latest_magnitude_subquery.c.obj_id,
        )

    if max_latest_magnitude is not None:
        try:
            max_latest_magnitude = float(max_latest_magnitude)
        except ValueError:
            raise ValueError(
                "Invalid values for maxLatestMagnitude - could not convert to float"
            )
        max_latest_magnitude_subquery = (
            PhotStat.select(user)
            .where(PhotStat.last_detected_mag >= max_latest_magnitude)
            .subquery()
        )
        obj_query = obj_query.join(
            max_latest_magnitude_subquery,
            Obj.id == max_latest_magnitude_subquery.c.obj_id,
        )
    if classifications is not None or sort_by == "classification":
        if classifications is not None:
            if isinstance(classifications, str) and "," in classifications:
                classifications = [c.strip() for c in classifications.split(",")]
            elif isinstance(classifications, str):
                classifications = [classifications]
            else:
                raise ValueError(
                    "Invalid classifications value -- must provide at least one string value"
                )
            taxonomy_names, classifications = list(
                zip(
                    *list(
                        map(
                            lambda c: (
                                c.split(":")[0].strip(),
                                c.split(":")[1].strip(),
                            ),
                            classifications,
                        )
                    )
                )
            )
            classification_accessible_query = Classification.select(user).subquery()

            classification_query = (
                session.query(
                    distinct(Classification.obj_id).label("obj_id"),
                    Classification.classification,
                )
                .join(Taxonomy)
                .where(Classification.classification.in_(classifications))
                .where(Taxonomy.name.in_(taxonomy_names))
            )
            classification_subquery = classification_query.subquery()

            # We join in the classifications being filtered for first before
            # the filter for accessible classifications to speed up the query
            # (this way seems to help the query planner come to more optimal join
            # strategies)
            obj_query = obj_query.join(
                classification_subquery,
                Obj.id == classification_subquery.c.obj_id,
            )
            obj_query = obj_query.join(
                classification_accessible_query,
                Obj.id == classification_accessible_query.c.obj_id,
            )

        else:
            # Not filtering on classifications, but ordering on them
            classification_query = Classification.select(user)
            classification_subquery = classification_query.subquery()

            # We need an outer join here when just sorting by classifications
            # to support sources with no classifications being sorted to the end
            obj_query = obj_query.join(
                classification_subquery,
                Obj.id == classification_subquery.c.obj_id,
                isouter=True,
            )
    if nonclassifications is not None:
        if isinstance(nonclassifications, str) and "," in nonclassifications:
            nonclassifications = [c.strip() for c in nonclassifications.split(",")]
        elif isinstance(nonclassifications, str):
            nonclassifications = [nonclassifications]
        else:
            raise ValueError(
                "Invalid non-classifications value -- must provide at least one string value"
            )
        taxonomy_names, nonclassifications = list(
            zip(
                *list(
                    map(
                        lambda c: (
                            c.split(":")[0].strip(),
                            c.split(":")[1].strip(),
                        ),
                        nonclassifications,
                    )
                )
            )
        )
        classification_accessible_subquery = Classification.select(user).subquery()

        nonclassification_query = (
            session.query(
                distinct(Classification.obj_id).label("obj_id"),
                Classification.classification,
            )
            .join(Taxonomy)
            .where(Classification.classification.in_(nonclassifications))
            .where(Taxonomy.name.in_(taxonomy_names))
        )
        nonclassification_subquery = nonclassification_query.subquery()

        # We join in the nonclassifications being filtered for first before
        # the filter for accessible classifications to speed up the query
        # (this way seems to help the query planner come to more optimal join
        # strategies)
        obj_query = obj_query.join(
            nonclassification_subquery,
            Obj.id != nonclassification_subquery.c.obj_id,
        )
        obj_query = obj_query.join(
            classification_accessible_subquery,
            Obj.id == classification_accessible_subquery.c.obj_id,
        )
    if annotations_filter is not None:
        if isinstance(annotations_filter, str) and "," in annotations_filter:
            annotations_filter = [c.strip() for c in annotations_filter.split(",")]
        elif isinstance(annotations_filter, str):
            annotations_filter = [annotations_filter]
        else:
            raise ValueError(
                "Invalid annotationsFilter value -- must provide at least one string value"
            )
    if annotations_filter_origin is not None:
        if (
            isinstance(annotations_filter_origin, str)
            and "," in annotations_filter_origin
        ):
            annotations_filter_origin = [
                c.strip() for c in annotations_filter_origin.split(",")
            ]
        elif isinstance(annotations_filter_origin, str):
            annotations_filter_origin = [annotations_filter_origin]
        else:
            raise ValueError(
                "Invalid annotationsFilterOrigin value -- must provide at least one string value"
            )

    if (
        (annotations_filter_origin is not None)
        or (annotations_filter_before is not None)
        or (annotations_filter_after is not None)
        or (annotations_filter is not None)
    ):
        if annotations_filter is not None:
            for ann_filt in annotations_filter:
                ann_split = ann_filt.split(":")
                if not (len(ann_split) == 1 or len(ann_split) == 3):
                    raise ValueError(
                        "Invalid annotationsFilter value -- annotation filter must have 1 or 3 values"
                    )
                name = ann_split[0].strip()

                annotations_query = create_annotations_query(
                    session,
                    annotations_filter_origin=annotations_filter_origin,
                    annotations_filter_before=annotations_filter_before,
                    annotations_filter_after=annotations_filter_after,
                )

                if len(ann_split) == 3:
                    value = ann_split[1].strip()
                    try:
                        value = float(value)
                    except ValueError as e:
                        raise ValueError(f"Invalid annotation filter value: {e}")
                    op = ann_split[2].strip()
                    op_options = ["lt", "le", "eq", "ne", "ge", "gt"]
                    if op not in op_options:
                        raise ValueError(f"Invalid operator: {op}")
                    comp_function = getattr(operator, op)

                    annotations_query = annotations_query.where(
                        comp_function(Annotation.data[name], cast(value, JSONB))
                    )
                else:
                    annotations_query = annotations_query.where(
                        Annotation.data[name].astext.is_not(None)
                    )

                annotations_subquery = annotations_query.subquery()
                obj_query = obj_query.join(
                    annotations_subquery,
                    Obj.id == annotations_subquery.c.obj_id,
                )
        else:
            annotations_query = create_annotations_query(
                session,
                annotations_filter_origin=annotations_filter_origin,
                annotations_filter_before=annotations_filter_before,
                annotations_filter_after=annotations_filter_after,
            )
            annotations_subquery = annotations_query.subquery()
            obj_query = obj_query.join(
                annotations_subquery,
                Obj.id == annotations_subquery.c.obj_id,
            )

    if (
        (comments_filter is not None)
        or comments_filter_before
        or comments_filter_after
        or (comments_filter_author is not None)
    ):

        comment_query = Comment.select(session.user_or_token)

        if comments_filter is not None:
            if isinstance(comments_filter, str) and "," in comments_filter:
                comments_filter = [c.strip() for c in comments_filter.split(",")]
            elif isinstance(comments_filter, str):
                comments_filter = [comments_filter]
            else:
                raise ValueError(
                    "Invalid commentsFilter value -- must provide at least one string value"
                )
            comment_query = comment_query.where(Comment.text.in_(comments_filter))

        if comments_filter_before:
            comment_query = comment_query.where(
                Comment.created_at <= comments_filter_before
            )

        if comments_filter_after:
            comment_query = comment_query.where(
                Comment.created_at >= comments_filter_after
            )

        if comments_filter_author is not None:
            if (
                isinstance(comments_filter_author, str)
                and "," in comments_filter_author
            ):
                comments_filter_author = [
                    c.strip() for c in comments_filter_author.split(",")
                ]
            elif isinstance(comments_filter_author, str):
                comments_filter_author = [comments_filter_author]
            else:
                raise ValueError(
                    "Invalid commentsFilterAuthor value -- must provide at least one string value"
                )

            author_query = User.select(session.user_or_token).where(
                User.username.in_(comments_filter_author)
            )
            author_subquery = author_query.subquery()

            comment_query = comment_query.join(
                author_subquery,
                Comment.author_id == author_subquery.c.id,
            )
        comment_subquery = comment_query.subquery()
        obj_query = obj_query.join(
            comment_subquery,
            Obj.id == comment_subquery.c.obj_id,
        )

    if localization_dateobs is not None:

        # This grabs just the IDs so the more expensive localization in-out
        # check is done on only this subset
        obj_ids = session.scalars(obj_query).all()

        if len(obj_ids) > MAX_LOCALIZATION_SOURCES:
            raise ValueError('Need fewer sources for efficient cross-match.')

        obj_query = Obj.select(user, options=obj_query_options).where(
            Obj.id.in_(obj_ids)
        )

        if localization_name is None:
            localization = session.scalars(
                Localization.select(
                    user,
                )
                .where(Localization.dateobs == localization_dateobs)
                .order_by(Localization.created_at.desc())
            ).first()
        else:
            localization = session.scalars(
                Localization.select(
                    user,
                )
                .where(Localization.dateobs == localization_dateobs)
                .where(Localization.localization_name == localization_name)
                .order_by(Localization.modified.desc())
            ).first()
        if localization is None:
            if localization_name is not None:
                raise ValueError(
                    f"Localization {localization_dateobs} with name {localization_name} not found",
                )
            else:
                raise ValueError(
                    f"Localization {localization_dateobs} not found",
                )

        cum_prob = (
            sa.func.sum(LocalizationTile.probdensity * LocalizationTile.healpix.area)
            .over(order_by=LocalizationTile.probdensity.desc())
            .label('cum_prob')
        )
        localizationtile_subquery = (
            sa.select(LocalizationTile.probdensity, cum_prob).filter(
                LocalizationTile.localization_id == localization.id
            )
        ).subquery()

        min_probdensity = (
            sa.select(
                sa.func.min(localizationtile_subquery.columns.probdensity)
            ).filter(localizationtile_subquery.columns.cum_prob <= localization_cumprob)
        ).scalar_subquery()

        tile_ids = session.scalars(
            sa.select(LocalizationTile.id).where(
                LocalizationTile.localization_id == localization.id,
                LocalizationTile.probdensity >= min_probdensity,
            )
        ).all()

        tiles_subquery = (
            sa.select(Obj.id)
            .filter(
                LocalizationTile.id.in_(tile_ids),
                LocalizationTile.healpix.contains(Obj.healpix),
            )
            .subquery()
        )

        obj_query = obj_query.join(
            tiles_subquery,
            Obj.id == tiles_subquery.c.id,
        )

    source_query = apply_active_or_requested_filtering(
        source_query, include_requested, requested_only
    )
    if group_ids is not None:
        if not all(gid in user_accessible_group_ids for gid in group_ids):
            raise ValueError(
                f"One of the requested groups in '{group_ids}' is inaccessible to user."
            )
        source_query = source_query.filter(Source.group_id.in_(group_ids))

    source_subquery = source_query.subquery()
    query = obj_query.join(source_subquery, Obj.id == source_subquery.c.obj_id)

    order_by = None
    if sort_by is not None:
        if sort_by == "id":
            order_by = [Obj.id] if sort_order == "asc" else [Obj.id.desc()]
        elif sort_by == "alias":
            order_by = (
                [Obj.alias.nullslast()]
                if sort_order == "asc"
                else [Obj.alias.desc().nullslast()]
            )
        elif sort_by == "origin":
            order_by = (
                [Obj.origin.nullslast()]
                if sort_order == "asc"
                else [Obj.origin.desc().nullslast()]
            )
        elif sort_by == "ra":
            order_by = (
                [Obj.ra.nullslast()]
                if sort_order == "asc"
                else [Obj.ra.desc().nullslast()]
            )
        elif sort_by == "dec":
            order_by = (
                [Obj.dec.nullslast()]
                if sort_order == "asc"
                else [Obj.dec.desc().nullslast()]
            )
        elif sort_by == "redshift":
            order_by = (
                [Obj.redshift.nullslast()]
                if sort_order == "asc"
                else [Obj.redshift.desc().nullslast()]
            )
        elif sort_by == "saved_at":
            order_by = (
                [source_subquery.c.saved_at]
                if sort_order == "asc"
                else [source_subquery.c.saved_at.desc()]
            )
        elif sort_by == "classification":
            order_by = (
                [classification_subquery.c.classification.nullslast()]
                if sort_order == "asc"
                else [classification_subquery.c.classification.desc().nullslast()]
            )

    try:
        page_number = max(int(page_number), 1)
    except ValueError:
        raise ValueError("Invalid page number value.")
    if save_summary:
        query_results = paginate_summary_query(
            session,
            source_query,
            page_number,
            num_per_page,
            total_matches,
        )
    else:
        try:
            query_results = grab_query_results(
                session,
                query,
                total_matches,
                page_number,
                num_per_page,
                "sources",
                order_by=order_by,
                # We'll join thumbnails in manually, as they lead to duplicate
                # results downstream with the detection stats being added in
                include_thumbnails=False,
                # include detection stats here as it is a query column,
                include_detection_stats=include_detection_stats,
                current_user=user,
            )
        except ValueError as e:
            if "Page number out of range" in str(e):
                raise ValueError("Page number out of range.")
            raise

        # Records are Objs, not Sources
        obj_list = []

        for result in query_results["sources"]:
            (obj,) = result
            obj_list.append(obj.to_dict())

            if include_comments:
                obj_list[-1]["comments"] = sorted(
                    (
                        {
                            k: v
                            for k, v in c.to_dict().items()
                            if k != "attachment_bytes"
                        }
                        for c in session.scalars(
                            Comment.select(session.user_or_token).where(
                                Comment.obj_id == obj.id
                            )
                        ).all()
                    ),
                    key=lambda x: x["created_at"],
                    reverse=True,
                )

            if include_thumbnails and not remove_nested:
                obj_list[-1]["thumbnails"] = session.scalars(
                    Thumbnail.select(session.user_or_token).where(
                        Thumbnail.obj_id == obj.id
                    )
                ).all()

            if not remove_nested:
                readable_classifications = (
                    session.scalars(
                        Classification.select(session.user_or_token).where(
                            Classification.obj_id == obj.id
                        )
                    )
                    .unique()
                    .all()
                )

                readable_classifications_json = []
                for classification in readable_classifications:
                    classification_dict = classification.to_dict()
                    classification_dict['groups'] = [
                        g.to_dict() for g in classification.groups
                    ]
                    readable_classifications_json.append(classification_dict)

                obj_list[-1]["classifications"] = readable_classifications_json

                obj_list[-1]["annotations"] = sorted(
                    session.scalars(
                        Annotation.select(session.user_or_token).where(
                            Annotation.obj_id == obj.id
                        )
                    )
                    .unique()
                    .all(),
                    key=lambda x: x.origin,
                )

            obj_list[-1]["gal_lon"] = obj.gal_lon_deg
            obj_list[-1]["gal_lat"] = obj.gal_lat_deg
            obj_list[-1]["luminosity_distance"] = obj.luminosity_distance
            obj_list[-1]["dm"] = obj.dm
            obj_list[-1]["angular_diameter_distance"] = obj.angular_diameter_distance

            if include_photometry_exists:
                stmt = Photometry.select(session.user_or_token).where(
                    Photometry.obj_id == obj.id
                )
                count_stmt = sa.select(func.count()).select_from(stmt.distinct())
                total_phot = session.execute(count_stmt).scalar()
                obj_list[-1]["photometry_exists"] = total_phot > 0
            if include_spectrum_exists:
                stmt = Spectrum.select(session.user_or_token).where(
                    Spectrum.obj_id == obj.id
                )
                count_stmt = sa.select(func.count()).select_from(stmt.distinct())
                total_spectrum = session.execute(count_stmt).scalar()
                obj_list[-1]["spectrum_exists"] = total_spectrum > 0
            if include_period_exists:
                annotations = (
                    session.scalars(
                        Annotation.select(session.user_or_token).where(
                            Annotation.obj_id == obj.id
                        )
                    )
                    .unique()
                    .all()
                )
                period_str_options = ['period', 'Period', 'PERIOD']
                obj_list[-1]["period_exists"] = any(
                    [
                        isinstance(an.data, dict) and 'period' in an.data
                        for an in annotations
                        for period_str in period_str_options
                    ]
                )
            if not remove_nested:
                source_query = Source.select(session.user_or_token).where(
                    Source.obj_id == obj_list[-1]["id"]
                )
                source_query = apply_active_or_requested_filtering(
                    source_query, include_requested, requested_only
                )
                source_subquery = source_query.subquery()
                groups = (
                    session.scalars(
                        Group.select(session.user_or_token).join(
                            source_subquery, Group.id == source_subquery.c.group_id
                        )
                    )
                    .unique()
                    .all()
                )
                obj_list[-1]["groups"] = [g.to_dict() for g in groups]

                for group in obj_list[-1]["groups"]:
                    source_table_row = session.scalars(
                        Source.select(session.user_or_token).where(
                            Source.obj_id == obj_list[-1]["id"],
                            Source.group_id == group["id"],
                        )
                    ).first()
                    if source_table_row is not None:
                        group["active"] = source_table_row.active
                        group["requested"] = source_table_row.requested
                        group["saved_at"] = source_table_row.saved_at
                        group["saved_by"] = (
                            source_table_row.saved_by.to_dict()
                            if source_table_row.saved_by is not None
                            else None
                        )

            if include_color_mag:
                obj_list[-1]["color_magnitude"] = get_color_mag(
                    obj_list[-1]["annotations"]
                )
        query_results["sources"] = obj_list

    query_results = recursive_to_dict(query_results)
    if includeGeoJSON:
        # features are JSON representations that the d3 stuff understands.
        # We use these to render the contours of the sky localization and
        # locations of the transients.

        features = []

        # useful for testing visualization
        # import numpy as np
        # for xx in np.arange(30, 180, 30):
        #   features.append(Feature(
        #       geometry=Point([float(xx), float(-30.0)]),
        #       properties={"name": "tmp"},
        #   ))

        for source in query_results["sources"]:
            point = Point((source["ra"], source["dec"]))
            aliases = [alias for alias in (source["alias"] or []) if alias]
            source_name = ", ".join(
                [
                    source["id"],
                ]
                + aliases
            )

            features.append(
                Feature(
                    geometry=point,
                    properties={
                        "name": source_name,
                        "url": f"/source/{source['id']}",
                    },
                )
            )

        query_results["geojson"] = {
            'type': 'FeatureCollection',
            'features': features,
        }

    return query_results


def post_source(data, user_id, session):
    """Post source to database.
    data: dict
        Source dictionary
    user_id : int
        SkyPortal ID of User posting the GcnEvent
    session: sqlalchemy.Session
        Database session for this transaction
    """

    user = session.scalar(sa.select(User).where(User.id == user_id))

    obj = session.scalars(Obj.select(user).where(Obj.id == data["id"])).first()
    if obj is None:
        obj_already_exists = False
    else:
        obj_already_exists = True
    schema = Obj.__schema__()

    ra = data.get('ra', None)
    dec = data.get('dec', None)

    if ((ra is None) or (dec is None)) and not obj_already_exists:
        raise AttributeError("RA/Declination must not be null for a new Obj")

    user_group_ids = [g.id for g in user.groups]
    user_accessible_group_ids = [g.id for g in user.accessible_groups]
    if not user_group_ids:
        raise AttributeError(
            "You must belong to one or more groups before you can add sources."
        )
    try:
        group_ids = [
            int(id)
            for id in data.pop('group_ids')
            if int(id) in user_accessible_group_ids
        ]
    except KeyError:
        group_ids = user_group_ids
    if not group_ids:
        raise AttributeError(
            "Invalid group_ids field. Please specify at least "
            "one valid group ID that you belong to."
        )

    if not obj_already_exists:
        try:
            obj = schema.load(data)
        except ValidationError as e:
            raise ValidationError(
                'Invalid/missing parameters: ' f'{e.normalized_messages()}'
            )
        session.add(obj)

    if (ra is not None) and (dec is not None):
        # This adds a healpix index for a new object being created
        obj.healpix = ha.constants.HPX.lonlat_to_healpix(ra * u.deg, dec * u.deg)

    groups = session.scalars(Group.select(user).where(Group.id.in_(group_ids))).all()
    if not groups:
        raise AttributeError(
            "Invalid group_ids field. Please specify at least "
            "one valid group ID that you belong to."
        )
    group_ids_loaded = [g.id for g in groups]
    if not set(group_ids_loaded) == set(group_ids):
        raise AttributeError('Not all group_ids could be loaded.')

    update_redshift_history_if_relevant(data, obj, user)

    for group in groups:
        source = session.scalars(
            Source.select(user)
            .where(Source.obj_id == obj.id)
            .where(Source.group_id == group.id)
        ).first()
        if source is not None:
            source.active = True
            source.saved_by = user
        else:
            session.add(Source(obj=obj, group=group, saved_by_id=user.id))
    session.commit()

    if not obj_already_exists:
        try:
            loop = IOLoop.current()
        except RuntimeError:
            loop = IOLoop(make_current=True).current()
        loop.run_in_executor(
            None,
            lambda: add_linked_thumbnails_and_push_ws_msg(obj.id, user_id),
        )
    else:
        flow = Flow()
        flow.push(
            '*', "skyportal/REFRESH_SOURCE", payload={"obj_key": obj.internal_key}
        )
        flow.push('*', "skyportal/REFRESH_CANDIDATE", payload={"id": obj.internal_key})

    return obj.id


def apply_active_or_requested_filtering(query, include_requested, requested_only):
    if include_requested:
        query = query.filter(or_(Source.requested.is_(True), Source.active.is_(True)))
    elif not requested_only:
        query = query.filter(Source.active.is_(True))
    if requested_only:
        query = query.filter(Source.active.is_(False)).filter(
            Source.requested.is_(True)
        )
    return query


def add_ps1_thumbnail_and_push_ws_msg(obj_id, user_id):
    with Session() as session:
        try:
            user = session.query(User).get(user_id)
            if Obj.get_if_accessible_by(obj_id, user) is None:
                raise AccessError(
                    f"Insufficient permissions for User {user_id} to read Obj {obj_id}"
                )
            obj = session.query(Obj).get(obj_id)
            obj.add_ps1_thumbnail(session=session)
            flow = Flow()
            flow.push(
                '*', "skyportal/REFRESH_SOURCE", payload={"obj_key": obj.internal_key}
            )
            flow.push(
                '*', "skyportal/REFRESH_CANDIDATE", payload={"id": obj.internal_key}
            )
        except Exception as e:
            log(f"Unable to generate PS1 thumbnail URL for {obj_id}: {e}")
            session.rollback()


def paginate_summary_query(session, query, page, num_per_page, total_matches):
    if total_matches is None:
        count_stmt = sa.select(func.count()).select_from(query.distinct())
        total_matches = session.execute(count_stmt).scalar()
    query = query.offset((page - 1) * num_per_page)
    query = query.limit(num_per_page)
    return {"sources": session.scalars(query).all(), "total_matches": total_matches}


class SourceHandler(BaseHandler):
    @auth_or_token
    def head(self, obj_id=None):
        """
        ---
        single:
          description: Check if a Source exists
          tags:
            - sources
          parameters:
            - in: path
              name: obj_id
              required: true
              schema:
                type: string
          responses:
            200:
              content:
                application/json:
                  schema: Success
            404:
              content:
                application/json:
                  schema: Error
        """

        with self.Session() as session:
            user_group_ids = [
                g.id for g in self.associated_user_object.accessible_groups
            ]
            query = (
                Source.select(session.user_or_token)
                .where(Source.obj_id == obj_id)
                .where(Source.group_id.in_(user_group_ids))
            )
            num_s = session.scalar(
                sa.select(func.count()).select_from(query.distinct())
            )
            if num_s > 0:
                return self.success()
            else:
                self.set_status(404)
                self.finish()

    @auth_or_token
    def get(self, obj_id=None):
        """
        ---
        single:
          description: Retrieve a source
          tags:
            - sources
          parameters:
            - in: path
              name: obj_id
              required: false
              schema:
                type: string
            - in: query
              name: includePhotometry
              nullable: true
              schema:
                type: boolean
              description: |
                Boolean indicating whether to include associated photometry. Defaults to
                false.
            - in: query
              name: includeComments
              nullable: true
              schema:
                type: boolean
              description: |
                Boolean indicating whether to include comment metadata in response.
                Defaults to false.
            - in: query
              name: includePhotometryExists
              nullable: true
              schema:
                type: boolean
              description: |
                Boolean indicating whether to return if a source has any photometry points. Defaults to false.
            - in: query
              name: includeSpectrumExists
              nullable: true
              schema:
                type: boolean
              description: |
                Boolean indicating whether to return if a source has a spectra. Defaults to false.
            - in: query
              name: includePeriodExists
              nullable: true
              schema:
                type: boolean
              description: |
                Boolean indicating whether to return if a source has a period set. Defaults to false.
            - in: query
              name: includeThumbnails
              nullable: true
              schema:
                type: boolean
              description: |
                Boolean indicating whether to include associated thumbnails. Defaults to false.
          responses:
            200:
              content:
                application/json:
                  schema: SingleObj
            400:
              content:
                application/json:
                  schema: Error
        multiple:
          description: Retrieve all sources
          tags:
            - sources
          parameters:
          - in: query
            name: ra
            nullable: true
            schema:
              type: number
            description: RA for spatial filtering (in decimal degrees)
          - in: query
            name: dec
            nullable: true
            schema:
              type: number
            description: Declination for spatial filtering (in decimal degrees)
          - in: query
            name: radius
            nullable: true
            schema:
              type: number
            description: Radius for spatial filtering if ra & dec are provided (in decimal degrees)
          - in: query
            name: sourceID
            nullable: true
            schema:
              type: string
            description: Portion of ID to filter on
          - in: query
            name: simbadClass
            nullable: true
            schema:
              type: string
            description: Simbad class to filter on
          - in: query
            name: alias
            nullable: true
            schema:
              type: array
              items:
                types: string
            description: additional name for the same object
          - in: query
            name: origin
            nullable: true
            schema:
              type: string
            description: who posted/discovered this source
          - in: query
            name: hasTNSname
            nullable: true
            schema:
              type: boolean
            description: If true, return only those matches with TNS names
          - in: query
            name: numPerPage
            nullable: true
            schema:
              type: integer
            description: |
              Number of sources to return per paginated request. Defaults to 100. Max 500.
          - in: query
            name: pageNumber
            nullable: true
            schema:
              type: integer
            description: Page number for paginated query results. Defaults to 1
          - in: query
            name: totalMatches
            nullable: true
            schema:
              type: integer
            description: |
              Used only in the case of paginating query results - if provided, this
              allows for avoiding a potentially expensive query.count() call.
          - in: query
            name: startDate
            nullable: true
            schema:
              type: string
            description: |
              Arrow-parseable date string (e.g. 2020-01-01). If provided, filter by
              PhotStat.first_detected_mjd >= startDate
          - in: query
            name: endDate
            nullable: true
            schema:
              type: string
            description: |
              Arrow-parseable date string (e.g. 2020-01-01). If provided, filter by
              PhotStat.last_detected_mjd <= endDate
          - in: query
            name: listName
            nullable: true
            schema:
              type: string
            description: |
              Get only sources saved to the querying user's list, e.g., "favorites".
          - in: query
            name: group_ids
            nullable: true
            schema:
              type: list
              items:
                type: integer
            description: |
               If provided, filter only sources saved to one of these group IDs.
          - in: query
            name: includeColorMagnitude
            nullable: true
            schema:
              type: boolean
            description: |
              Boolean indicating whether to include the color-magnitude data from Gaia.
              This will only include data for objects that have an annotation
              with the appropriate format: an annotation that contains a dictionary
              with keys named Mag_G, Mag_Bp, Mag_Rp, and Plx
              (underscores and case are ignored when matching all the above keys).
              The result is saved in a field named 'color_magnitude'.
              If no data is available, returns an empty array.
              Defaults to false (do not search for nor include this info).
          - in: query
            name: includeRequested
            nullable: true
            schema:
              type: boolean
            description: |
              Boolean indicating whether to include requested saves. Defaults to
              false.
          - in: query
            name: pendingOnly
            nullable: true
            schema:
              type: boolean
            description: |
              Boolean indicating whether to only include requested/pending saves.
              Defaults to false.
          - in: query
            name: savedBefore
            nullable: true
            schema:
              type: string
            description: |
              Only return sources that were saved before this UTC datetime.
          - in: query
            name: savedAfter
            nullable: true
            schema:
              type: string
            description: |
              Only return sources that were saved after this UTC datetime.
          - in: query
            name: hasSpectrumAfter
            nullable: true
            schema:
              type: string
            description: |
              Only return sources with a spectrum saved after this UTC datetime
          - in: query
            name: hasSpectrumBefore
            nullable: true
            schema:
              type: string
            description: |
              Only return sources with a spectrum saved before this UTC
              datetime
          - in: query
            name: saveSummary
            nullable: true
            schema:
              type: boolean
            description: |
              Boolean indicating whether to only return the source save
              information in the response (defaults to false). If true,
              the response will contain a list of dicts with the following
              schema under `response['data']['sources']`:
              ```
                  {
                    "group_id": 2,
                    "created_at": "2020-11-13T22:11:25.910271",
                    "saved_by_id": 1,
                    "saved_at": "2020-11-13T22:11:25.910271",
                    "requested": false,
                    "unsaved_at": null,
                    "modified": "2020-11-13T22:11:25.910271",
                    "obj_id": "16fil",
                    "active": true,
                    "unsaved_by_id": null
                  }
              ```
          - in: query
            name: sortBy
            nullable: true
            schema:
              type: string
            description: |
              The field to sort by. Currently allowed options are ["id", "ra", "dec", "redshift", "saved_at"]
          - in: query
            name: sortOrder
            nullable: true
            schema:
              type: string
            description: |
              The sort order - either "asc" or "desc". Defaults to "asc"
          - in: query
            name: includeComments
            nullable: true
            schema:
              type: boolean
            description: |
              Boolean indicating whether to include comment metadata in response.
              Defaults to false.
          - in: query
            name: includePhotometryExists
            nullable: true
            schema:
              type: boolean
            description: |
              Boolean indicating whether to return if a source has any photometry points. Defaults to false.
          - in: query
            name: includeSpectrumExists
            nullable: true
            schema:
              type: boolean
            description: |
              Boolean indicating whether to return if a source has a spectra. Defaults to false.
          - in: query
            name: removeNested
            nullable: true
            schema:
              type: boolean
            description: |
              Boolean indicating whether to remove nested output. Defaults to false.
          - in: query
            name: includeThumbnails
            nullable: true
            schema:
              type: boolean
            description: |
              Boolean indicating whether to include associated thumbnails. Defaults to false.
          - in: query
            name: includeDetectionStats
            nullable: true
            schema:
              type: boolean
            description: |
              Boolean indicating whether to include photometry detection statistics for each source
              (last detection and peak detection). Defaults to false.
          - in: query
            name: classifications
            nullable: true
            schema:
              type: array
              items:
                type: string
            explode: false
            style: simple
            description: |
              Comma-separated string of "taxonomy: classification" pair(s) to filter for sources matching
              that/those classification(s), i.e. "Sitewide Taxonomy: Type II, Sitewide Taxonomy: AGN"
          - in: query
            name: nonclassifications
            nullable: true
            schema:
              type: array
              items:
                type: string
            explode: false
            style: simple
            description: |
              Comma-separated string of "taxonomy: classification" pair(s) to filter for sources NOT matching
              that/those classification(s), i.e. "Sitewide Taxonomy: Type II, Sitewide Taxonomy: AGN"
          - in: query
            name: annotationsFilter
            nullable: true
            schema:
              type: array
              items:
                type: string
            explode: false
            style: simple
            description: |
              Comma-separated string of "annotation: value: operator" triplet(s) to filter for sources matching
              that/those annotation(s), i.e. "redshift: 0.5: lt"
          - in: query
            name: annotationsFilterOrigin
            nullable: true
            schema:
              type: string
            description: Comma separated string of origins. Only annotations from these origins are used when filtering with the annotationsFilter.
          - in: query
            name: annotationsFilterBefore
            nullable: true
            schema:
              type: string
            description: |
              Only return sources that have annotations before this UTC datetime.
          - in: query
            name: annotationsFilterAfter
            nullable: true
            schema:
              type: string
            description: |
              Only return sources that have annotations after this UTC datetime.
          - in: query
            name: commentsFilter
            nullable: true
            schema:
              type: array
              items:
                type: string
            explode: false
            style: simple
            description: |
              Comma-separated string of comment text to filter for sources matching.
          - in: query
            name: commentsFilterAuthor
            nullable: true
            schema:
              type: string
            description: Comma separated string of authors. Only comments from these authors are used when filtering with the commentsFilter.
          - in: query
            name: commentsFilterBefore
            nullable: true
            schema:
              type: string
            description: |
              Only return sources that have comments before this UTC datetime.
          - in: query
            name: commentsFilterAfter
            nullable: true
            schema:
              type: string
            description: |
              Only return sources that have comments after this UTC datetime.
          - in: query
            name: minRedshift
            nullable: true
            schema:
              type: number
            description: |
              If provided, return only sources with a redshift of at least this value
          - in: query
            name: maxRedshift
            nullable: true
            schema:
              type: number
            description: |
              If provided, return only sources with a redshift of at most this value
          - in: query
            name: minPeakMagnitude
            nullable: true
            schema:
              type: number
            description: |
              If provided, return only sources with a peak photometry magnitude of at least this value
          - in: query
            name: maxPeakMagnitude
            nullable: true
            schema:
              type: number
            description: |
              If provided, return only sources with a peak photometry magnitude of at most this value
          - in: query
            name: minLatestMagnitude
            nullable: true
            schema:
              type: number
            description: |
              If provided, return only sources whose latest photometry magnitude is at least this value
          - in: query
            name: maxLatestMagnitude
            nullable: true
            schema:
              type: number
            description: |
              If provided, return only sources whose latest photometry magnitude is at most this value
          - in: query
            name: numberDetections
            nullable: true
            schema:
              type: number
            description: |
              If provided, return only sources who have at least numberDetections detections.
          - in: query
            name: hasSpectrum
            nullable: true
            schema:
              type: boolean
            description: If true, return only those matches with at least one associated spectrum
          - in: query
            name: hasFollowupRequest
            nullable: true
            schema:
              type: boolean
            description: If true, return only those matches with at least one associated followup request
          - in: query
            name: followupRequestStatus
            nullable: true
            schema:
              type: string
            description: |
              If provided, string to match status of followup_request against
          - in: query
            name: createdOrModifiedAfter
            nullable: true
            schema:
              type: string
            description: |
              Arrow-parseable date-time string (e.g. 2020-01-01 or 2020-01-01T00:00:00 or 2020-01-01T00:00:00+00:00).
              If provided, filter by created_at or modified > createdOrModifiedAfter
          - in: query
            name: localizationDateobs
            schema:
              type: string
            description: |
                Event time in ISO 8601 format (`YYYY-MM-DDTHH:MM:SS.sss`).
                Each localization is associated with a specific GCNEvent by
                the date the event happened, and this date is used as a unique
                identifier. It can be therefore found as Localization.dateobs,
                queried from the /api/localization endpoint or dateobs in the
                GcnEvent page table.
          - in: query
            name: localizationName
            schema:
              type: string
            description: |
                Name of localization / skymap to use.
                Can be found in Localization.localization_name queried from
                /api/localization endpoint or skymap name in GcnEvent page
                table.
          - in: query
            name: localizationCumprob
            schema:
              type: number
            description: |
              Cumulative probability up to which to include sources
          - in: query
            name: includeGeoJSON
            nullable: true
            schema:
              type: boolean
            description: |
              Boolean indicating whether to include associated GeoJSON. Defaults to
              false.
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
                            type: object
                            properties:
                              sources:
                                type: array
                                items:
                                  $ref: '#/components/schemas/Obj'
                              totalMatches:
                                type: integer
                              pageNumber:
                                type: integer
                              numPerPage:
                                type: integer
            400:
              content:
                application/json:
                  schema: Error
        """

        start = time.time()

        page_number = self.get_query_argument('pageNumber', 1)
        num_per_page = min(
            int(self.get_query_argument("numPerPage", DEFAULT_SOURCES_PER_PAGE)),
            MAX_SOURCES_PER_PAGE,
        )
        ra = self.get_query_argument('ra', None)
        dec = self.get_query_argument('dec', None)
        radius = self.get_query_argument('radius', None)
        first_detected_date = self.get_query_argument('startDate', None)
        last_detected_date = self.get_query_argument('endDate', None)
        list_name = self.get_query_argument('listName', None)
        sourceID = self.get_query_argument('sourceID', None)  # Partial ID to match
        include_photometry = self.get_query_argument("includePhotometry", False)
        include_color_mag = self.get_query_argument("includeColorMagnitude", False)
        include_requested = self.get_query_argument("includeRequested", False)
        include_thumbnails = self.get_query_argument("includeThumbnails", False)
        requested_only = self.get_query_argument("pendingOnly", False)
        saved_after = self.get_query_argument('savedAfter', None)
        saved_before = self.get_query_argument('savedBefore', None)
        save_summary = self.get_query_argument('saveSummary', False)
        sort_by = self.get_query_argument("sortBy", None)
        sort_order = self.get_query_argument("sortOrder", "asc")
        include_comments = self.get_query_argument("includeComments", False)
        include_photometry_exists = self.get_query_argument(
            "includePhotometryExists", False
        )
        include_spectrum_exists = self.get_query_argument(
            "includeSpectrumExists", False
        )
        include_period_exists = self.get_query_argument("includePeriodExists", False)
        remove_nested = self.get_query_argument("removeNested", False)
        include_detection_stats = self.get_query_argument(
            "includeDetectionStats", False
        )
        classifications = self.get_query_argument("classifications", None)
        nonclassifications = self.get_query_argument("nonclassifications", None)
        annotations_filter = self.get_query_argument("annotationsFilter", None)
        annotations_filter_origin = self.get_query_argument(
            "annotationsFilterOrigin", None
        )
        annotations_filter_after = self.get_query_argument(
            'annotationsFilterAfter', None
        )
        annotations_filter_before = self.get_query_argument(
            'annotationsFilterBefore', None
        )
        comments_filter = self.get_query_argument("commentsFilter", None)
        comments_filter_author = self.get_query_argument("commentsFilterAuthor", None)
        comments_filter_after = self.get_query_argument('commentsFilterAfter', None)
        comments_filter_before = self.get_query_argument('commentsFilterBefore', None)
        min_redshift = self.get_query_argument("minRedshift", None)
        max_redshift = self.get_query_argument("maxRedshift", None)
        min_peak_magnitude = self.get_query_argument("minPeakMagnitude", None)
        max_peak_magnitude = self.get_query_argument("maxPeakMagnitude", None)
        min_latest_magnitude = self.get_query_argument("minLatestMagnitude", None)
        max_latest_magnitude = self.get_query_argument("maxLatestMagnitude", None)
        has_spectrum = self.get_query_argument("hasSpectrum", False)
        has_spectrum_after = self.get_query_argument("hasSpectrumAfter", None)
        has_spectrum_before = self.get_query_argument("hasSpectrumBefore", None)
        has_followup_request = self.get_query_argument("hasFollowupRequest", False)
        followup_request_status = self.get_query_argument("followupRequestStatus", None)

        created_or_modified_after = self.get_query_argument(
            "createdOrModifiedAfter", None
        )
        number_of_detections = self.get_query_argument("numberDetections", None)

        localization_dateobs = self.get_query_argument("localizationDateobs", None)
        localization_name = self.get_query_argument("localizationName", None)
        localization_cumprob = self.get_query_argument("localizationCumprob", 0.95)
        includeGeoJSON = self.get_query_argument("includeGeoJSON", False)

        class Validator(Schema):
            saved_after = UTCTZnaiveDateTime(required=False, missing=None)
            saved_before = UTCTZnaiveDateTime(required=False, missing=None)
            save_summary = fields.Boolean()
            remove_nested = fields.Boolean()
            include_thumbnails = fields.Boolean()
            first_detected_date = UTCTZnaiveDateTime(required=False, missing=None)
            last_detected_date = UTCTZnaiveDateTime(required=False, missing=None)
            has_spectrum_after = UTCTZnaiveDateTime(required=False, missing=None)
            has_spectrum_before = UTCTZnaiveDateTime(required=False, missing=None)
            created_or_modified_after = UTCTZnaiveDateTime(required=False, missing=None)

        validator_instance = Validator()
        params_to_be_validated = {}
        if saved_after is not None:
            params_to_be_validated['saved_after'] = saved_after
        if saved_before is not None:
            params_to_be_validated['saved_before'] = saved_before
        if save_summary is not None:
            params_to_be_validated['save_summary'] = save_summary
        if include_thumbnails is not None:
            params_to_be_validated['include_thumbnails'] = include_thumbnails
        if remove_nested is not None:
            params_to_be_validated['remove_nested'] = remove_nested
        if first_detected_date is not None:
            params_to_be_validated['first_detected_date'] = first_detected_date
        if last_detected_date is not None:
            params_to_be_validated['last_detected_date'] = last_detected_date
        if has_spectrum_after is not None:
            params_to_be_validated['has_spectrum_after'] = has_spectrum_after
        if has_spectrum_before is not None:
            params_to_be_validated['has_spectrum_before'] = has_spectrum_before
        if created_or_modified_after is not None:
            params_to_be_validated[
                'created_or_modified_after'
            ] = created_or_modified_after

        try:
            validated = validator_instance.load(params_to_be_validated)
        except ValidationError as e:
            return self.error(f'Error parsing query params: {e.args[0]}.')

        saved_after = validated['saved_after']
        saved_before = validated['saved_before']
        save_summary = validated['save_summary']
        remove_nested = validated['remove_nested']
        include_thumbnails = validated['include_thumbnails']
        first_detected_date = validated['first_detected_date']
        last_detected_date = validated['last_detected_date']
        has_spectrum_after = validated['has_spectrum_after']
        has_spectrum_before = validated['has_spectrum_before']
        created_or_modified_after = validated['created_or_modified_after']

        if localization_dateobs is not None or localization_name is not None:
            if first_detected_date is None or last_detected_date is None:
                return self.error(
                    'must specify startDate and endDate when filtering by localizationDateobs or localizationName'
                )
            if first_detected_date > last_detected_date:
                return self.error(
                    "startDate must be before endDate when filtering by localizationDateobs or localizationName",
                )
            if (
                last_detected_date - first_detected_date
            ).days > MAX_NUM_DAYS_USING_LOCALIZATION:
                return self.error(
                    "startDate and endDate must be less than a month apart when filtering by localizationDateobs or localizationName",
                )

        # parse the group ids:
        group_ids = self.get_query_argument('group_ids', None)
        if group_ids is not None:
            try:
                group_ids = [int(gid) for gid in group_ids.split(',')]
            except ValueError:
                return self.error(
                    f'Invalid group ids field ({group_ids}; Could not parse all elements to integers'
                )

        user_accessible_group_ids = [g.id for g in self.current_user.accessible_groups]

        simbad_class = self.get_query_argument('simbadClass', None)
        alias = self.get_query_argument('alias', None)
        origin = self.get_query_argument('origin', None)
        has_tns_name = self.get_query_argument('hasTNSname', None)
        total_matches = self.get_query_argument('totalMatches', None)
        is_token_request = isinstance(self.current_user, Token)

        if obj_id is not None:
            with self.Session() as session:
                try:
                    source_info = get_source(
                        obj_id,
                        self.associated_user_object.id,
                        session,
                        include_thumbnails=include_thumbnails,
                        include_comments=include_comments,
                        include_photometry=include_photometry,
                        include_photometry_exists=include_photometry_exists,
                        include_spectrum_exists=include_spectrum_exists,
                        include_period_exists=include_period_exists,
                        include_detection_stats=include_detection_stats,
                        is_token_request=is_token_request,
                        include_requested=include_requested,
                        requested_only=requested_only,
                        include_color_mag=include_color_mag,
                    )
                except Exception as e:
                    return self.error(f'Cannot retrieve source: {str(e)}')

                query_size = sizeof(source_info)
                if query_size >= SIZE_WARNING_THRESHOLD:
                    end = time.time()
                    duration = end - start
                    log(
                        f'User {self.associated_user_object.id} source query returned {query_size} bytes in {duration} seconds'
                    )

                return self.success(data=source_info)

        with self.Session() as session:
            try:
                query_results = get_sources(
                    self.associated_user_object.id,
                    session,
                    include_thumbnails=include_thumbnails,
                    include_comments=include_comments,
                    include_photometry_exists=include_photometry_exists,
                    include_spectrum_exists=include_spectrum_exists,
                    include_period_exists=include_period_exists,
                    include_detection_stats=include_detection_stats,
                    is_token_request=is_token_request,
                    include_requested=include_requested,
                    requested_only=requested_only,
                    include_color_mag=include_color_mag,
                    remove_nested=remove_nested,
                    first_detected_date=first_detected_date,
                    last_detected_date=last_detected_date,
                    sourceID=sourceID,
                    ra=ra,
                    dec=dec,
                    radius=radius,
                    has_spectrum_before=has_spectrum_before,
                    has_spectrum_after=has_spectrum_after,
                    saved_before=saved_before,
                    saved_after=saved_after,
                    created_or_modified_after=created_or_modified_after,
                    list_name=list_name,
                    simbad_class=simbad_class,
                    alias=alias,
                    origin=origin,
                    has_tns_name=has_tns_name,
                    has_spectrum=has_spectrum,
                    has_followup_request=has_followup_request,
                    followup_request_status=followup_request_status,
                    min_redshift=min_redshift,
                    max_redshift=max_redshift,
                    min_peak_magnitude=min_peak_magnitude,
                    max_peak_magnitude=max_peak_magnitude,
                    min_latest_magnitude=min_latest_magnitude,
                    max_latest_magnitude=max_latest_magnitude,
                    number_of_detections=number_of_detections,
                    classifications=classifications,
                    nonclassifications=nonclassifications,
                    annotations_filter=annotations_filter,
                    annotations_filter_origin=annotations_filter_origin,
                    annotations_filter_before=annotations_filter_before,
                    annotations_filter_after=annotations_filter_after,
                    comments_filter=comments_filter,
                    comments_filter_author=comments_filter_author,
                    comments_filter_before=comments_filter_before,
                    comments_filter_after=comments_filter_after,
                    localization_dateobs=localization_dateobs,
                    localization_name=localization_name,
                    localization_cumprob=localization_cumprob,
                    page_number=page_number,
                    num_per_page=num_per_page,
                    sort_by=sort_by,
                    sort_order=sort_order,
                    group_ids=group_ids,
                    user_accessible_group_ids=user_accessible_group_ids,
                    save_summary=save_summary,
                    total_matches=total_matches,
                    includeGeoJSON=includeGeoJSON,
                )
            except Exception as e:
                return self.error(f'Cannot retrieve sources: {str(e)}')

            query_size = sizeof(query_results)
            if query_size >= SIZE_WARNING_THRESHOLD:
                end = time.time()
                duration = end - start
                log(
                    f'User {self.associated_user_object.id} source query returned {query_size} bytes in {duration} seconds'
                )
            return self.success(data=query_results)

    @permissions(['Upload data'])
    def post(self):
        """
        ---
        description: Add a new source
        tags:
          - sources
        requestBody:
          content:
            application/json:
              schema:
                allOf:
                  - $ref: '#/components/schemas/ObjPost'
                  - type: object
                    properties:
                      group_ids:
                        type: array
                        items:
                          type: integer
                        description: |
                          List of associated group IDs. If not specified, all of the
                          user or token's groups will be used.
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
                          type: object
                          properties:
                            id:
                              type: string
                              description: New source ID
        """

        # Note that this POST method allows updating an object,
        # something usually reserved for PATCH/PUT. This is because
        # the user doing the POST may not have had access to the
        # object before (and therefore would have been unaware of its
        # existence).

        data = self.get_json()

        with self.Session() as session:
            obj_id = post_source(data, self.associated_user_object.id, session)
            return self.success(data={"id": obj_id})

    @permissions(['Upload data'])
    def patch(self, obj_id):
        """
        ---
        description: Update a source
        tags:
          - sources
        parameters:
          - in: path
            name: obj_id
            required: True
            schema:
              type: string
        requestBody:
          content:
            application/json:
              schema: ObjNoID
        responses:
          200:
            content:
              application/json:
                schema: Success
          400:
            content:
              application/json:
                schema: Error
        """
        data = self.get_json()
        data['id'] = obj_id

        schema = Obj.__schema__()
        try:
            obj = schema.load(data)
        except ValidationError as e:
            return self.error(
                'Invalid/missing parameters: ' f'{e.normalized_messages()}'
            )
        update_redshift_history_if_relevant(data, obj, self.associated_user_object)

        update_healpix_if_relevant(data, obj)

        self.verify_and_commit()
        self.push_all(
            action="skyportal/REFRESH_SOURCE",
            payload={"obj_key": obj.internal_key},
        )

        return self.success()

    @permissions(['Manage sources'])
    def delete(self, obj_id, group_id):
        """
        ---
        description: Delete a source
        tags:
          - sources
        parameters:
          - in: path
            name: obj_id
            required: true
            schema:
              type: string
          - in: path
            name: group_id
            required: true
            schema:
              type: string
        responses:
          200:
            content:
              application/json:
                schema: Success
        """

        with self.Session() as session:
            if group_id not in [g.id for g in self.current_user.accessible_groups]:
                return self.error("Inadequate permissions.")
            s = session.scalars(
                Source.select(self.current_user, mode="update")
                .where(Source.obj_id == obj_id)
                .where(Source.group_id == group_id)
            ).first()
            s.active = False
            s.unsaved_by = self.current_user
            session.commit()
            return self.success()


class SourceOffsetsHandler(BaseHandler):
    @auth_or_token
    async def get(self, obj_id):
        """
        ---
        description: Retrieve offset stars to aid in spectroscopy
        tags:
          - sources
        parameters:
        - in: path
          name: obj_id
          required: true
          schema:
            type: string
        - in: query
          name: facility
          nullable: true
          schema:
            type: string
            enum: [Keck, Shane, P200]
          description: Which facility to generate the starlist for
        - in: query
          name: num_offset_stars
          nullable: true
          schema:
            type: integer
            minimum: 0
            maximum: 10
          description: |
            Requested number of offset stars (set to zero to get starlist
            of just the source itself)
        - in: query
          name: obstime
          nullable: True
          schema:
            type: string
          description: |
            datetime of observation in isoformat (e.g. 2020-12-30T12:34:10)
        - in: query
          name: use_ztfref
          required: false
          schema:
            type: boolean
          description: |
            Use ZTFref catalog for offset star positions, otherwise Gaia DR3
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
                          type: object
                          properties:
                            facility:
                              type: string
                              enum: [Keck, Shane, P200]
                              description: Facility queried for starlist
                            starlist_str:
                              type: string
                              description: formatted starlist in facility format
                            starlist_info:
                              type: array
                              description: |
                                list of source and offset star information
                              items:
                                type: object
                                properties:
                                  str:
                                    type: string
                                    description: single-line starlist format per object
                                  ra:
                                    type: number
                                    format: float
                                    description: object RA in degrees (J2000)
                                  dec:
                                    type: number
                                    format: float
                                    description: object DEC in degrees (J2000)
                                  name:
                                    type: string
                                    description: object name
                                  dras:
                                    type: string
                                    description: offset from object to source in RA
                                  ddecs:
                                    type: string
                                    description: offset from object to source in DEC
                                  mag:
                                    type: number
                                    format: float
                                    description: |
                                      magnitude of object (from
                                      Gaia phot_rp_mean_mag)
                            ra:
                              type: number
                              format: float
                              description: source RA in degrees (J2000)
                            dec:
                              type: number
                              format: float
                              description: source DEC in degrees (J2000)
                            queries_issued:
                              type: integer
                              description: |
                                Number of times the catalog was queried to find
                                noffsets
                            noffsets:
                              type: integer
                              description: |
                                Number of suitable offset stars found (may be less)
                                than requested
                            query:
                              type: string
                              description: SQL query submitted to Gaia
          400:
            content:
              application/json:
                schema: Error
        """

        with self.Session() as session:

            source = session.scalars(
                Obj.select(session.user_or_token).where(Obj.id == obj_id)
            ).first()
            if source is None:
                return self.error('Source not found', status=404)

            initial_pos = (source.ra, source.dec)

            try:
                best_ra, best_dec = _calculate_best_position_for_offset_stars(
                    session.scalars(
                        Photometry.select(session.user_or_token).where(
                            Photometry.obj_id == source.id
                        )
                    ).all(),
                    fallback=(initial_pos[0], initial_pos[1]),
                    how="snr2",
                )
            except JSONDecodeError:
                self.push_notification(
                    'Source position using photometry points failed.'
                    ' Reverting to discovery position.'
                )
                best_ra, best_dec = initial_pos[0], initial_pos[1]

            facility = self.get_query_argument('facility', 'Keck')
            num_offset_stars = self.get_query_argument('num_offset_stars', '3')
            use_ztfref = self.get_query_argument('use_ztfref', True)

            obstime = self.get_query_argument(
                'obstime', datetime.datetime.utcnow().isoformat()
            )
            if not isinstance(isoparse(obstime), datetime.datetime):
                return self.error('obstime is not valid isoformat')

            if facility not in facility_parameters:
                return self.error('Invalid facility')

            radius_degrees = facility_parameters[facility]["radius_degrees"]
            mag_limit = facility_parameters[facility]["mag_limit"]
            min_sep_arcsec = facility_parameters[facility]["min_sep_arcsec"]
            mag_min = facility_parameters[facility]["mag_min"]

            try:
                num_offset_stars = int(num_offset_stars)
            except ValueError:
                # could not handle inputs
                return self.error('Invalid argument for `num_offset_stars`')

            offset_func = functools.partial(
                get_nearby_offset_stars,
                best_ra,
                best_dec,
                obj_id,
                how_many=num_offset_stars,
                radius_degrees=radius_degrees,
                mag_limit=mag_limit,
                min_sep_arcsec=min_sep_arcsec,
                starlist_type=facility,
                mag_min=mag_min,
                obstime=obstime,
                allowed_queries=2,
                use_ztfref=use_ztfref,
            )

            try:
                (
                    starlist_info,
                    query_string,
                    queries_issued,
                    noffsets,
                    used_ztfref,
                ) = await IOLoop.current().run_in_executor(None, offset_func)
            except ValueError:
                return self.error("Error querying for nearby offset stars")

            starlist_str = "\n".join(
                [x["str"].replace(" ", "&nbsp;") for x in starlist_info]
            )

            session.commit()
            return self.success(
                data={
                    'facility': facility,
                    'starlist_str': starlist_str,
                    'starlist_info': starlist_info,
                    'ra': source.ra,
                    'dec': source.dec,
                    'noffsets': noffsets,
                    'queries_issued': queries_issued,
                    'query': query_string,
                    'used_ztfref': used_ztfref,
                }
            )


class SourceFinderHandler(BaseHandler):
    @auth_or_token
    async def get(self, obj_id):
        """
        ---
        description: Generate a PDF/PNG finding chart to aid in spectroscopy
        tags:
          - sources
        parameters:
        - in: path
          name: obj_id
          required: true
          schema:
            type: string
        - in: query
          name: imsize
          schema:
            type: float
            minimum: 2
            maximum: 15
          description: Image size in arcmin (square)
        - in: query
          name: facility
          nullable: true
          schema:
            type: string
            enum: [Keck, Shane, P200]
        - in: query
          name: image_source
          nullable: true
          schema:
            type: string
            enum: [desi, dss, ztfref, ps1]
          description: |
             Source of the image used in the finding chart. Defaults to ps1
        - in: query
          name: use_ztfref
          required: false
          schema:
            type: boolean
          description: |
            Use ZTFref catalog for offset star positions, otherwise DR3
        - in: query
          name: obstime
          nullable: True
          schema:
            type: string
          description: |
            datetime of observation in isoformat (e.g. 2020-12-30T12:34:10)
        - in: query
          name: type
          nullable: true
          schema:
            type: string
            enum: [png, pdf]
          description: |
            output type
        - in: query
          name: num_offset_stars
          schema:
            type: integer
            minimum: 0
            maximum: 4
          description: |
            output desired number of offset stars [0,5] (default: 3)
        responses:
          200:
            description: A PDF/PNG finding chart file
            content:
              application/pdf:
                schema:
                  type: string
                  format: binary
              image/png:
                schema:
                  type: string
                  format: binary
          400:
            content:
              application/json:
                schema: Error
        """

        with self.Session() as session:
            source = session.scalars(
                Obj.select(session.user_or_token).where(Obj.id == obj_id)
            ).first()
            if source is None:
                return self.error('Source not found', status=404)

            output_type = self.get_query_argument('type', 'pdf')
            if output_type not in ["png", "pdf"]:
                return self.error(f'Invalid argument for `type`: {output_type}')

            imsize = self.get_query_argument('imsize', 4.0)
            try:
                imsize = float(imsize)
            except ValueError:
                # could not handle inputs
                return self.error('Invalid argument for `imsize`')

            if imsize < 2.0 or imsize > 15.0:
                return self.error(
                    'The value for `imsize` is outside the allowed range (2.0-15.0)'
                )

            initial_pos = (source.ra, source.dec)
            try:
                best_ra, best_dec = _calculate_best_position_for_offset_stars(
                    session.scalars(
                        Photometry.select(session.user_or_token).where(
                            Photometry.obj_id == source.id
                        )
                    ).all(),
                    fallback=(initial_pos[0], initial_pos[1]),
                    how="snr2",
                )
            except JSONDecodeError:
                self.push_notification(
                    'Source position using photometry points failed.'
                    ' Reverting to discovery position.'
                )
                best_ra, best_dec = initial_pos[0], initial_pos[1]

            facility = self.get_query_argument('facility', 'Keck')
            image_source = self.get_query_argument('image_source', 'ps1')
            use_ztfref = self.get_query_argument('use_ztfref', True)

            num_offset_stars = self.get_query_argument('num_offset_stars', '3')
            try:
                num_offset_stars = int(num_offset_stars)
            except ValueError:
                # could not handle inputs
                return self.error('Invalid argument for `num_offset_stars`')

            if not 0 <= num_offset_stars <= 4:
                return self.error(
                    'The value for `num_offset_stars` is outside the allowed range (0-4)'
                )

            obstime = self.get_query_argument(
                'obstime', datetime.datetime.utcnow().isoformat()
            )
            if not isinstance(isoparse(obstime), datetime.datetime):
                return self.error('obstime is not valid isoformat')

            if facility not in facility_parameters:
                return self.error('Invalid facility')

            if image_source not in source_image_parameters:
                return self.error('Invalid source image')

            radius_degrees = facility_parameters[facility]["radius_degrees"]
            mag_limit = facility_parameters[facility]["mag_limit"]
            min_sep_arcsec = facility_parameters[facility]["min_sep_arcsec"]
            mag_min = facility_parameters[facility]["mag_min"]

            finder = functools.partial(
                get_finding_chart,
                best_ra,
                best_dec,
                obj_id,
                image_source=image_source,
                output_format=output_type,
                imsize=imsize,
                how_many=num_offset_stars,
                radius_degrees=radius_degrees,
                mag_limit=mag_limit,
                mag_min=mag_min,
                min_sep_arcsec=min_sep_arcsec,
                starlist_type=facility,
                obstime=obstime,
                use_source_pos_in_starlist=True,
                allowed_queries=2,
                queries_issued=0,
                use_ztfref=use_ztfref,
            )

            self.push_notification(
                'Finding chart generation in progress. Download will start soon.'
            )
            rez = await IOLoop.current().run_in_executor(None, finder)

            filename = rez["name"]
            data = io.BytesIO(rez["data"])

            await self.send_file(data, filename, output_type=output_type)


class SourceNotificationHandler(BaseHandler):
    @permissions(["Upload data"])
    def post(self):
        """
        ---
        description: Send out a new source notification
        tags:
          - notifications
        requestBody:
          content:
            application/json:
              schema:
                type: object
                properties:
                  additionalNotes:
                    type: string
                    description: |
                      Notes to append to the message sent out
                  groupIds:
                    type: array
                    items:
                      type: integer
                    description: |
                      List of IDs of groups whose members should get the notification (if they've opted in)
                  sourceId:
                    type: string
                    description: |
                      The ID of the Source's Obj the notification is being sent about
                  level:
                    type: string
                    description: |
                      Either 'soft' or 'hard', determines whether to send an email or email+SMS notification
                required:
                  - groupIds
                  - sourceId
                  - level
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
                          type: object
                          properties:
                            id:
                              type: string
                              description: New SourceNotification ID
        """
        if not cfg["notifications.enabled"]:
            return self.error("Notifications are not enabled in current deployment.")
        data = self.get_json()

        additional_notes = data.get("additionalNotes")
        if isinstance(additional_notes, str):
            additional_notes = data["additionalNotes"].strip()
        else:
            if additional_notes is not None:
                return self.error(
                    "Invalid parameter `additionalNotes`: should be a string"
                )

        if data.get("groupIds") is None:
            return self.error("Missing required parameter `groupIds`")
        try:
            group_ids = [int(gid) for gid in data["groupIds"]]
        except ValueError:
            return self.error(
                "Invalid value provided for `groupIDs`; unable to parse "
                "all list items to integers."
            )

        if data.get("sourceId") is None:
            return self.error("Missing required parameter `sourceId`")

        with self.Session() as session:

            source = session.scalars(
                Obj.select(session.user_or_token).where(Obj.id == data["sourceId"])
            ).first()
            if source is None:
                return self.error('Source not found', status=404)

            source_id = data["sourceId"]

            source_group_ids = [
                row
                for row in session.scalars(
                    Source.select(
                        session.user_or_token, columns=[Source.group_id]
                    ).where(Source.obj_id == source_id)
                ).all()
            ]

            if bool(set(group_ids).difference(set(source_group_ids))):
                forbidden_groups = list(set(group_ids) - set(source_group_ids))
                return self.error(
                    "Insufficient recipient group access permissions. Not a member of "
                    f"group IDs: {forbidden_groups}."
                )

            if data.get("level") is None:
                return self.error("Missing required parameter `level`")
            if data["level"] not in ["soft", "hard"]:
                return self.error(
                    "Invalid value provided for `level`: should be either 'soft' or 'hard'"
                )
            level = data["level"]

            groups = session.scalars(
                Group.select(self.current_user).where(Group.id.in_(group_ids))
            ).all()
            if {g.id for g in groups} != set(group_ids):
                return self.error(
                    f'Cannot find one or more groups with IDs: {group_ids}.'
                )

            new_notification = SourceNotification(
                source_id=source_id,
                groups=groups,
                additional_notes=additional_notes,
                sent_by=self.associated_user_object,
                level=level,
            )
            session.add(new_notification)
            try:
                session.commit()
            except python_http_client.exceptions.UnauthorizedError:
                return self.error(
                    "Twilio Sendgrid authorization error. Please ensure "
                    "valid Sendgrid API key is set in server environment as "
                    "per their setup docs."
                )
            except TwilioException:
                return self.error(
                    "Twilio Communication SMS API authorization error. Please ensure "
                    "valid Twilio API key is set in server environment as "
                    "per their setup docs."
                )

            return self.success(data={'id': new_notification.id})


class PS1ThumbnailHandler(BaseHandler):
    @auth_or_token  # We should allow these requests from view-only users (triggered on source page)
    def post(self):
        data = self.get_json()
        obj_id = data.get("objID")
        if obj_id is None:
            return self.error("Missing required parameter objID")
        IOLoop.current().add_callback(
            lambda: add_ps1_thumbnail_and_push_ws_msg(
                obj_id, self.associated_user_object.id
            )
        )
        return self.success()
