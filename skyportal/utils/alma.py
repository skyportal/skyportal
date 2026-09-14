"""ALMA archive coverage for a position.

Querying the archive is cheap, so this runs in an ordinary service and records
what ALMA has observed as an annotation. Reducing any of it is not cheap, and
belongs in an analysis service; the annotation carries the dataset identifiers
that such a service would go and fetch.
"""

ANNOTATION_ORIGIN = "alma-archive"

# The archive returns ~73 columns; these are the ones worth keeping.
COLUMNS = (
    "obs_id",
    "target_name",
    "member_ous_uid",
    "proposal_id",
    "band_list",
    "frequency",
    "spatial_resolution",
    "velocity_resolution",
    "t_exptime",
    "obs_release_date",
)

# An annotation is read by people and sent whole to analysis services, so the
# dataset list is capped rather than carrying every execution block.
MAX_DATASETS = 25


def _numbers(rows, key):
    out = []
    for row in rows:
        value = row.get(key)
        try:
            value = float(value)
        except (TypeError, ValueError):
            continue
        if value == value:  # not NaN
            out.append(value)
    return out


def _bands(rows):
    bands = set()
    for row in rows:
        raw = row.get("band_list")
        if raw is None:
            continue
        # The archive gives a band list as "3" or "3 6".
        for part in str(raw).replace(",", " ").split():
            try:
                bands.add(int(float(part)))
            except ValueError:
                continue
    return sorted(bands)


def summarize(rows, ra=None, dec=None, radius_arcsec=None):
    """Turn archive rows into the annotation recorded against an object.

    `datasets` is what an analysis service would go and fetch; the rest is what
    makes the coverage legible without leaving SkyPortal.
    """
    rows = list(rows or [])
    frequencies = _numbers(rows, "frequency")
    resolutions = _numbers(rows, "spatial_resolution")
    velocities = _numbers(rows, "velocity_resolution")
    exposures = _numbers(rows, "t_exptime")

    datasets = []
    for row in rows:
        uid = row.get("member_ous_uid")
        if uid and uid not in datasets:
            datasets.append(uid)

    proposals = sorted({row["proposal_id"] for row in rows if row.get("proposal_id")})
    targets = sorted({row["target_name"] for row in rows if row.get("target_name")})
    releases = sorted(
        {row["obs_release_date"] for row in rows if row.get("obs_release_date")}
    )

    return {
        "observed": bool(rows),
        "n_observations": len(rows),
        "bands": _bands(rows),
        "frequency_ghz": (
            [min(frequencies), max(frequencies)] if frequencies else None
        ),
        # Smaller is finer, for both of these.
        "best_spatial_resolution_arcsec": min(resolutions) if resolutions else None,
        "best_velocity_resolution_m_s": min(velocities) if velocities else None,
        "total_exposure_s": sum(exposures) if exposures else None,
        "proposals": proposals,
        "targets": targets,
        "first_release": releases[0] if releases else None,
        "last_release": releases[-1] if releases else None,
        "datasets": datasets[:MAX_DATASETS],
        "datasets_truncated": len(datasets) > MAX_DATASETS,
        # What was asked of the archive, so the coverage can be read in context
        # and requeried at a different radius.
        "query": {"ra": ra, "dec": dec, "radius_arcsec": radius_arcsec},
    }


def query_coverage(ra, dec, radius_arcsec=30.0, public_only=True, science_only=True):
    """Rows the ALMA archive holds within `radius_arcsec` of a position."""
    import astropy.units as u
    from astropy.coordinates import SkyCoord
    from astroquery.alma import Alma

    table = Alma.query_region(
        SkyCoord(ra * u.deg, dec * u.deg),
        radius_arcsec * u.arcsec,
        public=public_only,
        science=science_only,
    )
    rows = []
    for row in table:
        entry = {}
        for column in COLUMNS:
            if column in table.colnames:
                value = row[column]
                entry[column] = value.item() if hasattr(value, "item") else value
        rows.append(entry)
    return rows
