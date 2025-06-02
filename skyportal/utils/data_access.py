import sqlalchemy as sa

from baselayer.log import make_log
from .parse import get_list_typed
from .tns import TNS_INSTRUMENT_IDS

from ..models import (
    Obj,
    TNSRobot,
    InstrumentTNSRobot,
    StreamTNSRobot,
    Source,
    Instrument,
    Stream,
    Photometry,
    StreamPhotometry,
)

log = make_log("publishable_access")

PHOTOMETRY_OPTIONS = {
    "first_and_last_detections": bool,
    "autoreport_allow_archival": bool,
}


def process_instrument_ids(session, instrument_ids, accessible_instrument_ids=None):
    """
    Retrieve the list of instruments from the database and
    check that they are valid and supported for TNS publishing.

    Parameters
    ----------
    session : `~sqlalchemy.orm.Session`
        The database session to use.
    instrument_ids : list of str or list of int
        The list of instrument IDs to check and retrieve.
    accessible_instrument_ids : list of str, optional
        The list of accessible instrument IDs to check against.
    """
    if instrument_ids and len(instrument_ids) > 0:
        instrument_ids = get_list_typed(
            instrument_ids,
            int,
            "instrument_ids must be a comma-separated list of integers",
        )
        if accessible_instrument_ids is not None:
            # Only keep the instrument IDs that are in the list of accessible instrument IDs
            instrument_ids = list(set(instrument_ids) & set(accessible_instrument_ids))
        else:
            instrument_ids = list(set(instrument_ids))
        instruments = session.scalars(
            Instrument.select(session.user_or_token).where(
                Instrument.id.in_(instrument_ids)
            )
        ).all()
        if len(instruments) != len(instrument_ids):
            raise ValueError(f"One or more instruments not found: {instrument_ids}")
        for instrument in instruments:
            if instrument.name.lower() not in TNS_INSTRUMENT_IDS:
                raise ValueError(
                    f"Instrument {instrument.name} not supported for TNS reporting"
                )
        return instruments
    else:
        return None


def filter_accessible_instrument_ids(session, instrument_ids, tns_robot):
    """
    Filter the instrument IDs based on the TNSRobot and the user access.

    Parameters
    ----------
    session : `~sqlalchemy.orm.Session`
        The database session to use.
    instrument_ids : list of str
        The list of instrument IDs to filter.
    tns_robot : `~skyportal.models.TNSRobot`
        The TNSRobot to submit with.

    Returns
    -------
    instrument_ids : list of int
        The instrument IDs accessible to the TNSRobot and the user.
    """
    tns_robot = tns_robot.id

    # get the list of instrument IDs that the TNSRobot has access to
    accessible_instrument_ids = session.scalars(
        sa.select(InstrumentTNSRobot.instrument_id).where(
            InstrumentTNSRobot.tnsrobot_id == tns_robot
        )
    ).all()
    if len(accessible_instrument_ids) == 0:
        raise ValueError(
            f"Must specify instruments for TNSRobot {tns_robot} before submitting source."
        )

    instruments = process_instrument_ids(
        session, instrument_ids, accessible_instrument_ids
    )
    if len(instruments) == 0:
        raise ValueError(
            f"None of the instruments specified for the submission request are accessible to TNSRobot {tns_robot}."
        )

    return [instrument.id for instrument in instruments]


def process_stream_ids(session, stream_ids, accessible_stream_ids=None):
    """
    Retrieve the list of streams from the database and
    check that they are valid.

    Parameters
    ----------
    session : `~sqlalchemy.orm.Session`
        The database session to use.
    stream_ids : list of str or list of int
        The list of stream IDs to check and retrieve.
    accessible_stream_ids : list of str, optional
        The list of accessible stream IDs to check against.
    """
    if stream_ids and len(stream_ids) > 0:
        stream_ids = get_list_typed(
            stream_ids, int, "stream_ids must be a comma-separated list of integers"
        )
        if accessible_stream_ids is not None:
            # Only keep the stream IDs that are in the list of accessible stream IDs
            stream_ids = list(set(stream_ids) & set(accessible_stream_ids))
        else:
            stream_ids = list(set(stream_ids))
        streams = session.scalars(
            Stream.select(session.user_or_token).where(Stream.id.in_(stream_ids))
        ).all()
        if len(streams) != len(stream_ids):
            raise ValueError(f"One or more streams not found: {stream_ids}")
        return streams
    else:
        return None


