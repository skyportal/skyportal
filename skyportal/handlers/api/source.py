import astropy
from astropy.coordinates import EarthLocation
from astropy.time import Time
from astroplan import (
    AirmassConstraint,
    AtNightConstraint,
    Observer,
    is_event_observable,
)
import datetime
from json.decoder import JSONDecodeError
import astropy.units as u
from geojson import Point, Feature
import python_http_client.exceptions
from twilio.base.exceptions import TwilioException
from tornado.ioloop import IOLoop
import io
from dateutil.parser import isoparse
import numpy as np
import pandas as pd
import sqlalchemy as sa
from sqlalchemy.orm import joinedload
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy import func, or_, distinct
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql.expression import cast
import arrow
from marshmallow import Schema, fields
from marshmallow.exceptions import ValidationError
from matplotlib import dates
import matplotlib.pyplot as plt
import operator  # noqa: F401
import functools
import conesearch_alchemy as ca
import healpix_alchemy as ha
import time

from ...utils.UTCTZnaiveDateTime import UTCTZnaiveDateTime
from ...utils.sizeof import sizeof, SIZE_WARNING_THRESHOLD
from ...utils.thumbnail import post_thumbnails

from baselayer.app.access import permissions, auth_or_token
from baselayer.app.env import load_env
from baselayer.app.model_util import recursive_to_dict
from baselayer.app.flow import Flow
from baselayer.log import make_log

from ..base import BaseHandler
from ...models import (
    Allocation,
    Annotation,
    Comment,
    GroupUser,
    Instrument,
    Obj,
    User,
    Source,
    Thumbnail,
    Token,
    Photometry,
    PhotometricSeries,
    Galaxy,
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
    ObjAnalysis,
    PhotStat,
    Spectrum,
    SourceLabel,
    SourceView,
    SourcesConfirmedInGCN,
    SpatialCatalog,
    SpatialCatalogEntry,
    SpatialCatalogEntryTile,
    Telescope,
    TNSRobot,
)
from ...utils.offset import (
    get_nearby_offset_stars,
    facility_parameters,
    source_image_parameters,
    get_finding_chart,
    _calculate_best_position_for_offset_stars,
)
from ...utils.tns import post_tns
from .candidate import (
    grab_query_results,
    update_redshift_history_if_relevant,
    update_summary_history_if_relevant,
    update_healpix_if_relevant,
)
from .photometry import serialize, add_external_photometry
from .color_mag import get_color_mag

DEFAULT_SOURCES_PER_PAGE = 100
MAX_SOURCES_PER_PAGE = 500
MAX_NUM_DAYS_USING_LOCALIZATION = 31
_, cfg = load_env()
log = make_log('api/source')

MAX_LOCALIZATION_SOURCES = 50000

Session = scoped_session(sessionmaker())


def check_if_obj_has_photometry(obj_id, user, session):
    """
    Check if an object has photometry that is
    accessible to the current user.
    This includes regular (individual point)
    photometry and also photometric series.

    Parameters
    ----------
    obj_id: str
        The ID of the object to check.
    user: baselayer.app.models.User
        The user to check.
    session: sqlalchemy.orm.session.Session
        The session to use to query the database.

    Returns
    -------
    bool
        True if the object has photometry that is accessible to the current user.
    """
    # Use columns=[] to avoid loading entire photometry objects
    # In the case of photometric series, that could include disk I/O
    phot = session.scalars(
        Photometry.select(user, columns=[Photometry.id]).where(
            Photometry.obj_id == obj_id
        )
    ).first()
    # only load the photometric series if there are no regular photometry points
    if phot is None:
        phot_series = session.scalars(
            PhotometricSeries.select(user, columns=[PhotometricSeries.id]).where(
                PhotometricSeries.obj_id == obj_id
            )
        ).first()
    else:
        phot_series = None

    return phot is not None or phot_series is not None


