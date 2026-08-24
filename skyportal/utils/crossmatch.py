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
from skyportal.utils.calculations import gaussian_sigmas_for

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
    if cone is not None:
        # The name carries 1 sigma, which holds only 39% of the probability.
        ra, dec, sigma = cone
        cone = (ra, dec, sigma * gaussian_sigmas_for(credible_level / 100.0))
        source = f"localization_name(level={credible_level})"
    else:
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


async def credible_levels_in_localization(
    session, localization, positions, cumprob=DEFAULT_CUMPROB
):
    """``{index: credible_level}`` for the positions inside ``cumprob``.

    The level is the smallest credible region containing the position: 0.05 is
    the best-localized 5% of the probability, 0.88 barely made a 90% cut.
    Containment is unchanged; this keeps how deep inside each match sits.

    ``positions`` is a sequence of (ra, dec) in degrees. Cone localizations are
    resolved analytically, everything else against the stored HEALPix tiles.
    """
    if not positions:
        return {}

    cone = cone_from_localization_name(localization.localization_name)
    if cone is not None:
        ra0, dec0, radius = cone
        seps = great_circle_distance(
            ra0, dec0, [p[0] for p in positions], [p[1] for p in positions]
        )
        if not radius:
            return {i: 0.0 for i, sep in enumerate(np.atleast_1d(seps)) if sep <= 0}
        # from_cone lays down a Gaussian of sigma = the error radius, so the
        # enclosed probability at r is the Rayleigh CDF -- the same distribution
        # the tiles carry, in closed form.
        levels = 1.0 - np.exp(-0.5 * (np.atleast_1d(seps) / radius) ** 2)
        return {
            i: float(round(level, 6))
            for i, level in enumerate(levels)
            if level <= cumprob
        }

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
            SELECT p.idx, MIN(tiles.cum_prob)
            FROM unnest(CAST(:idxs AS bigint[]), CAST(:hpxs AS bigint[]))
                 AS p(idx, hpx)
            JOIN tiles ON tiles.healpix @> p.hpx
            WHERE tiles.cum_prob <= :cumprob
            GROUP BY p.idx
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
    return {row[0]: float(round(row[1], 6)) for row in result}


async def contained_in_localization(
    session, localization, positions, cumprob=DEFAULT_CUMPROB
):
    """Indices of ``positions`` that fall inside a localization's credible region.

    Returns a set of indices into ``positions``. See
    ``credible_levels_in_localization`` for the same containment with the
    credible level of each match kept.
    """
    return set(
        await credible_levels_in_localization(
            session, localization, positions, cumprob=cumprob
        )
    )


def _uniq_ranges(uniq, probdensity):
    """A multi-order map as sorted level-29 ranges: (start, end, probdensity).

    UNIQ packs a level and a pixel index into one integer; expanding each cell
    to the level-29 range it covers puts two maps of different resolutions on a
    common axis without rasterizing either.
    """
    uniq = np.asarray(uniq, dtype=np.int64)
    density = np.asarray(probdensity, dtype=float)
    level = (np.log2(uniq / 4) / 2).astype(np.int64)
    ipix = uniq - 4 * (4**level)
    shift = 2 * (29 - level)
    start = np.left_shift(ipix, shift)
    end = np.left_shift(ipix + 1, shift)
    order = np.argsort(start)
    return start[order], end[order], density[order]


def _density_on_segments(start, end, density, seg_start):
    """The map's probdensity on each segment, 0 where the map has no cell."""
    idx = np.searchsorted(start, seg_start, side="right") - 1
    inside = (idx >= 0) & (end[np.clip(idx, 0, None)] > seg_start)
    return np.where(inside, density[np.clip(idx, 0, None)], 0.0)


def skymap_overlap_integral(loc1, loc2):
    """RAVEN's sky-map overlap integral for two localizations.

    ``I = 4 pi * integral(p1 * p2) dOmega``: 1 when the two maps are unrelated,
    large when they agree, 0 when they are disjoint. Dimensionless, so it can be
    compared across pairs, and it is the spatial term of the RAVEN joint FAR.

    Both maps are expanded to level-29 ranges and integrated on the segments
    where they overlap -- the cost follows the number of cells, not the
    resolution, so a full-sky rasterization is never materialized.
    """
    a_start, a_end, a_density = _uniq_ranges(loc1.uniq, loc1.probdensity)
    b_start, b_end, b_density = _uniq_ranges(loc2.uniq, loc2.probdensity)
    if not len(a_start) or not len(b_start):
        return 0.0

    edges = np.union1d(
        np.concatenate([a_start, a_end]), np.concatenate([b_start, b_end])
    )
    seg_start, seg_end = edges[:-1], edges[1:]

    a = _density_on_segments(a_start, a_end, a_density, seg_start)
    b = _density_on_segments(b_start, b_end, b_density, seg_start)

    both = (a > 0) & (b > 0)
    if not both.any():
        return 0.0

    area = (seg_end[both] - seg_start[both]).astype(float) * PIXEL_AREA
    return float(4.0 * np.pi * np.sum(a[both] * b[both] * area))


def skymap_consistency(loc1, loc2):
    """How consistent two localizations are, on a 0-1 scale.

    The overlap integral divided by the largest value it could take for these
    two maps (Cauchy-Schwarz: ``integral(p1 p2) <= sqrt(integral(p1^2)
    integral(p2^2))``), which is their correlation: 1 when they agree as well as
    maps of these shapes can, 0 when disjoint.

    The raw overlap cannot be read on its own -- its ceiling is roughly
    4 pi / area, so 1e6 is unremarkable for an arcminute cone and unreachable
    for a 1000 square degree skymap. Dividing that ceiling out is what makes one
    threshold mean the same thing for every pair.
    """
    a_start, a_end, a_density = _uniq_ranges(loc1.uniq, loc1.probdensity)
    b_start, b_end, b_density = _uniq_ranges(loc2.uniq, loc2.probdensity)
    if not len(a_start) or not len(b_start):
        return 0.0

    edges = np.union1d(
        np.concatenate([a_start, a_end]), np.concatenate([b_start, b_end])
    )
    seg_start, seg_end = edges[:-1], edges[1:]
    area = (seg_end - seg_start).astype(float) * PIXEL_AREA

    a = _density_on_segments(a_start, a_end, a_density, seg_start)
    b = _density_on_segments(b_start, b_end, b_density, seg_start)

    cross = float(np.sum(a * b * area))
    if cross <= 0:
        return 0.0
    norm = np.sqrt(np.sum(a * a * area) * np.sum(b * b * area))
    if norm <= 0:
        return 0.0
    return float(min(1.0, cross / norm))
