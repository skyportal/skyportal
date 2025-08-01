import sqlalchemy as sa

from baselayer.log import make_log
from .asynchronous import run_async
from ..utils.tns import TNS_INSTRUMENT_IDS
from ..models import (
    Obj,
    Source,
    Instrument,
    GroupUser,
    Stream,
    Photometry,
    StreamPhotometry,
    PublicRelease,
    SharingServiceGroupAutoPublisher,
    SharingServiceSubmission,
    SharingServiceGroup,
    SharingService,
    Thumbnail,
    InstrumentSharingService,
    StreamSharingService,
)
from .parse import get_list_typed, is_null

log = make_log("publishable_access")

SHARING_INSTRUMENT_IDS = TNS_INSTRUMENT_IDS

PHOTOMETRY_OPTIONS = {
    "first_and_last_detections": bool,
    "auto_sharing_allow_archival": bool,
}


def check_access_to_sharing_service(session, user, sharing_service_id):
    """Check if the user has access to the sharing_service.
    Returns the sharing service object if the user has access, otherwise raises ValueError.

    Parameters
    ----------
    session : `baselayer.app.models.Session`
        Database session, which contains the user or token
    user : `baselayer.app.models.User`
        The user to check access for
    sharing_service_id : int
        The ID of the sharing_service to check access for

    Returns
    -------
    sharing_service : `SharingService`
        The SharingService object if the user has access, otherwise raises ValueError
    """
    sharing_service = session.scalar(
        SharingService.select(user).where(SharingService.id == sharing_service_id)
    )
    if sharing_service is None:
        raise ValueError(
            f"No sharing service with ID {sharing_service_id}, or inaccessible"
        )
    return sharing_service


def is_existing_submission_request(
    session, obj, sharing_service_id, service, is_bot=False
):
    """Check if there is an existing submission request for the given object and sharing service and external service.
    session: SQLAlchemy
        session
    obj: Obj
        object to check
    sharing_service_id: int
        ID of the sharing service
    service: str
        Name of the external service to check (TNS or Hermes)
    is_bot: bool
        If True, checks for bot-specific submissions; otherwise, checks for all submissions.

    Returns:
        SharingServiceSubmission or None:
            The existing submission request if found, None otherwise.
    """
    if service not in ["TNS", "Hermes"]:
        raise ValueError("Invalid service name. Must be 'TNS' or 'Hermes'.")
    if service == "TNS":
        service_status = SharingServiceSubmission.tns_status
    else:
        service_status = SharingServiceSubmission.hermes_status

    stmt = SharingServiceSubmission.select(session.user_or_token).where(
        SharingServiceSubmission.obj_id == obj.id,
        SharingServiceSubmission.sharing_service_id == sharing_service_id,
        sa.or_(
            service_status == "pending",
            service_status == "processing",
            service_status.like("submitted%"),
            service_status.like("complete%"),
        ),
    )
    if is_bot:
        stmt = stmt.where(SharingServiceGroup.auto_sharing_allow_bots.is_(True))
    return session.scalars(stmt).first()


def process_instrument_ids(
    session, user, instrument_ids, accessible_instrument_ids=None
):
    """
    Retrieve the list of instruments from the database and
    check that they are valid and supported for sharing.

    Parameters
    ----------
    session : `~sqlalchemy.orm.Session`
        The database session to use.
    user : `~skyportal.models.User`
        The user to check access for.
    instrument_ids : list of str or list of int
        The list of instrument IDs to check and retrieve.
    accessible_instrument_ids : list of str, optional
        The list of accessible instrument IDs to check against.

    Returns
    -------
    instruments : list of `~skyportal.models.Instrument` or None
        The list of instruments that are valid and supported for sharing.
    """
    if instrument_ids:
        instrument_ids = get_list_typed(
            instrument_ids,
            int,
            "instrument_ids must be a comma-separated list of integers",
        )
        if accessible_instrument_ids:
            # Only keep the instrument IDs that are in the list of accessible instrument IDs
            instrument_ids = list(set(instrument_ids) & set(accessible_instrument_ids))
        else:
            instrument_ids = list(set(instrument_ids))
        instruments = session.scalars(
            Instrument.select(user).where(Instrument.id.in_(instrument_ids))
        ).all()
        if len(instruments) != len(instrument_ids):
            raise ValueError(f"One or more instruments not found: {instrument_ids}")
        for instrument in instruments:
            if instrument.name.lower() not in SHARING_INSTRUMENT_IDS:
                raise ValueError(
                    f"Instrument {instrument.name} not supported for sharing"
                )
        return instruments
    else:
        return None


