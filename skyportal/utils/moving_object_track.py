"""Measuring a linked moving-object track from its difference cutouts.

A main-belt asteroid moves far enough between visits that a positional survey
gives it a new object id every epoch, so a real object arrives as a scatter of
one-point sources. What binds them is the track, and what decides whether the
track is real is the pixels: every epoch a positive point source at the cutout
centre, on a smoothly curving path.

Nothing here finds tracks; that is the linker's job. This measures one it is
given.
"""

import numpy as np

# Annulus as a fraction of the stamp's half-width: 12-25 px on ZTF's 63x63
# cutout, and the same patch of sky on a stamp of any size.
ANNULUS_INNER_FRACTION = 12 / 31
ANNULUS_OUTER_FRACTION = 25 / 31
# Half-width of the box the peak is looked for in: a real detection sits at the
# centre by construction, since the stamp is cut at the reported position.
PEAK_BOX_HALF_PX = 3

MIN_ANNULUS_PIXELS = 20


class NotMeasurable(Exception):
    """The cutout cannot be measured, with the reason a reader needs."""


def background(data):
    """Median and MAD-based sigma of the annulus around the centre.

    MAD, never the standard deviation: a field star inside the annulus inflates
    a standard deviation enough to push a genuine detection under 3 sigma, and
    nothing about that failure is visible in the output.
    """
    centre = min(data.shape) // 2
    yy, xx = np.mgrid[0 : data.shape[0], 0 : data.shape[1]]
    radius = np.hypot(yy - centre, xx - centre)

    inner = centre * ANNULUS_INNER_FRACTION
    outer = centre * ANNULUS_OUTER_FRACTION
    ring = data[(radius > inner) & (radius < outer)]
    if ring.size < MIN_ANNULUS_PIXELS:
        raise NotMeasurable(
            f"only {ring.size} background pixels between {inner:.0f} and "
            f"{outer:.0f} px; the stamp is too small to measure against"
        )

    median = float(np.median(ring))
    sigma = float(1.4826 * np.median(np.abs(ring - median)))
    return median, sigma


def measure_cutout(data):
    """Peak significance and centroid offset of the source at a stamp's centre.

    Returns the background it measured against too: the same numbers set the
    display stretch, and a strip of cutouts stretched to their own background
    is the difference between a 12-sigma source looking obvious and looking
    like noise.
    """
    data = np.nan_to_num(np.asarray(data, dtype=float), nan=0.0)
    if data.ndim != 2:
        raise NotMeasurable(f"expected a 2D cutout, got shape {data.shape}")

    median, sigma = background(data)
    if not np.isfinite(sigma) or sigma <= 0:
        raise NotMeasurable("background sigma is zero; the stamp is flat")

    centre = min(data.shape) // 2
    half = PEAK_BOX_HALF_PX
    box = data[centre - half : centre + half + 1, centre - half : centre + half + 1]
    box = box - median
    peak_y, peak_x = np.unravel_index(int(np.argmax(box)), box.shape)

    return {
        "snr": float(box.max() / sigma),
        "centroid_offset_px": float(np.hypot(peak_y - half, peak_x - half)),
        "peak": float(box.max()),
        "background_median": median,
        "background_sigma": sigma,
    }


def stretch_limits(median, sigma, low=2.0, high=9.0):
    """Display limits keyed to the local background, not the whole stamp.

    A zscale over the full cutout is set by whatever else is in the frame, and
    renders a real detection as noise to the eye.
    """
    return median - low * sigma, median + high * sigma


def _ra_difference(from_ra, to_ra):
    """Signed RA difference in degrees, taking the short way around 0h."""
    return ((to_ra - from_ra + 180.0) % 360.0) - 180.0


def _unwrapped_ra(values):
    """An RA sequence made continuous, so a track crossing 0h can be fitted."""
    return np.degrees(np.unwrap(np.radians(np.asarray(values, dtype=float))))


def position_angles(detections):
    """Position angle in degrees between consecutive detections, east of north.

    A real object traces a smoothly turning path; unrelated artifacts do not.
    Costs nothing, since it is arithmetic on positions already in hand.
    """
    rows = sorted(detections, key=lambda d: d["jd"])
    angles = []
    for earlier, later in zip(rows, rows[1:]):
        mean_dec = np.radians((earlier["dec"] + later["dec"]) / 2)
        d_ra = _ra_difference(earlier["ra"], later["ra"]) * np.cos(mean_dec)
        d_dec = later["dec"] - earlier["dec"]
        angles.append(float(np.degrees(np.arctan2(d_ra, d_dec)) % 360))
    return angles


def motion_residuals(detections, degree=3):
    """RMS residual about a polynomial in RA/Dec against time, in arcseconds.

    A cubic follows the curvature of a real arc over days. A two-night track has
    too few points for one, so the degree drops to what the data can carry and
    is reported back: a fit with no freedom left has a small residual by
    construction and means nothing on its own.
    """
    rows = sorted(detections, key=lambda d: d["jd"])
    n = len(rows)
    # One spare point beyond the fit's parameters, or the residual is forced.
    degree = min(degree, n - 3)
    if degree < 1:
        return None

    t = np.array([d["jd"] for d in rows], dtype=float)
    t = t - t.mean()
    dec = np.array([d["dec"] for d in rows], dtype=float)
    ra = _unwrapped_ra([d["ra"] for d in rows])
    # RA converges at high declination, so residuals are compared on the sky.
    ra_scaled = ra * np.cos(np.radians(dec.mean()))

    squared = 0.0
    for values in (ra_scaled, dec):
        fit = np.polyval(np.polyfit(t, values, degree), t)
        squared += np.sum(((values - fit) * 3600.0) ** 2)
    return {
        "rms_arcsec": float(np.sqrt(squared / n)),
        "degree": degree,
        "n_points": n,
        "arc_days": float(t.max() - t.min()),
    }