def filter_accessible_stream_ids(session, stream_ids, tns_robot, auto_submission=False):
    """
    Filter the stream IDs based on the TNSRobot and the user access.

    Parameters
    ----------
    session : `~sqlalchemy.orm.Session`
        The database session to use.
    stream_ids : list of str
        The list of stream IDs to filter.
    tns_robot : `~skyportal.models.TNSRobot`
        The TNSRobot to submit with.
    auto_submission : bool, optional
        Whether the submission is an auto-submission, by default False

    Returns
    -------
    stream_ids : list of int
        The stream IDs accessible to the TNSRobot and the user.
    """
    tns_robot_id = tns_robot.id

    # if it is auto_submission or if stream_ids are not specified
    # we use the TNSRobot list of stream
    if auto_submission or stream_ids is None or len(stream_ids) == 0:
        accessible_stream_ids = session.scalars(
            sa.select(StreamTNSRobot.stream_id).where(
                StreamTNSRobot.tnsrobot_id == tns_robot_id
            )
        ).all()

        if len(accessible_stream_ids) == 0 and auto_submission is True:
            raise ValueError(
                f"Must specify streams for TNSRobot {tns_robot_id} when auto-submitting source to TNS."
            )
    else:
        # if it is not auto_submission and stream_ids are specified,
        # we use all the specified stream not filtered by the TNSRobot stream
        accessible_stream_ids = None

    streams = process_stream_ids(session, stream_ids, accessible_stream_ids)
    if len(streams) == 0:
        return None
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
            # make sure that the origin does not contain 'fp' (for forced photometry)
            # as we only want to submit alert-based photometry for surveys
            # like ZTF that also provide a forced photometry service,
            # which detections might have lower SNR and be less reliable or not real
            ~Photometry.origin.ilike("%fp%"),
        )
    ).all()

    if len(photometry) == 0:
        raise ValueError(
            f"No photometry available for {obj_id} with instruments {instrument_ids}."
        )

    # Filter the photometry by stream IDs
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
    detections = [
        phot for phot in photometry if phot.mag not in {None, "", "None", "nan"}
    ]

    # if no photometry or only non-detections photometry is found, raise an error
    if len(detections) == 0:
        stream_names = (
            session.scalars(sa.select(Stream.name).where(Stream.id.in_(stream_ids)))
            .unique()
            .all()
        )
        raise ValueError(
            f"No photometry for {obj_id} with streams {', '.join(stream_names)}, cannot submit"
        )

    # Filter the photometry by the photometry options
    if photometry_options.get("first_and_last_detections", False):
        if len(detections) < 2:
            raise ValueError(
                f"'first and last detections' option is set but only one detection is available."
            )

    return photometry


def get_publishable_obj_photometry(
    session, user, tns_robot_id, obj_id, instrument_ids, stream_ids, photometry_options
):
    """Get publishable source and photometry after checking the access and the options.

    Parameters
    ----------
    session : Session
        Database session
    user : User
        The user trying to publish the data
    tns_robot_id : str
        The ID of the TNSRobot to use for restricting the data
    obj_id : str
        Object ID
    instrument_ids : list of str
        List of instrument IDs to restrict the data from
    stream_ids : list of str
        List of stream IDs to restrict the data from
    photometry_options : dict
        Photometry options to use for the data

    Returns
    -------
    obj : Obj
        The publishable object
    photometry : list of Photometry
        The list of publishable photometry
    """
    process_stream_ids(session, stream_ids)

    obj = session.scalar(
        Obj.select(session.user_or_token, mode="read").where(Obj.id == obj_id)
    )
    if not obj:
        raise ValueError(f"Object {obj_id} not found")

    tns_robot = session.scalars(
        TNSRobot.select(session.user_or_token).where(TNSRobot.id == tns_robot_id)
    ).first()
    if tns_robot is None:
        return ValueError(f"TNSRobot {tns_robot_id} not found")

    # Check if the user has access to the TNSRobot
    accessible_group_ids = [g.id for g in user.accessible_groups]
    tns_robot_groups = [
        tns_robot_group
        for tns_robot_group in tns_robot.groups
        if tns_robot_group.group_id in accessible_group_ids
    ]
    if len(tns_robot_groups) == 0:
        raise ValueError(
            f"User {user.id} does not have access to any group with TNSRobot {tns_robot_id}"
        )

    photometry_options = validate_photometry_options(
        photometry_options, tns_robot.photometry_options
    )

    source = session.scalar(
        Source.select(session.user_or_token)
        .where(
            Source.obj_id == obj_id,
            Source.active.is_(True),
            Source.group_id.in_([group.group_id for group in tns_robot_groups]),
        )
        .order_by(Source.saved_at.asc())
    )
    if source is None:
        raise ValueError(
            f"Source {obj_id} not saved to any group with TNSRobot {tns_robot_id}."
        )

    instrument_ids = filter_accessible_instrument_ids(
        session, instrument_ids, tns_robot
    )
    stream_ids = filter_accessible_stream_ids(
        session, stream_ids, tns_robot, auto_submission=False
    )

    photometry = get_photometry_by_instruments_stream_and_options(
        session, user, obj_id, instrument_ids, stream_ids, photometry_options
    )

    return obj, photometry