def filter_accessible_instrument_ids(session, user, instrument_ids, sharing_service):
    """
    Filter the instrument IDs based on the sharing service and the user access.

    Parameters
    ----------
    session : `~sqlalchemy.orm.Session`
        The database session to use.
    user : `~skyportal.models.User`
        The user to check access for.
    instrument_ids : list of str or list of int
        The list of instrument IDs to filter.
    sharing_service : `~skyportal.models.SharingService`
        The sharing service to submit with.

    Returns
    -------
    instrument_ids : list of int
        The instrument IDs publishable and accessible to the sharing service and the user.
    """
    # get the list of instrument IDs that the sharing service has access to
    accessible_instrument_ids = session.scalars(
        sa.select(InstrumentSharingService.instrument_id).where(
            InstrumentSharingService.sharing_service_id == sharing_service.id
        )
    ).all()
    if not accessible_instrument_ids:
        raise ValueError(
            f"Must specify instruments on the sharing service '{sharing_service.id}' before submitting source."
        )
    # if instrument_ids are not specified, we use the sharing service list of instruments
    if not instrument_ids:
        instrument_ids = accessible_instrument_ids

    instruments = process_instrument_ids(
        session, user, instrument_ids, accessible_instrument_ids
    )
    if not instruments:
        raise ValueError(
            f"None of the instruments specified for the submission request are accessible to sharing service '{sharing_service.id}'."
        )

    return [instrument.id for instrument in instruments]


def process_stream_ids(session, user, stream_ids, accessible_stream_ids=None):
    """
    Retrieve the list of streams from the database and
    check that they are valid.

    Parameters
    ----------
    session : `~sqlalchemy.orm.Session`
        The database session to use.
    user : `~skyportal.models.User`
        The user to check access for.
    stream_ids : list of str or list of int
        The list of stream IDs to check and retrieve.
    accessible_stream_ids : list of str, optional
        The list of accessible stream IDs to check against.

    Returns
    -------
    streams : list of `~skyportal.models.Stream` or None
        The list of streams that are publishable and accessible for the user.
    """
    if stream_ids:
        stream_ids = get_list_typed(
            stream_ids, int, "stream_ids must be a comma-separated list of integers"
        )
        if accessible_stream_ids is not None:
            # Only keep the stream IDs that are in the list of accessible stream IDs
            stream_ids = list(set(stream_ids) & set(accessible_stream_ids))
        else:
            stream_ids = list(set(stream_ids))
        streams = session.scalars(
            Stream.select(user).where(Stream.id.in_(stream_ids))
        ).all()
        if len(streams) != len(stream_ids):
            raise ValueError(f"One or more streams not found: {stream_ids}")
        return streams
    else:
        return None


def filter_accessible_stream_ids(
    session, user, stream_ids, sharing_service, auto_submission=False
):
    """
    Filter the stream IDs based on the sharing service and the user access.

    Parameters
    ----------
    session : `~sqlalchemy.orm.Session`
        The database session to use.
    stream_ids : list of str or list of int
        The list of stream IDs to filter.
    user : `~skyportal.models.User`
        The user to check access for.
    sharing_service : `~skyportal.models.SharingService`
        The sharing service to submit with.
    auto_submission : bool, optional
        Whether the submission is an auto-submission, by default False

    Returns
    -------
    stream_ids : list of int or None
        The stream IDs accessible to the sharing service and the user or None.
    """
    # specifying streams to use being optional, we return None if no streams are specified
    if not auto_submission and not stream_ids:
        return None

    accessible_stream_ids = session.scalars(
        sa.select(StreamSharingService.stream_id).where(
            StreamSharingService.sharing_service_id == sharing_service.id
        )
    ).all()
    # if it is an auto submission, we use the sharing service list of stream
    if auto_submission:
        if not accessible_stream_ids:
            raise ValueError(
                f"Must specify streams for sharing service {sharing_service.id} when auto-submitting source."
            )
        stream_ids = accessible_stream_ids

    streams = process_stream_ids(session, user, stream_ids, accessible_stream_ids)
    return [stream.id for stream in streams]


