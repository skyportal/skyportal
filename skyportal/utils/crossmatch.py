"""Geometry helpers for crossmatching broker alerts against GCN localizations.

Brokers expose positional alert search as a cone (ra, dec, radius), so every
localization has to be reduced to a cone before it can be queried. That cone is
only ever used to *over*-select: whatever comes back is then filtered for real
containment against the localization's HEALPix tiles, the same mechanism the
``localizationDateobs`` source query uses.

The asymmetry matters. An over-large cone costs extra broker work and is
harmless; an under-large cone silently drops true matches with nothing in the
logs to say so. Every path here therefore either returns a provable upper bound
or refuses to return anything at all.
"""

import json

import numpy as np
import sqlalchemy as sa
from astropy import units as u
from healpix_alchemy.constants import HPX, PIXEL_AREA

from baselayer.log import make_log

log = make_log("crossmatch")

# Contour credible level to bound the search cone with. get_contour() writes
# levels 50 and 90, so 90 is the widest available.
DEFAULT_CREDIBLE_LEVEL = 90

# Cumulative probability defining the credible region for containment, matching
# the localizationCumprob default on the source query.
DEFAULT_CUMPROB = 0.95


def great_circle_distance(ra1_deg, dec1_deg, ra2_deg, dec2_deg):
    """Angular separation in degrees, vectorized over the second position.

    Ported from the ep-ztf-xmatch service, which used it in preference to
    astropy's SkyCoord.separation for being orders of magnitude faster on the
    per-alert path.
    """
    delta_ra = np.radians(np.abs(np.asarray(ra2_deg) - ra1_deg))
    dec1 = np.radians(dec1_deg)
    dec2 = np.radians(np.asarray(dec2_deg))
    return np.degrees(
        np.arctan2(
            np.sqrt(
                (np.cos(dec2) * np.sin(delta_ra)) ** 2
                + (
                    np.cos(dec1) * np.sin(dec2)
                    - np.sin(dec1) * np.cos(dec2) * np.cos(delta_ra)
                )
                ** 2
            ),
            np.sin(dec1) * np.sin(dec2)
            + np.cos(dec1) * np.cos(dec2) * np.cos(delta_ra),
        )
    )


def cone_from_localization_name(localization_name):
    """(ra, dec, radius_deg) for a cone localization, or None.

    Cone localizations are named ``{ra:.5f}_{dec:.5f}_{error:.5f}`` by
    ``from_cone``; ``Localization.center`` relies on the same convention, so this
    is the model's own encoding rather than a guess. Anything that does not parse
    as three floats is a real skymap.
    """
    if not localization_name:
        return None
    parts = str(localization_name).split("_")
    if len(parts) != 3:
        return None
    try:
        ra, dec, radius = (float(p) for p in parts)
    except ValueError:
        return None
    if not (0.0 <= ra <= 360.0 and -90.0 <= dec <= 90.0 and radius >= 0.0):
        return None
    return ra, dec, radius


def _iter_contour_positions(geometry):
    """Yield (ra, dec) from a GeoJSON geometry of any nesting depth."""
    coords = geometry.get("coordinates")
    if coords is None:
        return

    def walk(node):
        if (
            isinstance(node, (list, tuple))
            and len(node) == 2
            and all(isinstance(v, (int, float)) for v in node)
        ):
            yield float(node[0]), float(node[1])
            return
        if isinstance(node, (list, tuple)):
            for child in node:
                yield from walk(child)

    yield from walk(coords)


def cone_from_contour(contour, credible_level=DEFAULT_CREDIBLE_LEVEL):
    """(ra, dec, radius_deg) bounding a localization's credible contour, or None.

    ``get_contour`` stores a FeatureCollection holding a ``credible_level: 0``
    Point at the posterior maximum plus MultiLineString features per level. The
    radius returned is the greatest separation between that centre and any
    vertex of the requested contour, so the cone provably contains that credible
    region -- no assumption that the region is circular, which matters for the
    elongated localizations where an area-derived radius would under-cover.
    """
    if not contour:
        return None
    if isinstance(contour, str):
        try:
            contour = json.loads(contour)
        except ValueError:
            return None

    features = contour.get("features") or []
    center = None
    positions = []
    for feature in features:
        level = (feature.get("properties") or {}).get("credible_level")
        geometry = feature.get("geometry") or {}
        if level == 0 and geometry.get("type") == "Point":
            coords = geometry.get("coordinates") or []
            if len(coords) == 2:
                center = (float(coords[0]), float(coords[1]))
        elif level == credible_level:
            positions.extend(_iter_contour_positions(geometry))

    if center is None or not positions:
        return None

    ras = [p[0] for p in positions]
    decs = [p[1] for p in positions]
    radius = float(np.max(great_circle_distance(center[0], center[1], ras, decs)))
    return center[0], center[1], radius


