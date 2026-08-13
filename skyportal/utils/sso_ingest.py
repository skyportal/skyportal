"""Ingest solar-system object detections from a survey alert stream.

The standard broker path is unusable for moving targets on two counts, both
measured on ZTF:

* Identity. A survey assigns its object ID by sky position (~1.5" for ZTF), and
  a main-belt asteroid moves ~30"/hour, so a second detection lands under a new
  ID by construction: ~97% of asteroid object IDs carry exactly one detection.
  Keying on the object ID yields single-point sources, so we key on the MPC
  designation instead.
* Photometry. ``prv_candidates``, ``prv_nondetections`` and ``fp_hists`` are all
  keyed to the sky position, not the object. For a moving target that history
  belongs to whatever else has passed through those coordinates, and the forced
  photometry measures a position the asteroid has left. Only the triggering
  detection is real, so only it is ingested.
"""

import re

import astropy.units as u
import healpix_alchemy as ha
import sqlalchemy as sa
from sqlalchemy.orm import selectinload

from baselayer.log import make_log

from ..models import Obj, Source, SuperObj

log = make_log("sso_ingest")

# Alert fields that may carry an MPC designation, in order of preference.
DESIGNATION_KEYS = (
    "designation",
    "ssnamenr",
    "ztf_ssnamenr",
    "ss_object_id",
    "mpc_name",
)

# Association quality, recorded rather than thresholded: the upstream ephemeris
# match degrades over time, and a stored distribution shows that where a boolean
# cut would silently pass fewer objects.
SEPARATION_KEYS = ("separation_arcsec", "ssdistnr")

# Obj IDs appear in URL paths, whose route pattern allows [0-9A-Za-z-_.+] only.
_OBJ_ID_UNSAFE = re.compile(r"[^0-9A-Za-z\-_.+]")
OBJ_ID_PREFIX = "sso_"


def designation_to_obj_id(designation):
    """Map an MPC designation to a collision-safe, URL-safe Obj ID.

    Bare designations are often plain numbers ('220'), which would collide with
    unrelated object IDs, hence the prefix.
    """
    slug = _OBJ_ID_UNSAFE.sub("_", str(designation).strip())
    if not slug:
        raise ValueError(f"Unusable SSO designation: {designation!r}")
    return f"{OBJ_ID_PREFIX}{slug}"


def _designation_from_mapping(mapping):
    if not isinstance(mapping, dict):
        return None
    # A normalized `sso` block (BOOM's `properties.sso`) takes precedence over
    # the raw survey fields it was derived from.
    nested = mapping.get("sso")
    if isinstance(nested, dict):
        found = _designation_from_mapping(nested)
        if found:
            return found
    for key in DESIGNATION_KEYS:
        value = mapping.get(key)
        if value is None:
            continue
        value = str(value).strip()
        # Brokers spell "no match" several ways; negative sentinels are not names.
        if value and value.lower() not in ("null", "none", "nan", "-999", "-999.0"):
            return value
    return None


def _first_value(data, keys):
    """First present value for `keys`, checked in `properties.sso` then `candidate`."""
    properties = (data or {}).get("properties") or {}
    for mapping in (properties.get("sso"), properties, (data or {}).get("candidate")):
        if not isinstance(mapping, dict):
            continue
        for key in keys:
            value = mapping.get(key)
            # -999 is the upstream "no match" sentinel, not a measurement.
            if value is not None and value != -999 and value != -999.0:
                return value
    return None


def extract_designation(data=None, annotations_by_filter_id=None):
    """Find an MPC designation on an alert.

    Checked in both places it can arrive: a normalized block on the alert itself
    (``properties.sso``), and a broker filter's annotations. Which of the two
    carries it is a broker-side decision, so accept either.
    """
    for mapping in (data or {}).get("properties"), (data or {}).get("candidate"):
        found = _designation_from_mapping(mapping)
        if found:
            return found

    for annotations in (annotations_by_filter_id or {}).values():
        found = _designation_from_mapping(annotations)
        if found:
            return found

    return None