def validate_photometry_options(
    photometry_options=None, existing_photometry_options=None
):
    """Validate the photometry options and their values

    Parameters
    ----------
    photometry_options : dict, optional
        Dictionary containing the photometry options
    existing_photometry_options : dict, optional
        Dictionary containing the existing photometry options, by default None

    Returns
    -------
    dict
        Dictionary containing the validated photometry options
    """
    if photometry_options is None:
        photometry_options = {}
    if not isinstance(photometry_options, dict):
        raise ValueError("photometry_options must be a dictionary")

    # if existing_photometry_options is provided, add missing keys with the existing values
    if existing_photometry_options is not None and isinstance(
        existing_photometry_options, dict
    ):
        for key in PHOTOMETRY_OPTIONS:
            if key not in photometry_options and key in existing_photometry_options:
                photometry_options[key] = existing_photometry_options[key]

    # validate the photometry options and their values
    for key, value in photometry_options.items():
        if key not in PHOTOMETRY_OPTIONS:
            raise ValueError(f"Invalid photometry option: {key}")
        if not isinstance(value, PHOTOMETRY_OPTIONS[key]):
            raise ValueError(f"Invalid value for photometry option {key}: {value}")

    # add the missing keys with default values (default to True if not specified)
    for key in PHOTOMETRY_OPTIONS:
        if key not in photometry_options:
            photometry_options[key] = True

    return photometry_options


def get_photometry_by_instruments_stream_and_options(
    session, user, obj_id, instrument_ids, stream_ids, photometry_options
):
    """Filter the photometry by the stream IDs.

    Parameters
    ----------
    session : Session
        Database session
    user : User
        The user trying to publish the data
    obj_id : str
        Object ID
    instrument_ids : list of int
        List of instrument IDs to filter by
    stream_ids : list of int
        List of stream IDs to filter by
    photometry_options : dict
        Dictionary containing the photometry options
    """
    # Filter the photometry by instrument IDs
    photometry = session.scalars(
        Photometry.select(user).where(
            Photometry.obj_id == obj_id,
            Photometry.instrument_id.in_(instrument_ids),
            # keep all non-detections, reject detections with SNR < 5
            sa.or_(
                Photometry.flux / Photometry.fluxerr > 5,
                Photometry.flux.is_(None),
            ),
        )
    ).all()

    if len(photometry) == 0:
        raise ValueError(
            f"No photometry available for {obj_id} with instruments {instrument_ids}."
        )

    # Filter the photometry by stream IDs
    if stream_ids:
        photometry = [
            phot
            for phot in photometry
            if session.scalar(
                sa.select(StreamPhotometry.stream_id).where(
                    StreamPhotometry.photometr_id == phot.id,
                    StreamPhotometry.stream_id.in_(stream_ids),
                )
            )
            is not None
        ]
    detections = [phot for phot in photometry if not is_null(phot.mag)]

    # if no photometry or only non-detections photometry is found, raise an error
    if not detections:
        stream_names = (
            session.scalars(sa.select(Stream.name).where(Stream.id.in_(stream_ids)))
            .unique()
            .all()
        )
        raise ValueError(
            f"No photometry for {obj_id} with {'streams ' + ', '.join(stream_names) if stream_names else 'unspecified streams'}, cannot submit"
        )

    # Filter the photometry by the photometry options
    if photometry_options.get("first_and_last_detections", False):
        if len(detections) < 2:
            raise ValueError(
                f"'first and last detections' option is set but only one detection is available."
            )

    return photometry