async def get_source(
    obj_id,
    user_id,
    session,
    include_thumbnails=False,
    include_comments=False,
    include_analyses=False,
    include_photometry=False,
    include_photometry_exists=False,
    include_spectrum_exists=False,
    include_comment_exists=False,
    include_period_exists=False,
    include_detection_stats=False,
    include_labellers=False,
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
    source_info["followup_requests"] = (
        session.scalars(
            FollowupRequest.select(
                user,
                options=[
                    joinedload(FollowupRequest.allocation).joinedload(
                        Allocation.instrument
                    ),
                    joinedload(FollowupRequest.allocation).joinedload(Allocation.group),
                    joinedload(FollowupRequest.requester),
                    joinedload(FollowupRequest.watchers),
                ],
            )
            .where(FollowupRequest.obj_id == obj_id)
            .where(FollowupRequest.status != "deleted")
        )
        .unique()
        .all()
    )
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
    galaxies = session.scalars(
        Galaxy.select(user).where(Galaxy.within(point, 10 / 3600))
    ).all()
    if len(galaxies) > 0:
        source_info["galaxies"] = list({galaxy.name for galaxy in galaxies})
    else:
        source_info["galaxies"] = None

    # Check for nearby galaxies (within 10 arcsecs)
    duplicate_objs = (
        Obj.select(user)
        .where(Obj.within(point, 4 / 3600))
        .where(Obj.id != s.id)
        .subquery()
    )
    duplicates = session.scalars(
        Source.select(user).join(duplicate_objs, Source.obj_id == duplicate_objs.c.id)
    ).all()
    if len(duplicates) > 0:
        source_info["duplicates"] = list({dup.obj_id for dup in duplicates})
    else:
        source_info["duplicates"] = None

    if 'photstats' in source_info:
        photstats = source_info["photstats"]
        for photstat in photstats:
            if (
                hasattr(photstat, 'first_detected_mjd')
                and photstat.first_detected_mjd is not None
            ):
                source_info["first_detected"] = Time(
                    photstat.first_detected_mjd, format='mjd'
                ).isot
            if (
                hasattr(photstat, 'last_detected_mjd')
                and photstat.last_detected_mjd is not None
            ):
                source_info["last_detected"] = Time(
                    photstat.last_detected_mjd, format='mjd'
                ).isot

    if s.host_id:
        source_info["host"] = s.host.to_dict()
        source_info["host_offset"] = s.host_offset.deg * 3600.0
        source_info["host_distance"] = s.host_distance.value

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
        thumbnails = list({"ps1", "ls", "sdss"} - set(existing_thumbnail_types))
        if len(thumbnails) > 0:
            post_thumbnails([obj_id])

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
    if include_analyses:
        analyses = (
            session.scalars(
                ObjAnalysis.select(
                    user,
                ).where(ObjAnalysis.obj_id == obj_id)
            )
            .unique()
            .all()
        )
        source_info["analyses"] = [analysis.to_dict() for analysis in analyses]
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
    if include_labellers:
        labels_subquery = (
            SourceLabel.select(session.user_or_token)
            .where(SourceLabel.obj_id == obj_id)
            .subquery()
        )

        users = (
            session.scalars(
                User.select(session.user_or_token).join(
                    labels_subquery,
                    User.id == labels_subquery.c.labeller_id,
                )
            )
            .unique()
            .all()
        )
        source_info["labellers"] = [user.to_dict() for user in users]

    annotations = sorted(
        session.scalars(
            Annotation.select(user)
            .options(joinedload(Annotation.author))
            .where(Annotation.obj_id == obj_id)
        )
        .unique()
        .all(),
        key=lambda x: x.origin,
    )
    source_info["annotations"] = [
        {**annotation.to_dict(), 'type': 'source'} for annotation in annotations
    ]
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
        classification_dict['votes'] = [g.to_dict() for g in classification.votes]
        readable_classifications_json.append(classification_dict)

    source_info["classifications"] = readable_classifications_json
    source_info["gal_lat"] = s.gal_lat_deg
    source_info["gal_lon"] = s.gal_lon_deg
    source_info["luminosity_distance"] = s.luminosity_distance
    source_info["dm"] = s.dm
    source_info["angular_diameter_distance"] = s.angular_diameter_distance
    source_info["ebv"] = s.ebv

    if include_photometry:
        photometry = (
            session.scalars(
                Photometry.select(
                    user, options=[joinedload(Photometry.annotations)]
                ).where(Photometry.obj_id == obj_id)
            )
            .unique()
            .all()
        )
        source_info["photometry"] = [
            serialize(phot, 'ab', 'flux') for phot in photometry
        ]
    if include_photometry_exists:
        source_info["photometry_exists"] = check_if_obj_has_photometry(
            obj_id, user, session
        )

    if include_spectrum_exists:
        source_info["spectrum_exists"] = (
            session.scalars(
                Spectrum.select(user).where(Spectrum.obj_id == obj_id)
            ).first()
            is not None
        )
    if include_comment_exists:
        source_info["comment_exists"] = (
            session.scalars(
                Comment.select(user).where(Comment.obj_id == obj_id)
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
        source_info["color_magnitude"] = get_color_mag(annotations)

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


async def get_sources(
    user_id,
    session,
    include_thumbnails=False,
    include_comments=False,
    include_photometry_exists=False,
    include_spectrum_exists=False,
    include_comment_exists=False,
    include_period_exists=False,
    include_detection_stats=False,
    include_labellers=False,
    include_hosts=False,
    exclude_forced_photometry=False,
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
    has_been_labelled=False,
    has_not_been_labelled=False,
    current_user_labeller=False,
    sourceID=None,
    rejectedSourceIDs=None,
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
    classifications_simul=False,
    nonclassifications=None,
    unclassified=False,
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
    localization_reject_sources=False,
    include_sources_in_gcn=False,
    spatial_catalog_name=None,
    spatial_catalog_entry_name=None,
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

    obj_query = Obj.select(user, columns=[Obj.id])
    source_query = Source.select(user)

    if sourceID:
        obj_query = obj_query.where(
            func.lower(Obj.id).contains(func.lower(sourceID.strip()))
        )
    if rejectedSourceIDs:
        obj_query = obj_query.where(Obj.id.notin_(rejectedSourceIDs))

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
        if exclude_forced_photometry:
            photstat_subquery = (
                PhotStat.select(user)
                .where(
                    PhotStat.first_detected_no_forced_phot_mjd
                    >= Time(first_detected_date).mjd
                )
                .subquery()
            )
        else:
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
        if exclude_forced_photometry:
            photstat_subquery = (
                PhotStat.select(user)
                .where(
                    PhotStat.last_detected_no_forced_phot_mjd
                    <= Time(last_detected_date).mjd
                )
                .subquery()
            )
        else:
            photstat_subquery = (
                PhotStat.select(user)
                .where(PhotStat.last_detected_mjd <= Time(last_detected_date).mjd)
                .subquery()
            )
        obj_query = obj_query.join(
            photstat_subquery, Obj.id == photstat_subquery.c.obj_id
        )
    if number_of_detections:
        if exclude_forced_photometry:
            photstat_subquery = (
                PhotStat.select(user)
                .where(PhotStat.num_det_no_forced_phot_global >= number_of_detections)
                .subquery()
            )
        else:
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
        obj_query = obj_query.where(Obj.tns_name.isnot(None))
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
    if has_been_labelled:
        labels_query = SourceLabel.select(session.user_or_token)
        if current_user_labeller:
            labels_query = labels_query.where(SourceLabel.labeller_id == user.id)
        labels_subquery = labels_query.subquery()
        obj_query = obj_query.join(labels_subquery, Obj.id == labels_subquery.c.obj_id)
    if has_not_been_labelled:
        labels_query = SourceLabel.select(
            session.user_or_token, columns=[SourceLabel.obj_id]
        )
        if current_user_labeller:
            labels_query = labels_query.where(SourceLabel.labeller_id == user.id)
        labels_subquery = labels_query.subquery()
        obj_query = obj_query.where(Obj.id.notin_(labels_subquery))

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
            classification_accessible_subquery = Classification.select(user).subquery()

            if classifications_simul:
                classification_id_query = Obj.select(
                    session.user_or_token, columns=[Obj.id]
                )
                for taxonomy_name, classification in zip(
                    taxonomy_names, classifications
                ):
                    classification_query = (
                        session.query(
                            distinct(Classification.obj_id).label("obj_id"),
                            Classification.classification,
                        )
                        .join(Taxonomy)
                        .where(Classification.classification == classification)
                        .where(Taxonomy.name == taxonomy_name)
                    )
                    classification_subquery = classification_query.subquery()

                    classification_id_query = classification_id_query.where(
                        Obj.id == classification_subquery.c.obj_id
                    )
                # We join in the classifications being filtered for first before
                # the filter for accessible classifications to speed up the query                                                                                               # (this way seems to help the query planner come to more optimal join
                # strategies)
                classification_id_query = classification_id_query.join(
                    classification_accessible_subquery,
                    Obj.id == classification_accessible_subquery.c.obj_id,
                )
                # classification_id_subquery = classification_id_query.subquery()
                classification_id_subquery = (
                    session.scalars(classification_id_query).unique().all()
                )

            else:
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

                classification_id_query = Obj.select(
                    session.user_or_token, columns=[Obj.id]
                ).where(Obj.id == classification_subquery.c.obj_id)
                # We join in the classifications being filtered for first before
                # the filter for accessible classifications to speed up the query
                # (this way seems to help the query planner come to more optimal join
                # strategies)
                classification_id_query = classification_id_query.join(
                    classification_accessible_subquery,
                    Obj.id == classification_accessible_subquery.c.obj_id,
                )
                # classification_id_subquery = classification_id_query.subquery()
                classification_id_subquery = (
                    session.scalars(classification_id_query).unique().all()
                )

            obj_query = obj_query.where(Obj.id.in_(classification_id_subquery))

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

        nonclassification_id_query = Obj.select(
            session.user_or_token, columns=[Obj.id]
        ).where(Obj.id == nonclassification_subquery.c.obj_id)
        # We join in the nonclassifications being filtered for first before
        # the filter for accessible classifications to speed up the query
        # (this way seems to help the query planner come to more optimal join
        # strategies)
        nonclassification_id_query = nonclassification_id_query.join(
            classification_accessible_subquery,
            Obj.id == classification_accessible_subquery.c.obj_id,
        )
        nonclassification_id_subquery = nonclassification_id_query.subquery()

        obj_query = obj_query.where(Obj.id.notin_(nonclassification_id_subquery))

    if unclassified:
        unclassified_subquery = (
            Classification.select(
                session.user_or_token, columns=[Classification.obj_id]
            )
            .where(Classification.ml.is_(False))
            .subquery()
        )
        obj_query = obj_query.where(Obj.id.notin_(unclassified_subquery))

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
        obj_ids = session.scalars(obj_query).unique().all()

        if len(obj_ids) > MAX_LOCALIZATION_SOURCES:
            raise ValueError('Need fewer sources for efficient cross-match.')

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

        partition_key = arrow.get(localization.dateobs).datetime
        localizationtile_partition_name = (
            f'{partition_key.year}_{partition_key.month:02d}'
        )
        localizationtilescls = LocalizationTile.partitions.get(
            localizationtile_partition_name, None
        )
        if localizationtilescls is None:
            localizationtilescls = LocalizationTile.partitions.get(
                'def', LocalizationTile
            )
        else:
            # check that there is actually a localizationTile with the given localization_id in the partition
            # if not, use the default partition
            if not (
                session.scalars(
                    localizationtilescls.select(session.user_or_token).where(
                        localizationtilescls.localization_id == localization.id
                    )
                ).first()
            ):
                localizationtilescls = LocalizationTile.partitions.get(
                    'def', LocalizationTile
                )

        cum_prob = (
            sa.func.sum(
                localizationtilescls.probdensity * localizationtilescls.healpix.area
            )
            .over(order_by=localizationtilescls.probdensity.desc())
            .label('cum_prob')
        )
        localizationtile_subquery = (
            sa.select(localizationtilescls.probdensity, cum_prob).filter(
                localizationtilescls.localization_id == localization.id
            )
        ).subquery()

        min_probdensity = (
            sa.select(
                sa.func.min(localizationtile_subquery.columns.probdensity)
            ).filter(localizationtile_subquery.columns.cum_prob <= localization_cumprob)
        ).scalar_subquery()

        tile_ids = session.scalars(
            sa.select(localizationtilescls.id).where(
                localizationtilescls.localization_id == localization.id,
                localizationtilescls.probdensity >= min_probdensity,
            )
        ).all()

        tiles_subquery = (
            sa.select(Obj.id)
            .filter(
                localizationtilescls.id.in_(tile_ids),
                localizationtilescls.healpix.contains(Obj.healpix),
            )
            .subquery()
        )

        obj_query = obj_query.join(
            tiles_subquery,
            Obj.id == tiles_subquery.c.id,
        )

        if localization_reject_sources:
            obj_rejection_query = sa.select(SourcesConfirmedInGCN.obj_id).where(
                SourcesConfirmedInGCN.dateobs == localization_dateobs,
                SourcesConfirmedInGCN.confirmed.is_(False),
            )

            # check is done on only this subset
            rejected_obj_ids = session.scalars(obj_rejection_query).all()

            obj_query = obj_query.where(Obj.id.notin_(rejected_obj_ids))

    if spatial_catalog_name is not None:

        if spatial_catalog_entry_name is None:
            raise ValueError(
                'spatial_catalog_entry_name must be defined if spatial_catalog_name is as well'
            )

        # This grabs just the IDs so the more expensive localization in-out
        # check is done on only this subset
        obj_ids = session.scalars(obj_query).all()

        if len(obj_ids) > MAX_LOCALIZATION_SOURCES:
            raise ValueError('Need fewer sources for efficient cross-match.')

        catalog = session.scalars(
            SpatialCatalog.select(
                user,
            ).where(SpatialCatalog.catalog_name == spatial_catalog_name)
        ).first()

        catalog_entry = session.scalars(
            SpatialCatalogEntry.select(
                user,
            )
            .where(SpatialCatalogEntry.entry_name == spatial_catalog_entry_name)
            .where(SpatialCatalogEntry.catalog_id == catalog.id)
        ).first()
        if catalog_entry is None:
            raise ValueError(
                f"Catalog entry {spatial_catalog_entry_name} from catalog {spatial_catalog_name} not found",
            )

        tile_ids = session.scalars(
            sa.select(SpatialCatalogEntryTile.id).where(
                SpatialCatalogEntryTile.entry_name == catalog_entry.entry_name,
            )
        ).all()

        tiles_subquery = (
            sa.select(Obj.id)
            .filter(
                SpatialCatalogEntryTile.id.in_(tile_ids),
                SpatialCatalogEntryTile.healpix.contains(Obj.healpix),
            )
            .subquery()
        )

        obj_query = obj_query.join(
            tiles_subquery,
            Obj.id == tiles_subquery.c.id,
        )

    if include_sources_in_gcn and localization_dateobs is not None:
        obj_include_query = sa.select(SourcesConfirmedInGCN.obj_id).where(
            SourcesConfirmedInGCN.dateobs == localization_dateobs,
            SourcesConfirmedInGCN.confirmed.is_not(False),
        )

        obj_ids = list(
            set(session.scalars(obj_query).unique().all()).union(
                set(session.scalars(obj_include_query).unique().all())
            )
        )

        obj_query = Obj.select(user, columns=[Obj.id]).where(Obj.id.in_(obj_ids))

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

    # order_by = None
    order_by = (
        [source_subquery.c.saved_at]
        if sort_order == "desc"
        else [source_subquery.c.saved_at.desc()]
    )

    if localization_dateobs is not None and sort_by is None:
        sort_by = "gcn_status"

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
        elif sort_by == "gcn_status" and localization_dateobs is not None:
            # For Ascending (Desc is the opposite)
            # 1. sources where there is no match
            # 2. sources where the confirmed column is true
            # 3. sources where the confirmed column is null
            # 4. sources where the confirmed column is false

            source_confirmed_in_gcn_subquery = (
                sa.select(
                    SourcesConfirmedInGCN.obj_id,
                    SourcesConfirmedInGCN.dateobs,
                    SourcesConfirmedInGCN.confirmed,
                )
                .where(
                    SourcesConfirmedInGCN.obj_id == source_subquery.c.obj_id,
                    SourcesConfirmedInGCN.dateobs == localization_dateobs,
                )
                .subquery()
            )

            query = query.outerjoin(
                source_confirmed_in_gcn_subquery,
                source_subquery.c.obj_id == source_confirmed_in_gcn_subquery.c.obj_id,
            )

            order_by = (
                [
                    source_confirmed_in_gcn_subquery.c.dateobs.is_not(None),
                    source_confirmed_in_gcn_subquery.c.confirmed.is_not(True),
                    source_confirmed_in_gcn_subquery.c.confirmed.is_not(None),
                    source_confirmed_in_gcn_subquery.c.confirmed.is_not(False),
                ]
                if sort_order == "asc"
                else [
                    source_confirmed_in_gcn_subquery.c.dateobs.is_(None),
                    source_confirmed_in_gcn_subquery.c.confirmed.is_not(False),
                    source_confirmed_in_gcn_subquery.c.confirmed.is_not(None),
                    source_confirmed_in_gcn_subquery.c.confirmed.is_not(True),
                ]
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
                use_cache=True,
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
                    classification_dict['votes'] = [
                        g.to_dict() for g in classification.votes
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
            if include_labellers:
                labels_subquery = (
                    SourceLabel.select(session.user_or_token)
                    .where(SourceLabel.obj_id == obj.id)
                    .subquery()
                )

                users = (
                    session.scalars(
                        User.select(session.user_or_token).join(
                            labels_subquery,
                            User.id == labels_subquery.c.labeller_id,
                        )
                    )
                    .unique()
                    .all()
                )

                obj_list[-1]["labellers"] = [user.to_dict() for user in users]

            if include_hosts:
                if obj.host_id:
                    obj_list[-1]["host"] = obj.host.to_dict()
                    obj_list[-1]["host_offset"] = obj.host_offset.deg * 3600.0

            if include_photometry_exists:
                obj_list[-1]["photometry_exists"] = check_if_obj_has_photometry(
                    obj.id, user, session
                )
            if include_spectrum_exists:
                stmt = Spectrum.select(session.user_or_token).where(
                    Spectrum.obj_id == obj.id
                )
                count_stmt = sa.select(func.count()).select_from(stmt.distinct())
                total_spectrum = session.execute(count_stmt).scalar()
                obj_list[-1]["spectrum_exists"] = total_spectrum > 0
            if include_comment_exists:
                stmt = Comment.select(session.user_or_token).where(
                    Comment.obj_id == obj.id
                )
                count_stmt = sa.select(func.count()).select_from(stmt.distinct())
                total_comment = session.execute(count_stmt).scalar()
                obj_list[-1]["comment_exists"] = total_comment > 0
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


def post_source(data, user_id, session, refresh_source=True):
    """Post source to database.
    data: dict
        Source dictionary
    user_id : int
        SkyPortal ID of User posting the GcnEvent
    session: sqlalchemy.Session
        Database session for this transaction
    refresh_source : bool
        Refresh source upon post. Defaults to True.
    """

    user = session.scalar(sa.select(User).where(User.id == user_id))

    if ' ' in data["id"]:
        raise AttributeError("No spaces allowed in source ID")

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
        if not user.is_admin:
            group_user = session.scalars(
                GroupUser.select(user)
                .where(GroupUser.user_id == user.id)
                .where(GroupUser.group_id == group.id)
            ).first()
            if group_user is None:
                raise AttributeError(
                    f'User is not a member of the group with ID {group.id}.'
                )
            if not group_user.can_save:
                raise AttributeError(
                    f'User does not have power to save to group with ID {group.id}.'
                )
        if source is not None:
            source.active = True
            source.saved_by = user
        else:
            session.add(Source(obj=obj, group=group, saved_by_id=user.id))

    session.commit()

    loop = None
    for group in groups:
        tnsrobot = session.scalars(
            TNSRobot.select(user).where(
                TNSRobot.auto_report_group_ids.contains([group.id]),
                TNSRobot.auto_reporters.isnot(None),
            )
        ).first()
        if tnsrobot is not None:
            if loop is None:
                try:
                    loop = IOLoop.current()
                except RuntimeError:
                    loop = IOLoop(make_current=True).current()

            loop.run_in_executor(
                None,
                lambda: post_tns(
                    obj_ids=[obj.id],
                    tnsrobot_id=tnsrobot.id,
                    user_id=user.id,
                    reporters=tnsrobot.auto_reporters,
                    timeout=30,
                ),
            )

            # only need to report once
            break

    if not obj_already_exists:
        post_thumbnails([obj.id])
    else:
        if refresh_source:
            flow = Flow()
            flow.push(
                '*', "skyportal/REFRESH_SOURCE", payload={"obj_key": obj.internal_key}
            )
            flow.push(
                '*', "skyportal/REFRESH_CANDIDATE", payload={"id": obj.internal_key}
            )

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
    async def get(self, obj_id=None):
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
              name: includeAnalyses
              nullable: true
              schema:
                type: boolean
              description: |
                Boolean indicating whether to include associated analyses. Defaults to
                false.
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
              name: includeCommentExists
              nullable: true
              schema:
                type: boolean
              description: |
                Boolean indicating whether to return if a source has a comment. Defaults to false.
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
            name: rejectedSourceIDs
            nullable: true
            schema:
              type: str
            description: Comma-separated string of object IDs not to be returned, useful in cases where you are looking for new sources passing a query.
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
            name: hasBeenLabelled
            nullable: true
            schema:
              type: boolean
            description: |
              If true, return only those objects which have been labelled
          - in: query
            name: hasNotBeenLabelled
            nullable: true
            schema:
              type: boolean
            description: |
              If true, return only those objects which have not been labelled
          - in: query
            name: currentUserLabeller
            nullable: true
            schema:
              type: boolean
            description: |
              If true and one of hasBeenLabeller or hasNotBeenLabelled is true, return only those objects which have been labelled/not labelled by the current user. Otherwise, return results for all users.
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
            name: includeLabellers
            nullable: true
            schema:
              type: boolean
            description: |
              Boolean indicating whether to return list of users who have labelled this source. Defaults to false.
          - in: query
            name: includeHosts
            nullable: true
            schema:
              type: boolean
            description: |
              Boolean indicating whether to return source host galaxies. Defaults to false.

          - in: query
            name: includeCommentExists
            nullable: true
            schema:
              type: boolean
            description: |
              Boolean indicating whether to return if a source has a comment. Defaults to false.
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
            name: classifications_simul
            nullable: true
            schema:
              type: boolean
            description: |
              Boolean indicating whether object must satisfy all classifications if query (i.e. an AND rather than an OR).
              Defaults to false.
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
            name: unclassified
            nullable: true
            schema:
              type: boolean
            description: |
              Boolean indicating whether to reject any sources with classifications.
              Defaults to false.
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
            name: localizationRejectSources
            schema:
              type: bool
            description: |
              Remove sources rejected in localization. Defaults to false.
          - in: query
            name: spatialCatalogName
            schema:
              type: string
            description: |
                Name of spatial catalog to use. spatialCatalogEntryName must also be defined for use.
          - in: query
            name: spatialCatalogEntryName
            schema:
              type: string
            description: |
                Name of spatial catalog entry to use. spatialCatalogName must also be defined for use.
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
        rejectedSourceIDs = self.get_query_argument('rejectedSourceIDs', None)
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
        include_analyses = self.get_query_argument("includeAnalyses", False)
        include_photometry_exists = self.get_query_argument(
            "includePhotometryExists", False
        )
        include_spectrum_exists = self.get_query_argument(
            "includeSpectrumExists", False
        )
        include_comment_exists = self.get_query_argument("includeCommentExists", False)
        include_period_exists = self.get_query_argument("includePeriodExists", False)
        include_labellers = self.get_query_argument("includeLabellers", False)
        include_hosts = self.get_query_argument("includeHosts", False)
        exclude_forced_photometry = self.get_query_argument(
            "excludeForcedPhotometry", False
        )
        remove_nested = self.get_query_argument("removeNested", False)
        include_detection_stats = self.get_query_argument(
            "includeDetectionStats", False
        )
        classifications = self.get_query_argument("classifications", None)
        classifications_simul = self.get_query_argument("classifications_simul", False)
        nonclassifications = self.get_query_argument("nonclassifications", None)
        unclassified = self.get_query_argument("unclassified", False)
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
        localization_reject_sources = self.get_query_argument(
            "localizationRejectSources", False
        )
        include_sources_in_gcn = self.get_query_argument("includeSourcesInGcn", False)
        spatial_catalog_name = self.get_query_argument("spatialCatalogName", None)
        spatial_catalog_entry_name = self.get_query_argument(
            "spatialCatalogEntryName", None
        )
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

        if spatial_catalog_name is not None:
            if spatial_catalog_entry_name is None:
                return self.error(
                    'spatialCatalogEntryName must be defined if spatialCatalogName is as well'
                )

        if rejectedSourceIDs:
            rejectedSourceIDs = rejectedSourceIDs.split(",")

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
        has_been_labelled = self.get_query_argument('hasBeenLabelled', False)
        has_not_been_labelled = self.get_query_argument('hasNotBeenLabelled', False)
        current_user_labeller = self.get_query_argument('currentUserLabeller', False)
        total_matches = self.get_query_argument('totalMatches', None)
        is_token_request = isinstance(self.current_user, Token)

        if obj_id is not None:
            with self.Session() as session:
                try:
                    source_info = await get_source(
                        obj_id,
                        self.associated_user_object.id,
                        session,
                        include_thumbnails=include_thumbnails,
                        include_comments=include_comments,
                        include_analyses=include_analyses,
                        include_photometry=include_photometry,
                        include_photometry_exists=include_photometry_exists,
                        include_spectrum_exists=include_spectrum_exists,
                        include_comment_exists=include_comment_exists,
                        include_period_exists=include_period_exists,
                        include_detection_stats=include_detection_stats,
                        include_labellers=include_labellers,
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
                query_results = await get_sources(
                    self.associated_user_object.id,
                    session,
                    include_thumbnails=include_thumbnails,
                    include_comments=include_comments,
                    include_photometry_exists=include_photometry_exists,
                    include_spectrum_exists=include_spectrum_exists,
                    include_comment_exists=include_comment_exists,
                    include_period_exists=include_period_exists,
                    include_detection_stats=include_detection_stats,
                    include_labellers=include_labellers,
                    include_hosts=include_hosts,
                    exclude_forced_photometry=exclude_forced_photometry,
                    is_token_request=is_token_request,
                    include_requested=include_requested,
                    requested_only=requested_only,
                    include_color_mag=include_color_mag,
                    remove_nested=remove_nested,
                    first_detected_date=first_detected_date,
                    last_detected_date=last_detected_date,
                    sourceID=sourceID,
                    rejectedSourceIDs=rejectedSourceIDs,
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
                    has_been_labelled=has_been_labelled,
                    has_not_been_labelled=has_not_been_labelled,
                    current_user_labeller=current_user_labeller,
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
                    classifications_simul=classifications_simul,
                    nonclassifications=nonclassifications,
                    unclassified=unclassified,
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
                    localization_reject_sources=localization_reject_sources,
                    include_sources_in_gcn=include_sources_in_gcn,
                    spatial_catalog_name=spatial_catalog_name,
                    spatial_catalog_entry_name=spatial_catalog_entry_name,
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
                      refresh_source:
                        type: bool
                        description: |
                          Refresh source upon post. Defaults to True.
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
        refresh_source = data.pop('refresh_source', True)

        with self.Session() as session:
            try:
                obj_id = post_source(
                    data,
                    self.associated_user_object.id,
                    session,
                    refresh_source=refresh_source,
                )
                return self.success(data={"id": obj_id})
            except Exception as e:
                return self.error(f'Failed to post source: {str(e)}')

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
        update_summary_history_if_relevant(data, obj, self.associated_user_object)

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


class SurveyThumbnailHandler(BaseHandler):
    @auth_or_token  # We should allow these requests from view-only users (triggered on source page)
    def post(self):
        data = self.get_json()
        obj_id = data.get("objID")
        obj_ids = data.get("objIDs")

        if obj_id is None and obj_ids is None:
            return self.error("Missing required parameter objID or objIDs")

        if obj_id is not None:
            obj_ids = [obj_id]

        post_thumbnails(obj_ids)

        return self.success()


class SourceObservabilityPlotHandler(BaseHandler):
    @auth_or_token
    async def get(self, obj_id):
        """
        ---
        description: Create a summary plot for the observability for a given source.
        tags:
          - localizations
        parameters:
          - in: path
            name: obj_id
            required: true
            schema:
              type: string
            description: |
              ID of object to generate observability plot for
          - in: query
            name: maximumAirmass
            nullable: true
            schema:
              type: number
            description: |
              Maximum airmass to consider. Defaults to 2.5.
          - in: query
            name: twilight
            nullable: true
            schema:
              type: string
            description: |
                Twilight definition. Choices are astronomical (-18 degrees), nautical (-12 degrees), and civil (-6 degrees).
        responses:
          200:
            content:
              application/json:
                schema: Success
        """

        max_airmass = self.get_query_argument("maxAirmass", 2.5)
        twilight = self.get_query_argument("twilight", "astronomical")

        with self.Session() as session:

            stmt = Telescope.select(self.current_user)
            telescopes = session.scalars(stmt).all()

            stmt = Obj.select(self.current_user).where(Obj.id == obj_id)
            source = session.scalars(stmt).first()
            coords = astropy.coordinates.SkyCoord(source.ra, source.dec, unit='deg')

            trigger_time = Time.now()
            times = trigger_time + np.linspace(0, 1) * u.day

            observers = []
            for telescope in telescopes:
                if not telescope.fixed_location:
                    continue
                location = EarthLocation(
                    lon=telescope.lon * u.deg,
                    lat=telescope.lat * u.deg,
                    height=(telescope.elevation or 0) * u.m,
                )

                observers.append(Observer(location, name=telescope.nickname))
            observers = list(reversed(observers))

            constraints = [
                getattr(AtNightConstraint, f'twilight_{twilight}')(),
                AirmassConstraint(max_airmass),
            ]

            output_format = 'pdf'
            fig = plt.figure(figsize=(14, 10))
            width, height = fig.get_size_inches()
            fig.set_size_inches(width, (len(observers) + 1) / 16 * width)
            ax = plt.axes()
            locator = dates.AutoDateLocator()
            formatter = dates.DateFormatter('%H:%M')
            ax.set_xlim([times[0].plot_date, times[-1].plot_date])
            ax.xaxis.set_major_formatter(formatter)
            ax.xaxis.set_major_locator(locator)
            ax.set_xlabel(f"Time from {min(times).datetime.date()} [UTC]")
            plt.setp(ax.get_xticklabels(), rotation=30, ha='right')
            ax.set_yticks(np.arange(len(observers)))
            ax.set_yticklabels([observer.name for observer in observers])
            ax.yaxis.set_tick_params(left=False)
            ax.grid(axis='x')
            ax.spines['bottom'].set_visible(False)
            ax.spines['top'].set_visible(False)

            for i, observer in enumerate(observers):
                observable = 100 * np.dot(
                    1.0, is_event_observable(constraints, observer, coords, times)
                )
                ax.contourf(
                    times.plot_date,
                    [i - 0.4, i + 0.4],
                    np.tile(observable, (2, 1)),
                    levels=np.arange(10, 110, 10),
                    cmap=plt.get_cmap().reversed(),
                )

            buf = io.BytesIO()
            fig.savefig(buf, format=output_format, bbox_inches='tight')
            plt.close(fig)
            buf.seek(0)

            filename = f"observability.{output_format}"
            data = io.BytesIO(buf.read())

            await self.send_file(data, filename, output_type=output_format)


class SourceCopyPhotometryHandler(BaseHandler):
    @permissions(["Upload data"])
    def post(self, target_id):
        """
        ---
        description: Copy all photometry points from one source to another
        tags:
          - sources
          - photometry
        parameters:
          - in: path
            name: target_id
            required: true
            schema:
              type: string
            description: |
              The obj_id of the target Source (to which the photometry is being copied to)
        requestBody:
          content:
            application/json:
              schema:
                type: object
                properties:
                  group_ids:
                    type: array
                    items:
                      type: integer
                    description: |
                      List of IDs of groups to give photometry access to
                  origin_id:
                    type: string
                    description: |
                      The ID of the Source's Obj the photometry is being copied from
                required:
                  - group_ids
                  - origin_id
        responses:
          200:
            content:
              application/json:
                schema:
                  allOf:
                    - $ref: '#/components/schemas/Success'
        """

        data = self.get_json()

        if data.get("group_ids") is None:
            return self.error("Missing required parameter `groupIds`")
        try:
            group_ids = [int(gid) for gid in data["group_ids"]]
        except ValueError:
            return self.error(
                "Invalid value provided for `groupIDs`; unable to parse "
                "all list items to integers."
            )

        if data.get("origin_id") is None:
            return self.error("Missing required parameter `duplicateId`")

        origin_id = data.get("origin_id")

        with self.Session() as session:
            s = session.scalars(
                Obj.select(self.current_user).where(Obj.id == target_id)
            ).first()
            if s is None:
                return self.error(f"Source {target_id} not found")

            d = session.scalars(
                Obj.select(self.current_user).where(Obj.id == origin_id)
            ).first()
            if d is None:
                return self.error("Duplicate source {origin_id} not found")

            groups = (
                session.scalars(
                    Group.select(self.current_user).where(Group.id.in_(group_ids))
                )
                .unique()
                .all()
            )
            if {g.id for g in groups} != set(group_ids):
                return self.error(
                    f'Cannot find one or more groups with IDs: {group_ids}.'
                )

            data = session.scalars(
                Photometry.select(self.current_user)
                .options(
                    joinedload(Photometry.instrument).joinedload(Instrument.telescope)
                )
                .where(Photometry.obj_id == origin_id)
            ).all()

            query_result = []
            for p in data:
                instrument = p.instrument
                result = serialize(p, 'ab', 'both', groups=False, annotations=False)
                query_result.append(result)

            df = pd.DataFrame.from_dict(query_result)
            if df.empty:
                return self.error(f"No photometry found with source {origin_id}")

            drop_columns = list(
                set(df.columns.values)
                - {'mjd', 'ra', 'dec', 'mag', 'magerr', 'limiting_mag', 'filter'}
            )

            df.drop(
                columns=drop_columns,
                inplace=True,
            )
            df['magsys'] = 'ab'

            data_out = {
                'obj_id': target_id,
                'instrument_id': instrument.id,
                'group_ids': [g.id for g in groups],
                **df.to_dict(orient='list'),
            }

            add_external_photometry(data_out, self.associated_user_object)

            self.push_all(
                action="skyportal/REFRESH_SOURCE",
                payload={"obj_key": s.internal_key},
            )

            return self.success()
