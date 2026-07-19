"""Shared save-as-source machinery for broker providers.

Turning a broker alert/object into an skyportal Obj + Source + photometry is
survey-dependent (zeropoint, instrument, stream), not broker-dependent — every
provider that yields a standard alert object (candidate + prv_candidates /
prv_nondetections / fp_hists, with psfFlux/band/jd) shares this exact logic. A
provider's ``save_as_source`` should fetch the object and delegate here.
"""

from baselayer.log import make_log

log = make_log("broker/save")

# AB zeropoint per survey (psfFlux is in Jy after the 1e-9 scaling below).
ZP_PER_SURVEY = {"LSST": 8.9, "ZTF": 23.9}

# A "detection" must clear this S/N unless a Filter's criteria override it. Broker
# science topics/filters are often broad, so a Filter can carry an extra criteria
# gate (see _passes_criteria) that alerts must satisfy before becoming Candidates.
_DEFAULT_MIN_SNR = 5.0
# sigma_mag = 2.5/ln(10) / SNR, so SNR = (2.5/ln(10)) / sigma_mag in mag space.
_MAG_SNR_CONST = 1.0857362


def _point_snr(p):
    """S/N of a photometry point, handling both flux-space (psfFlux/psfFluxErr,
    e.g. BOOM/LSST) and mag-space (magpsf/sigmapsf, e.g. Fink ZTF) normalizations.
    Returns None for a non-detection / upper limit (no usable flux or error)."""
    flux, flux_err = p.get("psfFlux"), p.get("psfFluxErr")
    if flux is not None and flux_err:
        return abs(flux) / flux_err
    mag, mag_err = p.get("magpsf"), p.get("sigmapsf")
    if mag is not None and mag_err:
        return _MAG_SNR_CONST / mag_err
    return None


def _normalize_band(band):
    """Collapse survey-prefixed band names to a bare filter letter so per-band
    criteria are provider-agnostic (``ztfg`` -> ``g``, ``g`` -> ``g``)."""
    b = str(band or "").lower()
    for prefix in ("ztf", "lsst", "atlas"):
        if b.startswith(prefix) and len(b) > len(prefix):
            return b[len(prefix) :].lstrip("_")
    return b


def _passes_criteria(data, criteria):
    """Whether an alert satisfies a Filter's optional ingestion ``criteria``
    (stored in ``Filter.altdata['criteria']``). An absent/empty block passes, so
    existing filters are unaffected. Supported keys:

      * ``min_snr`` (default 5): S/N a point needs to count as a detection.
      * ``min_detections`` (default 1): total qualifying detections.
      * ``min_detections_per_band``: ``{band: n}`` (bands normalized, e.g. ``g``).
      * ``min_time_baseline``: min days between first and last qualifying detection.
    """
    if not criteria:
        return True
    min_snr = float(criteria.get("min_snr", _DEFAULT_MIN_SNR))
    detections = [
        p
        for p in (data.get("prv_candidates") or [])
        if (snr := _point_snr(p)) is not None and snr >= min_snr
    ]
    if len(detections) < int(criteria.get("min_detections", 1)):
        return False
    per_band = criteria.get("min_detections_per_band") or {}
    if per_band:
        from collections import Counter

        counts = Counter(_normalize_band(p.get("band")) for p in detections)
        for band, need in per_band.items():
            if counts.get(_normalize_band(band), 0) < int(need):
                return False
    min_baseline = criteria.get("min_time_baseline")
    if min_baseline is not None:
        jds = [p.get("jd") for p in detections if p.get("jd") is not None]
        if len(jds) < 2 or (max(jds) - min(jds)) < float(min_baseline):
            return False
    return True


async def _filters_passing_criteria(session, filter_ids, data):
    """Subset of ``filter_ids`` whose Filter criteria the alert satisfies (a
    filter with no criteria always passes)."""
    import sqlalchemy as sa

    from ..models import Filter

    rows = (
        await session.scalars(sa.select(Filter).where(Filter.id.in_(filter_ids)))
    ).all()
    criteria_by_id = {f.id: (f.altdata or {}).get("criteria") for f in rows}
    return [
        fid for fid in filter_ids if _passes_criteria(data, criteria_by_id.get(fid))
    ]