def get_publishable_source_and_photometry(
    session,
    user,
    sharing_service_id,
    obj_id,
    instrument_ids,
    stream_ids,
    photometry_options,
    is_auto_submission,
):
    """Get publishable source and photometry after checking the access and the options.

    Parameters
    ----------
    session : Session
        Database session
    user : User
        The user trying to publish the data
    sharing_service_id : int
        The ID of the sharing services to use for restricting the data
    obj_id : str
        Object ID
    instrument_ids : list of str
        List of instrument IDs to restrict the data from
    stream_ids : list of str
        List of stream IDs to restrict the data from
    photometry_options : dict
        Photometry options to use for the data
    is_auto_submission : bool
        Whether the submission is an auto-submission

    Returns
    -------
    source : Source
        The publishable source
    photometry : list of Photometry
        The list of publishable photometry
    stream_ids : list of int
        The list of stream IDs used to filter the photometry
    """
    obj = session.scalar(Obj.select(user, mode="read").where(Obj.id == obj_id))
    if not obj:
        raise ValueError(f"Object {obj_id} not found")

    sharing_service = check_access_to_sharing_service(session, user, sharing_service_id)

    # Filter sharing service groups the user has access to
    user_accessible_group_ids = [group.id for group in user.accessible_groups]
    valid_groups = [
        group
        for group in sharing_service.groups
        if group.group_id in user_accessible_group_ids
    ]

    # if auto_submission, check if the group has auto-publish enabled for TNS or Hermes
    # and if the user is an auto-publisher for that group
    if is_auto_submission:
        valid_groups = [
            group
            for group in valid_groups
            if group.auto_share_to_tns or group.auto_share_to_hermes
        ]
        if not valid_groups:
            raise ValueError(
                f"No group with sharing services {sharing_service_id} set to auto-publish."
            )

        # we filter out the groups that this user is not an auto-publisher for
        valid_groups = [
            group
            for group in valid_groups
            if session.scalar(
                sa.select(SharingServiceGroupAutoPublisher).where(
                    SharingServiceGroupAutoPublisher.sharing_service_group_id
                    == group.id,
                    SharingServiceGroupAutoPublisher.group_user_id.in_(
                        sa.select(GroupUser.id).where(
                            GroupUser.user_id == user.id,
                            GroupUser.group_id == group.group_id,
                        )
                    ),
                )
            )
        ]
        if not valid_groups:
            raise ValueError(
                f"User {user.id} is not an auto-publisher for any group with sharing services {sharing_service_id}."
            )

        # if the user is a bot, filter out the groups that are not set to auto-publish with bots
        if user.is_bot:
            valid_groups = [
                group for group in valid_groups if group.auto_sharing_allow_bots
            ]

            if not valid_groups:
                raise ValueError(
                    f"No group in sharing service {sharing_service_id} set to auto-publish with bot users."
                )

    photometry_options = validate_photometry_options(
        photometry_options, sharing_service.photometry_options
    )

    source = session.scalar(
        Source.select(user)
        .where(
            Source.obj_id == obj_id,
            Source.active.is_(True),
            Source.group_id.in_([group.group_id for group in valid_groups]),
        )
        .order_by(Source.saved_at.asc())
    )
    if source is None:
        raise ValueError(
            f"Source {obj_id} not saved to any group with sharing services {sharing_service_id}."
        )

    instrument_ids = filter_accessible_instrument_ids(
        session, user, instrument_ids, sharing_service
    )
    stream_ids = filter_accessible_stream_ids(
        session, user, stream_ids, sharing_service, auto_submission=is_auto_submission
    )

    photometry = get_photometry_by_instruments_stream_and_options(
        session, user, obj_id, instrument_ids, stream_ids, photometry_options
    )

    return source, photometry, stream_ids


