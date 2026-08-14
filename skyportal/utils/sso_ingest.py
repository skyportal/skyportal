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

Opt in by setting ``altdata['sso']`` on a Filter; its passing alerts route here
and are saved to that Filter's group. The filter must actually *pass* the
alerts: brokers publish only filter-passing alerts, and transient filters are
built to reject asteroids, so without one this sees nothing.
"""

import re

import astropy.units as u
import healpix_alchemy as ha
import sqlalchemy as sa
from sqlalchemy.orm import selectinload

from baselayer.log import make_log

from ..models import Candidate, Obj, Source, SuperObj
from .naive_datetime import utcnow_naive

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

# Bare designations are often plain integers, which read as an id from anywhere.
# The alias and SuperObj name carry a marker so one query finds every
# solar-system object; `mpc_name` keeps the canonical designation.
ALIAS_PREFIX = "SSO"


def sso_label(designation):
    """The prefixed label used for both an Obj's alias and its SuperObj name."""
    return f"{ALIAS_PREFIX} {designation}"


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


def _first_value(data, keys, annotations_by_filter_id=None):
    """First present value for `keys`.

    Searched wherever a designation can arrive, since the rest of the `sso`
    block travels with it: on the alert, or in a filter's annotations.
    """
    properties = (data or {}).get("properties") or {}
    mappings = [properties.get("sso"), properties, (data or {}).get("candidate")]
    for annotations in (annotations_by_filter_id or {}).values():
        if isinstance(annotations, dict):
            mappings += [annotations.get("sso"), annotations]

    for mapping in mappings:
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


def sso_filter_targets(filters):
    """Map Filter id -> group id to auto-save to, or None to only scan.

    Built once when a broker's ingestion loop starts, so the per-alert check is
    a lookup rather than a query. `autosave` keeps its usual meaning: without it
    the object is a candidate to scan rather than a saved source, which is what
    someone filtering for, say, active asteroids wants instead of every
    designation the survey sees.
    """
    return {
        f.id: (f.group_id if f.autosave else None)
        for f in filters
        if (f.altdata or {}).get("sso")
    }


def sso_routing_for(filter_ids, sso_targets):
    """(filter ids, group ids) an alert routes to, given the filters it passed.

    Empty filter ids mean no passing filter opted in, so the alert takes the
    normal sidereal path even if it does carry a designation.
    """
    matched = [fid for fid in filter_ids or [] if fid in sso_targets]
    group_ids = sorted({sso_targets[fid] for fid in matched} - {None})
    return matched, group_ids


# Alert and photometry JDs come from the same source, so they should match
# exactly; allow ~0.1s of slack against float round-tripping.
_JD_TOLERANCE = 1e-6


def triggering_detection(data):
    """The alert's own detection, picked out of the position-keyed history.

    Providers differ: some put the detection in ``candidate``, while BOOM's
    normalized alert leaves only ``ra``/``dec``/``drb`` there and carries the
    real photometry in ``prv_candidates``, identified by the alert's own JD.
    """
    cand = data.get("candidate") or {}
    if cand.get("jd") is not None and cand.get("band") is not None:
        return cand

    jd = data.get("jd", cand.get("jd"))
    if jd is None:
        return None
    for point in data.get("prv_candidates") or []:
        if point.get("jd") is not None and abs(point["jd"] - jd) <= _JD_TOLERANCE:
            return point
    return None


async def _link_designation(session, obj_id, designation):
    """Link this detection stream to any other Obj for the same body."""
    # Eager-load: touching a lazy collection under an async session raises.
    super_obj = await session.scalar(
        sa.select(SuperObj)
        .options(selectinload(SuperObj.objs))
        .where(SuperObj.name == sso_label(designation))
    )
    obj = await session.scalar(sa.select(Obj).where(Obj.id == obj_id))

    if super_obj is None:
        # Populate at construction: a flushed-then-read collection lazy-loads.
        session.add(
            SuperObj(
                name=sso_label(designation), is_roid=True, objs=[obj] if obj else []
            )
        )
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
    filter_ids=None,
    passing_alert_id=None,
    annotations_by_filter_id=None,
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
        Groups the object is saved to as a Source.
    filter_ids : list of int, optional
        Filters to register the object as a Candidate under, so it can be
        scanned rather than saved outright.
    passing_alert_id : optional
        Alert id the Candidate rows dedupe on across re-consumption.
    annotations_by_filter_id : dict, optional
        Each passing filter's annotations, which may carry the `sso` fields when
        the alert itself does not.

    Returns
    -------
    dict
        ``{"id": obj_id}``.
    """
    from ..broker_apis._save import build_photometry_groups, programid_to_stream_ids
    from ..handlers.api.photometry import add_external_photometry
    from ..models import Instrument

    cand = data.get("candidate") or {}
    detection = triggering_detection(data) or {}
    # Prefer the detection's own astrometry; fall back to the alert's.
    ra = detection.get("ra") if detection.get("ra") is not None else cand.get("ra")
    dec = detection.get("dec") if detection.get("dec") is not None else cand.get("dec")
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
    alias = sso_label(designation)
    aliases = set(obj.alias or [])
    if alias not in aliases:
        obj.alias = sorted(aliases | {alias})
    # The position is only ever "where it was last seen", so stamp the epoch.
    if ra is not None and dec is not None:
        obj.ra, obj.dec = ra, dec
        obj.healpix = ha.constants.HPX.lonlat_to_healpix(ra * u.deg, dec * u.deg)
        altdata = dict(obj.altdata or {})
        altdata["last_detection_jd"] = detection.get("jd", data.get("jd"))
        separation = _first_value(data, SEPARATION_KEYS, annotations_by_filter_id)
        if separation is not None:
            altdata["last_separation_arcsec"] = separation
        obj.altdata = altdata

    await session.flush()

    for filter_id in filter_ids or []:
        exists = await session.scalar(
            sa.select(Candidate).where(
                Candidate.obj_id == obj_id,
                Candidate.filter_id == filter_id,
                Candidate.passing_alert_id == passing_alert_id,
            )
        )
        if exists is None:
            session.add(
                Candidate(
                    obj_id=obj_id,
                    filter_id=filter_id,
                    passed_at=utcnow_naive(),
                    passing_alert_id=passing_alert_id,
                    uploader_id=user.id,
                )
            )

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
    if detection:
        programid2streamid = await programid_to_stream_ids(session)
        photometry_data = build_photometry_groups(
            obj_id,
            survey,
            {"prv_candidates": [detection]},
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