async def _link_designation(session, obj_id, designation):
    """Link this detection stream to any other Obj for the same body."""
    # Eager-load: touching a lazy collection under an async session raises.
    super_obj = await session.scalar(
        sa.select(SuperObj)
        .options(selectinload(SuperObj.objs))
        .where(SuperObj.name == designation)
    )
    obj = await session.scalar(sa.select(Obj).where(Obj.id == obj_id))

    if super_obj is None:
        # Populate at construction: a flushed-then-read collection lazy-loads.
        session.add(SuperObj(name=designation, is_roid=True, objs=[obj] if obj else []))
        return

    super_obj.is_roid = True
    if obj is not None and obj_id not in {o.id for o in super_obj.objs}:
        super_obj.objs.append(obj)


async def ingest_sso_alert(
    data,
    survey,
    session,
    user,
    designation,
    group_ids,
):
    """Ingest one alert as a detection of a known solar-system object.

    Parameters
    ----------
    data : dict
        Standard alert object; only ``candidate`` is used for photometry.
    survey : str
        "ZTF", "LSST", ... — selects the instrument, zeropoint and stream.
    session : sqlalchemy.ext.asyncio.AsyncSession
        Database session.
    user : User
        Owner of the ingested photometry.
    designation : str
        MPC designation, used as the object's identity.
    group_ids : list of int
        Groups the object is saved to.

    Returns
    -------
    dict
        ``{"id": obj_id}``.
    """
    from ..broker_apis._save import build_photometry_groups, programid_to_stream_ids
    from ..handlers.api.photometry import add_external_photometry
    from ..models import Instrument

    cand = data.get("candidate") or {}
    ra, dec = cand.get("ra"), cand.get("dec")
    obj_id = designation_to_obj_id(designation)

    instrument_id = await session.scalar(
        sa.select(Instrument.id).where(Instrument.name == survey)
    )
    if instrument_id is None:
        raise ValueError(f"Instrument '{survey}' not found in the database.")

    obj = await session.scalar(sa.select(Obj).where(Obj.id == obj_id))
    if obj is None:
        obj = Obj(id=obj_id, origin=survey)
        session.add(obj)

    obj.is_roid = True
    obj.mpc_name = designation
    # The position is only ever "where it was last seen", so stamp the epoch.
    if ra is not None and dec is not None:
        obj.ra, obj.dec = ra, dec
        obj.healpix = ha.constants.HPX.lonlat_to_healpix(ra * u.deg, dec * u.deg)
        altdata = dict(obj.altdata or {})
        altdata["last_detection_jd"] = cand.get("jd")
        separation = _first_value(data, SEPARATION_KEYS)
        if separation is not None:
            altdata["last_separation_arcsec"] = separation
        obj.altdata = altdata

    await session.flush()

    for group_id in group_ids or []:
        source = await session.scalar(
            sa.select(Source).where(
                Source.obj_id == obj_id, Source.group_id == group_id
            )
        )
        if source is None:
            session.add(
                Source(
                    obj_id=obj_id,
                    group_id=group_id,
                    saved_by_id=user.id,
                    active=True,
                )
            )
        else:
            source.active = True

    # Reuse the shared transform on the triggering detection alone, so units,
    # band naming and stream gating cannot drift from the sidereal path.
    if cand:
        programid2streamid = await programid_to_stream_ids(session)
        photometry_data = build_photometry_groups(
            obj_id,
            survey,
            {"prv_candidates": [cand]},
            instrument_id,
            programid2streamid,
        )
        for pd in photometry_data.values():
            if pd["mjd"]:
                await add_external_photometry(
                    pd, user, session, apply_default_share=False
                )

    await _link_designation(session, obj_id, designation)
    await session.commit()

    return {"id": obj_id}