async def programid_to_stream_ids(session):
    """Map (survey, programid) -> [stream_id] from each Stream's altdata."""
    import sqlalchemy as sa

    from ..models import Stream

    streams = (await session.scalars(sa.select(Stream))).all()
    mapper: dict = {}
    for stream in streams:
        altdata = stream.altdata or {}
        if "collection" not in altdata or "selector" not in altdata:
            continue
        key = (altdata["collection"].split("_")[0], max(altdata["selector"]))
        mapper.setdefault(key, []).append(stream.id)
    return mapper


def build_photometry_groups(object_id, survey, data, instrument_id, programid2streamid):
    """Transform a standard alert object's photometry arrays into per-(survey,
    programid) groups in skyportal units, keyed by the stream that gates them.

    Pure (no I/O), so the persisting path and the read-only passthrough
    (``_photometry.py``) share one transform and cannot drift: what a
    passthrough displays is exactly what a save would have written.
    """
    import numpy as np

    zp = ZP_PER_SURVEY.get(survey)
    if zp is None:
        raise ValueError(f"No zeropoint configured for survey '{survey}'.")

    photometry_data: dict = {}
    for array_name in ["prv_candidates", "prv_nondetections", "fp_hists"]:
        for phot in data.get(array_name) or []:
            jd, band = phot.get("jd"), phot.get("band")
            if jd is None or band is None:
                continue

            # Flux space (psfFlux, e.g. BOOM/babamul) or magnitude space
            # (magpsf, e.g. Lasair) — a source is homogeneous either way.
            flux_err = phot.get("psfFluxErr")
            if flux_err is not None:
                flux = phot.get("psfFlux")
                flux_err *= 1e-9
                if flux is not None and not np.isnan(flux):
                    flux *= 1e-9
                    if not np.isnan(flux_err) and abs(flux) / flux_err <= 3:
                        flux = np.nan
                columns = {"flux": flux, "fluxerr": flux_err, "zp": zp}
            elif phot.get("magpsf") is not None and phot.get("sigmapsf") is not None:
                # Magnitude space (e.g. Lasair): convert to flux with the survey
                # zeropoint so it flows through the flux path (skyportal's mag path
                # also requires a limiting_mag, which these brokers don't provide).
                # mag = -2.5*log10(flux) + zp, so flux = 10**(-0.4*(mag - zp)).
                mag, magerr = phot["magpsf"], phot["sigmapsf"]
                flux = 10.0 ** (-0.4 * (mag - zp))
                flux_err = flux * magerr * 0.9210340371976184  # ln(10)/2.5
                columns = {"flux": flux, "fluxerr": flux_err, "zp": zp}
            else:
                continue

            programid = phot.get("programid", 1) if survey == "ZTF" else 1
            key = (survey, programid)
            if key not in photometry_data:
                stream_ids = programid2streamid.get(key)
                if not stream_ids:
                    continue
                photometry_data[key] = {
                    "obj_id": object_id,
                    "stream_ids": stream_ids,
                    "instrument_id": instrument_id,
                    "mjd": [],
                    "filter": [],
                    "magsys": [],
                    "ra": [],
                    "dec": [],
                    **{col: [] for col in columns},
                }
            pd = photometry_data[key]
            pd["mjd"].append(jd - 2400000.5)
            pd["filter"].append(f"{survey.lower()}{str(band).lower()}")
            pd["magsys"].append("ab")
            pd["ra"].append(phot.get("ra"))
            pd["dec"].append(phot.get("dec"))
            for col, value in columns.items():
                pd.setdefault(col, []).append(value)

    return photometry_data