def auto_source_publishing(session, saver, group_id, obj, publish_to):
    """Check for every auto publishing procedure for a source that is saved to a group.

    Parameters
    ----------
    session : Session
        Database session
    saver : User
        The user who saved the source
    group_id : int
        The ID of the group to which the source is saved
    obj : Obj
        The source object to check for auto-publishing
    publish_to : list of str
        The procedures to check for auto-publishing (e.g., ["TNS", "Hermes", "Public page"])
    """
    tns, hermes = "TNS", "Hermes"
    if tns in publish_to or hermes in publish_to:
        # Check if group auto publish is enabled to TNS or Hermes and a user is auto publisher
        stmt = (
            SharingServiceGroup.select(saver)
            .join(
                SharingServiceGroupAutoPublisher,
                SharingServiceGroup.id
                == SharingServiceGroupAutoPublisher.sharing_service_group_id,
            )
            .where(
                SharingServiceGroup.group_id == group_id,
                sa.or_(
                    SharingServiceGroup.auto_share_to_tns,
                    SharingServiceGroup.auto_share_to_hermes,
                ),
                SharingServiceGroupAutoPublisher.group_user_id.in_(
                    sa.select(GroupUser.id).where(
                        GroupUser.user_id == saver.id,
                        GroupUser.group_id == group_id,
                    )
                ),
            )
        )
        if saver.is_bot:
            stmt = stmt.where(SharingServiceGroup.auto_sharing_allow_bots.is_(True))
        groups_with_auto_publisher = session.scalars(stmt).all()
        if groups_with_auto_publisher:
            external_services = {}
            # Determine which external services (TNS, Hermes) can be auto-published
            # and the corresponding sharing service id
            for group in groups_with_auto_publisher:
                sharing_service = group.sharing_service
                if (
                    not external_services.get(tns)
                    and tns in publish_to
                    and sharing_service.enable_sharing_with_tns
                    and group.auto_share_to_tns
                    and not is_existing_submission_request(
                        session, obj, sharing_service.id, tns
                    )
                ):
                    external_services[tns] = sharing_service.id
                    publish_to.remove(
                        tns
                    )  # Remove TNS from publish_to to avoid duplicate processing

                if (
                    not external_services.get(hermes)
                    and hermes in publish_to
                    and sharing_service.enable_sharing_with_hermes
                    and group.auto_share_to_hermes
                    and not is_existing_submission_request(
                        session, obj, sharing_service.id, hermes
                    )
                ):
                    external_services[hermes] = sharing_service.id
                    publish_to.remove(
                        hermes
                    )  # Remove Hermes from publish_to to avoid duplicate processing
                if len(external_services) == 2:
                    break

            if external_services:
                # Merge if same sharing service is used for both
                if external_services.get(tns) == external_services.get(hermes):
                    external_services = {f"{tns}/{hermes}": external_services[tns]}

                # Create submission requests
                for service_name, sharing_service_id in external_services.items():
                    submission_request = SharingServiceSubmission(
                        sharing_service_id=sharing_service_id,
                        obj_id=obj.id,
                        user_id=saver.id,
                        auto_submission=True,
                        publish_to_tns=tns in service_name,
                        tns_status="pending" if tns in service_name else None,
                        publish_to_hermes=hermes in service_name,
                        hermes_status="pending" if hermes in service_name else None,
                    )
                    session.add(submission_request)
                    session.commit()
                    log(
                        f"Added SharingServiceSubmission for obj_id {obj.id}, group {group_id}, sharing_service_id {sharing_service_id}, user_id {saver.id}, services {service_name}"
                    )
            else:
                log(
                    "No auto-sharing services associated with this group are selected to auto publish to TNS or Hermes."
                )

    if "Public page" in publish_to:
        # if there is releases with auto_publish_enabled and one of the source groups,
        # a public page is published
        releases = session.scalars(
            sa.select(PublicRelease).where(
                PublicRelease.groups.any(id=group_id),
                PublicRelease.auto_publish_enabled,
            )
        ).all()
        if releases:
            from ..handlers.api.public_pages.public_source_page import (
                async_post_public_source_page,
            )

            dict_obj = obj.to_dict()
            dict_obj["thumbnails"] = [
                thumbnail.to_dict()
                for thumbnail in session.scalars(
                    sa.select(Thumbnail).where(Thumbnail.obj_id == obj.id)
                ).all()
            ]
            for release in releases:
                run_async(
                    async_post_public_source_page,
                    options=release.options,
                    source=dict_obj,
                    release=release,
                    user_id=saver.id,
                )