# Below this the two magnitudes are the same measurement to within their
# errors, and which is brighter in the pixels says nothing.
MIN_BAND_MAG_DIFFERENCE = 0.1
# Two detections this far apart share the night's seeing and sky, so their peak
# counts are comparable. Across nights they are not.
SAME_NIGHT_DAYS = 0.5


def band_flux_agreements(measurements):
    """Same-night pairs in different bands, and whether pixels and photometry
    agree on which is brighter.

    Peak counts, not SNR: SNR divides by each exposure's own noise, so it
    reorders bands whenever the seeing differs. Pairs whose magnitudes differ by
    less than the photometric error are skipped rather than counted as
    disagreements.
    """
    rows = sorted(
        (
            m
            for m in measurements
            if m.get("peak") is not None and m.get("mag") is not None
        ),
        key=lambda m: m["jd"],
    )
    agreements = []
    for earlier, later in zip(rows, rows[1:]):
        if later["jd"] - earlier["jd"] > SAME_NIGHT_DAYS:
            continue
        if earlier["band"] == later["band"]:
            continue
        if abs(earlier["mag"] - later["mag"]) < MIN_BAND_MAG_DIFFERENCE:
            continue
        brighter_mag = min(earlier, later, key=lambda m: m["mag"])
        brighter_pixels = max(earlier, later, key=lambda m: m["peak"])
        agreements.append(
            {
                "jd": earlier["jd"],
                "bands": (earlier["band"], later["band"]),
                "agrees": brighter_mag is brighter_pixels,
            }
        )
    return agreements


def band_flux_is_consistent(measurements):
    """Whether every comparable same-night band pair agrees.

    Vacuously true when the arc has no such pair, which is a fact about the
    cadence rather than a verdict on the track.
    """
    return all(pair["agrees"] for pair in band_flux_agreements(measurements))


ZTF_PIXEL_ARCSEC = 1.012
MAX_TRAIL_FRACTION = 0.5
MAX_SEERATIO = 2.0
MIN_ACTIVITY_DETECTIONS = 5
# 99th percentile of known-asteroid tracks on BOOM Caltech, which flags 5 of 7 comet tracks.
ACTIVE_FWHM_RATIO = 1.15
ACTIVE_CLASSTAR = 0.87


def sky_rate_arcsec_per_hour(detections):
    rows = sorted(detections, key=lambda d: d["jd"])
    if len(rows) < 2 or rows[-1]["jd"] <= rows[0]["jd"]:
        return None
    first, last = rows[0], rows[-1]
    mean_dec = np.radians((first["dec"] + last["dec"]) / 2)
    d_ra = _ra_difference(first["ra"], last["ra"]) * np.cos(mean_dec)
    d_dec = last["dec"] - first["dec"]
    return float(np.hypot(d_ra, d_dec) * 3600 / ((last["jd"] - first["jd"]) * 24))


def fwhm_ratio(candidate, rate_arcsec_per_hour):
    fwhm, seeratio = candidate.get("fwhm"), candidate.get("seeratio")
    if not fwhm or not seeratio or seeratio >= MAX_SEERATIO:
        return None
    trail = (rate_arcsec_per_hour or 0.0) * (candidate.get("exptime") or 30.0) / 3600
    if trail > MAX_TRAIL_FRACTION * fwhm * seeratio * ZTF_PIXEL_ARCSEC:
        return None
    return float(1 / seeratio)


def activity(detections):
    usable = [d for d in detections if d.get("fwhm_ratio") is not None]
    if len(usable) < MIN_ACTIVITY_DETECTIONS:
        return None
    ratio = float(np.median([d["fwhm_ratio"] for d in usable]))
    stars = [d["classtar"] for d in usable if d.get("classtar") is not None]
    classtar = float(np.median(stars)) if stars else None
    return {
        "fwhm_ratio": ratio,
        "classtar": classtar,
        "n_detections": len(usable),
        "possible_comet": ratio > ACTIVE_FWHM_RATIO
        or (classtar is not None and classtar < ACTIVE_CLASSTAR),
    }


def render_epoch(data, survey="ZTF", header=None):
    """One epoch's difference cutout as a PNG, stretched to its own background.

    The stretch is the whole point: a percentile interval over the full stamp is
    set by whatever else is in the frame, and renders a real 12-sigma source as
    noise. Returns None when the stamp cannot be measured, so a strip shows a
    gap rather than a misleading picture.
    """
    import base64

    from astropy.visualization import AsymmetricPercentileInterval, LinearStretch

    from ..broker_apis._thumbnails import orient_cutout, render_cutout_png

    try:
        median, sigma = background(np.nan_to_num(np.asarray(data, dtype=float)))
    except NotMeasurable:
        return None

    oriented = orient_cutout(np.asarray(data, dtype=float), survey, header or {})
    # ImageNormalize maps the data onto 0-1 before the limits apply, so the
    # background limits are scaled the same way.
    low, high = stretch_limits(median, sigma)
    span = float(np.nanmax(oriented) - np.nanmin(oriented)) or 1.0
    floor = float(np.nanmin(oriented))
    limits = ((low - floor) / span, (high - floor) / span)

    buff = render_cutout_png(
        oriented,
        LinearStretch(),
        AsymmetricPercentileInterval(lower_percentile=1, upper_percentile=100),
        cmap="bone",
        limits=limits,
    )
    return base64.b64encode(buff.read()).decode("utf-8")