async def _ingest_object(
    data,
    survey,
    session,
    user,
    *,
    group_ids=None,
    filter_ids=None,
    passing_alert_id=None,
    cutouts=None,
):
    """Create/refresh an Obj for ``data`` (a standard alert object), attach it to
    groups (as a Source) and/or filters (as a Candidate), and ingest its
    photometry. Returns ``{"id": object_id}``.

    Shared by the interactive save-as-source path (``group_ids``) and the
    ingestion path (``filter_ids`` + ``passing_alert_id``).

    Parameters
    ----------
    data : dict
        Alert object with ``objectId``, ``candidate``, and any of
        ``prv_candidates`` / ``prv_nondetections`` / ``fp_hists``.
    survey : str
        "ZTF", "LSST", ... — selects the instrument, zeropoint, and stream.
    cutouts : dict, optional
        ``{cutoutScience, cutoutTemplate, cutoutDifference}`` FITS payloads, if
        the provider supplies them, rendered into science/template/diff thumbnails.
    """
    import sqlalchemy as sa

    from ..handlers.api.photometry import add_external_photometry
    from ..models import Candidate, Group, Instrument, Obj, Source
    from ..utils.naive_datetime import utcnow_naive

    object_id = data["objectId"]
    cand = data.get("candidate") or {}

    # Ingestion criteria gate: drop the alert against filters whose extra criteria
    # it fails. If nothing survives and this isn't an interactive save (group_ids),
    # skip before writing any Obj/Candidate/photometry.
    if filter_ids:
        filter_ids = await _filters_passing_criteria(session, filter_ids, data)
        if not filter_ids and not group_ids:
            return {"id": object_id}

    instrument_id = await session.scalar(
        sa.select(Instrument.id).where(Instrument.name == survey)
    )
    if instrument_id is None:
        raise ValueError(f"Instrument '{survey}' not found in the database.")

    programid2streamid = await programid_to_stream_ids(session)

    obj = await session.scalar(sa.select(Obj).where(Obj.id == object_id))
    created = obj is None
    if created:
        obj = Obj(
            id=object_id,
            ra=cand.get("ra"),
            dec=cand.get("dec"),
            ra_dis=cand.get("ra"),
            dec_dis=cand.get("dec"),
            score=cand.get("drb"),
            origin=survey,
        )
        session.add(obj)

    # Save-as-source: attach to groups (only meaningful on first save).
    if group_ids:
        groups = (
            await session.scalars(sa.select(Group).where(Group.id.in_(group_ids)))
        ).all()
        if len(groups) != len(set(group_ids)):
            raise ValueError("Some group_ids do not exist or are not accessible.")
        if created:
            for g in groups:
                session.add(Source(obj=obj, group=g, saved_by_id=user.id))

    # Ingestion: register as a Candidate under each filter, deduped on the passing
    # alert (the same alert may be re-consumed).
    if filter_ids:
        for fid in filter_ids:
            exists = await session.scalar(
                sa.select(Candidate).where(
                    Candidate.obj_id == object_id,
                    Candidate.filter_id == fid,
                    Candidate.passing_alert_id == passing_alert_id,
                )
            )
            if exists is None:
                session.add(
                    Candidate(
                        obj=obj,
                        filter_id=fid,
                        passed_at=utcnow_naive(),
                        passing_alert_id=passing_alert_id,
                        uploader_id=user.id,
                    )
                )

    # autoflush is off on skyportal's async session; flush so the new Obj (and any
    # Candidate rows) are visible to add_external_photometry's existence check.
    if created or filter_ids:
        await session.flush()

    photometry_data = build_photometry_groups(
        object_id, survey, data, instrument_id, programid2streamid
    )

    for pd in photometry_data.values():
        if pd["mjd"]:  # never post empty photometry (breaks JSON coercion)
            await add_external_photometry(pd, user, session)

    # Best-effort science/template/difference thumbnails if the provider gave us
    # the cutouts.
    if cutouts:
        try:
            from ._thumbnails import add_thumbnails

            await add_thumbnails(object_id, cutouts, survey, session, user_id=user.id)
        except Exception as e:
            log(f"Failed to add thumbnails for {object_id}: {e}")

    await session.commit()
    return {"id": object_id}


async def save_object_as_source(data, survey, session, user, group_ids, cutouts=None):
    """Interactive save: create an Obj + Source(s) under ``group_ids`` and ingest
    photometry. A provider's ``save_as_source`` delegates here."""
    return await _ingest_object(
        data, survey, session, user, group_ids=group_ids, cutouts=cutouts
    )


async def save_object_as_candidate(
    data, survey, session, user, filter_ids, passing_alert_id=None, cutouts=None
):
    """Ingestion save: create/refresh an Obj, register it as a Candidate under each
    of ``filter_ids`` (deduped on ``passing_alert_id``), and ingest photometry."""
    return await _ingest_object(
        data,
        survey,
        session,
        user,
        filter_ids=filter_ids,
        passing_alert_id=passing_alert_id,
        cutouts=cutouts,
    )
