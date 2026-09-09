"""TESS sector footprints as SkyPortal instrument fields.

A sector's four cameras become four fields, so "is this target on silicon in
the current sector" is the healpix containment query SkyPortal already runs for
every other survey. The camera centres are derived from the published
spacecraft pointing table rather than a TESS-specific library: offsetting the
boresight by [-36, -12, 12, 36] degrees at position angle -roll reproduces the
official camera centres exactly.
"""

import functools
import json
import pathlib

import astropy.units as u
import numpy as np
from astropy.coordinates import SkyCoord
from astropy.time import Time

POINTINGS_FILE = pathlib.Path(__file__).parents[2] / "data" / "TESS_Pointings.json"

# field_id encodes the sector and camera, since InstrumentField has nowhere
# else to record which sector a footprint belongs to.
FIELD_ID_SECTOR_STRIDE = 10


def field_id_for(sector, camera):
    """The field_id standing for one sector's camera."""
    if not 1 <= camera <= 4:
        raise ValueError(f"camera must be 1-4, got {camera}")
    return sector * FIELD_ID_SECTOR_STRIDE + camera


def sector_of(field_id):
    """The sector a field_id belongs to."""
    return field_id // FIELD_ID_SECTOR_STRIDE


@functools.lru_cache(maxsize=1)
def pointings():
    """The published spacecraft pointing per sector."""
    with open(POINTINGS_FILE) as f:
        return json.load(f)


def sector_window(sector):
    """(start, end) of a sector's observing window as astropy Times."""
    table = pointings()
    row = next((p for p in table["pointings"] if p["sector"] == sector), None)
    if row is None:
        return None
    half = table["sector_duration_days"] / 2
    mid = Time(row["midtime_jd"], format="jd")
    return mid - half * u.day, mid + half * u.day


def current_sector(when=None):
    """The sector observing at `when` (default now), or None between sectors.

    Sectors do not tile time continuously -- there is a downlink gap between
    them -- so this legitimately returns None.
    """
    when = Time(when) if when is not None else Time.now()
    table = pointings()
    half = table["sector_duration_days"] / 2
    for row in table["pointings"]:
        if abs((when - Time(row["midtime_jd"], format="jd")).to_value("day")) <= half:
            return row["sector"]
    return None


def camera_pointings(sector):
    """Centre and roll of each of a sector's four cameras.

    Returns a list of (camera, ra, dec, rotation) with angles in degrees.
    """
    table = pointings()
    row = next((p for p in table["pointings"] if p["sector"] == sector), None)
    if row is None:
        return []

    boresight = SkyCoord(row["ra"] * u.deg, row["dec"] * u.deg)
    # Position angle -roll along the great circle the cameras sit on.
    position_angle = -row["roll"] * u.deg
    out = []
    for camera, offset in enumerate(table["camera_offsets_deg"], start=1):
        centre = boresight.directional_offset_by(position_angle, offset * u.deg)
        # The footprint is square, so its orientation only matters modulo 90
        # degrees; the angle back along the great circle fixes it.
        rotation = centre.position_angle(boresight).to_value(u.deg)
        out.append(
            (
                camera,
                float(centre.ra.deg),
                float(centre.dec.deg),
                float(np.mod(rotation, 90.0)),
            )
        )
    return out


def camera_region():
    """The camera footprint to tile, as a region for the instrument POST."""
    from regions import RectangleSkyRegion

    fov = pointings()["camera_fov_deg"] * u.deg
    return RectangleSkyRegion(
        center=SkyCoord(0 * u.deg, 0 * u.deg), width=fov, height=fov
    )


def field_data(sectors):
    """`field_data` for POSTing these sectors' cameras as instrument fields."""
    ids, ras, decs, rotations = [], [], [], []
    for sector in sectors:
        for camera, ra, dec, rotation in camera_pointings(sector):
            ids.append(field_id_for(sector, camera))
            ras.append(ra)
            decs.append(dec)
            rotations.append(rotation)
    return {"ID": ids, "RA": ras, "Dec": decs, "rotation": rotations}


INSTRUMENT_NAME = "TESS"
ANNOTATION_ORIGIN = "tess-sector"


def all_sectors():
    """Every sector the pointing table knows about, in order."""
    return [row["sector"] for row in pointings()["pointings"]]


def missing_field_data(existing_field_ids):
    """`field_data` for the sectors that have no fields yet.

    Loading is incremental: publishing a new sector means adding it to the
    pointing table, and the next run fills in its four cameras.
    """
    existing = set(existing_field_ids)
    wanted = [
        sector
        for sector in all_sectors()
        if any(field_id_for(sector, camera) not in existing for camera in range(1, 5))
    ]
    return field_data(wanted) if wanted else None


def annotation_data(sectors, when=None):
    """What to record about a position's TESS coverage.

    `observed` answers the scanning question -- has TESS ever pointed here --
    while `current_sector` answers whether it is pointing here now.
    """
    now = current_sector(when)
    return {
        "sectors": sectors,
        "observed": bool(sectors),
        "current_sector": now if now in sectors else None,
        "in_current_sector": now is not None and now in sectors,
    }