def search_cone(
    localization, max_radius_deg=None, credible_level=DEFAULT_CREDIBLE_LEVEL
):
    """Reduce a Localization to a search cone, or None if it cannot be bounded.

    Returns
    -------
    (ra, dec, radius_deg) or None
        None means "do not query": either the localization cannot be bounded
        (no parseable name and no contour) or its bound exceeds
        ``max_radius_deg``. Returning None is deliberate -- guessing a radius
        here would drop real matches without a trace.
    """
    cone = cone_from_localization_name(localization.localization_name)
    source = "localization_name"
    if cone is None:
        cone = cone_from_contour(localization.contour, credible_level=credible_level)
        source = f"contour(level={credible_level})"

    if cone is None:
        log(
            f"Localization {localization.id} ({localization.localization_name}) has "
            f"neither a cone name nor a usable contour; skipping rather than "
            f"guessing a search radius"
        )
        return None

    ra, dec, radius = cone
    if max_radius_deg is not None and radius > max_radius_deg:
        log(
            f"Localization {localization.id} ({localization.localization_name}) "
            f"bounds to {radius:.3f} deg via {source}, over the "
            f"{max_radius_deg:.3f} deg limit; skipping"
        )
        return None

    return ra, dec, radius


async def contained_in_localization(
    session, localization, positions, cumprob=DEFAULT_CUMPROB
):
    """Indices of ``positions`` that fall inside a localization's credible region.

    ``positions`` is a sequence of (ra, dec) in degrees. Cone localizations are
    resolved analytically; everything else is resolved against the stored
    HEALPix tiles using the same cumulative-probability containment the
    ``localizationDateobs`` source query uses, so the two agree on what "inside
    the 95% region" means.

    Returns a set of indices into ``positions``.
    """
    if not positions:
        return set()

    cone = cone_from_localization_name(localization.localization_name)
    if cone is not None:
        ra0, dec0, radius = cone
        seps = great_circle_distance(
            ra0, dec0, [p[0] for p in positions], [p[1] for p in positions]
        )
        return {i for i, sep in enumerate(np.atleast_1d(seps)) if sep <= radius}

    # Multi-order skymap: convert each position to a level-29 nested HEALPix
    # index and ask which credible-region tiles contain it. One round trip for
    # the whole batch rather than one per alert.
    indices = HPX.lonlat_to_healpix(
        np.asarray([p[0] for p in positions]) * u.deg,
        np.asarray([p[1] for p in positions]) * u.deg,
    )

    result = await session.execute(
        sa.text(
            """
            WITH tiles AS (
                SELECT
                    healpix,
                    SUM(
                        probdensity
                        * (upper(healpix) - lower(healpix))
                        * :pixel_area
                    ) OVER (ORDER BY probdensity DESC) AS cum_prob
                FROM localizationtiles
                WHERE localization_id = :localization_id
                  AND dateobs = :dateobs
            )
            SELECT DISTINCT p.idx
            FROM unnest(CAST(:idxs AS bigint[]), CAST(:hpxs AS bigint[]))
                 AS p(idx, hpx)
            JOIN tiles ON tiles.healpix @> p.hpx
            WHERE tiles.cum_prob <= :cumprob
            """
        ),
        {
            "localization_id": localization.id,
            "dateobs": localization.dateobs,
            "pixel_area": PIXEL_AREA,
            "cumprob": cumprob,
            "idxs": list(range(len(positions))),
            "hpxs": [int(i) for i in np.atleast_1d(indices)],
        },
    )
    return {row[0] for row in result}
