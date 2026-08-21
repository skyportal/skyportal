"""Asteroid/comet outburst statistic (M. S. P. Kelley).

Each photometric point in a short window is scaled to the observing geometry and
colour of the point being tested (the last one); the sigma distance of every
other point from the test value is an outburst statistic. A large positive
median (>~3-5) means the test point is brighter than the recent trend, i.e. an
outburst.

Geometry -- heliocentric distance ``rh`` (au), observer-target distance
``delta`` (au), and solar phase angle ``phase`` (deg) -- is an *input*: it comes
from the alert packets (Rubin carries the vectors directly) or an ephemeris.

The IAU HG1G2 / HG12* (Penttila et al. 2016) phase function is reimplemented in
numpy so this module has no sbpy runtime dependency; it is checked against sbpy
fixtures in the tests.
"""

import numpy as np
from numpy.polynomial.polynomial import Polynomial

# Asteroid defaults; comets differ (rh_slope ~ -4, delta_slope ~ -1, and a dust
# phase function).
DEFAULT_RH_SLOPE = -2
DEFAULT_DELTA_SLOPE = -2


class _Spline:
    """Cubic spline through nodes with clamped end-derivatives and *linear*
    extrapolation beyond the node range (ported from sbpy.photometry.core so the
    HG1G2 basis matches bit-for-bit). ``positive`` clips negatives to 0.
    """

    def __init__(self, x, y, dy, positive=False):
        self.x = np.asarray(x, dtype=float)
        self.y = np.asarray(y, dtype=float)
        self.dy = np.asarray(dy, dtype=float)
        self.positive = positive
        n = len(self.y)
        h = self.x[1:] - self.x[:-1]
        r = (self.y[1:] - self.y[:-1]) / h
        B = np.zeros((n - 2, n))
        for i in range(n - 2):
            k = i + 1
            B[i, i : i + 3] = [h[k], 2 * (h[k - 1] + h[k]), h[k - 1]]
        C = np.empty((n - 2, 1))
        for i in range(n - 2):
            k = i + 1
            C[i] = 3 * (r[k - 1] * h[k] + r[k] * h[k - 1])
        C[0] = C[0] - self.dy[0] * B[0, 0]
        C[-1] = C[-1] - self.dy[1] * B[-1, -1]
        B = B[:, 1 : n - 1]
        dys = np.linalg.solve(B, C)
        dys = np.array([self.dy[0], *dys.flatten(), self.dy[1]])
        A0 = self.y[:-1]
        A1 = dys[:-1]
        A2 = (3 * r - 2 * dys[:-1] - dys[1:]) / h
        A3 = (-2 * r + dys[:-1] + dys[1:]) / h**2
        self.polys = [Polynomial(c) for c in np.array([A0, A1, A2, A3]).T]
        # Linear extrapolation outside the node range.
        self.polys.insert(
            0, Polynomial([self.y[0] - self.x[0] * self.dy[0], self.dy[0]])
        )
        self.polys.append(
            Polynomial([self.y[-1] - self.x[-1] * self.dy[-1], self.dy[-1]])
        )

    def __call__(self, x):
        x = np.asarray(x, dtype=float)
        out = np.zeros(x.shape, dtype=float)
        idx = x < self.x[0]
        if idx.any():
            out[idx] = self.polys[0](x[idx])
        for i in range(len(self.x) - 1):
            idx = (self.x[i] <= x) & (x < self.x[i + 1])
            if idx.any():
                out[idx] = self.polys[i + 1](x[idx] - self.x[i])
        idx = x >= self.x[-1]
        if idx.any():
            out[idx] = self.polys[-1](x[idx])
        if self.positive:
            out[out < 0] = 0
        return out


# HG1G2 basis-function nodes (Muinonen et al. 2010; Penttila et al. 2016), with
# node abscissae in radians.
_PHI1 = _Spline(
    np.radians([7.5, 30, 60, 90, 120, 150]),
    [0.75, 0.33486016, 0.1341056, 0.051104756, 0.021465687, 0.0036396989],
    [-1.9098593, -0.091328612],
    positive=True,
)
_PHI2 = _Spline(
    np.radians([7.5, 30, 60, 90, 120, 150]),
    [0.925, 0.62884169, 0.31755495, 0.12716367, 0.022373903, 0.00016505689],
    [-0.5729578, -8.6573138e-08],
    positive=True,
)
_PHI3 = _Spline(
    np.radians([0, 0.3, 1, 2, 4, 8, 12, 20, 30]),
    [
        1.0,
        0.83381185,
        0.57735424,
        0.42144772,
        0.2317423,
        0.10348178,
        0.061733473,
        0.016107006,
        0.0,
    ],
    [-1.0630097, 0.0],
    positive=True,
)


def hg12_phase_function(phase, G12=0.5):
    """HG12* reduced-magnitude phase function (mag), H=0, per Penttila 2016."""
    a = np.radians(np.asarray(phase, dtype=float))
    scalar = a.ndim == 0
    a = np.atleast_1d(a)
    g1 = 0.84293649 * G12
    g2 = 0.53513350 * (1 - G12)
    phi = g1 * _PHI1(a) + g2 * _PHI2(a) + (1 - g1 - g2) * _PHI3(a)
    out = -2.5 * np.log10(phi)
    return out[0] if scalar else out


def scale_by_geometry(
    rh,
    delta,
    phase,
    rh_slope=DEFAULT_RH_SLOPE,
    delta_slope=DEFAULT_DELTA_SLOPE,
    phase_function=hg12_phase_function,
):
    """Magnitude offset that brings each point to the geometry of the last one
    (apparent -> absolute-like magnitude)."""
    rh = np.asarray(rh, dtype=float)
    delta = np.asarray(delta, dtype=float)
    phase = np.asarray(phase, dtype=float)
    return (
        -2.5 * np.log10((rh[-1] / rh) ** rh_slope * (delta[-1] / delta) ** delta_slope)
        + phase_function(phase[-1])
        - phase_function(phase)
    )


def weighted_mean(x, unc):
    """Inverse-variance weighted mean and its uncertainty, ignoring non-finite."""
    x = np.asarray(x, dtype=float)
    unc = np.asarray(unc, dtype=float)
    i = np.isfinite(x * unc)
    if i.sum() == 0:
        return np.nan, np.nan
    m, sw = np.average(x[i], weights=unc[i] ** -2, returned=True)
    return m, sw**-0.5


def color_scales(m, unc, bands):
    """Per-band colour offsets that scale each band to the test point's band.

    ``m`` must already be geometry-corrected. Excludes the test point (last)
    from the band averages.
    """
    m = np.asarray(m, dtype=float)
    unc = np.asarray(unc, dtype=float)
    bands = np.asarray(bands)
    target_band = bands[-1]
    if target_band not in bands[:-1]:
        raise ValueError(f"Cannot estimate color for band {target_band}")

    avg = {}
    avg_unc = {}
    for band in set(bands):
        i = bands == band
        i[-1] = False  # never the point being tested
        avg[band], avg_unc[band] = weighted_mean(m[i], unc[i])

    color = {}
    color_unc = {}
    for band in set(bands):
        if band == target_band:
            color[band] = 0
            color_unc[band] = 0
            continue
        color[band] = avg[band] - avg[target_band]
        color_unc[band] = np.hypot(avg_unc[band], avg_unc[target_band])
    return color, color_unc


def outburst_statistic(
    rh,
    delta,
    phase,
    m,
    unc,
    bands,
    rh_slope=DEFAULT_RH_SLOPE,
    delta_slope=DEFAULT_DELTA_SLOPE,
    phase_function=hg12_phase_function,
):
    """Outburst statistics for a window of photometry (last point is tested).

    Returns ``(ostats, color, color_unc)`` where ``ostats`` holds the N-1 sigma
    distances of the earlier points from the test value; the median is the
    single detection statistic (>~3-5 => outburst).
    """
    m = np.asarray(m, dtype=float)
    unc = np.asarray(unc, dtype=float)
    bands = np.asarray(bands)
    geom = scale_by_geometry(rh, delta, phase, rh_slope, delta_slope, phase_function)
    color, color_unc = color_scales(m + geom, unc, bands)
    c = np.array([color[band] for band in bands])
    x = m[:-1] + geom[:-1] - c[:-1] - m[-1]
    y = np.sqrt(unc[-1] ** 2 + unc**2)[:-1]
    return x / y, color, color_unc


def outburst_report(
    time,
    m,
    unc,
    bands,
    rh,
    delta,
    phase,
    window=14,
    rh_slope=DEFAULT_RH_SLOPE,
    delta_slope=DEFAULT_DELTA_SLOPE,
    phase_function=hg12_phase_function,
):
    """Run the statistic on the trailing ``window`` days and assemble everything
    the figure + annotation need.

    Points are ordered by ``time`` and restricted to the ``window`` days ending
    at the most recent point (the one tested). Returns a dict with the summary
    ``median_o`` plus the per-point series for the four diagnostic panels
    (apparent ``m``, geometry-corrected ``H``, colour-removed ``H_color``, and
    the ``ostats`` histogram). Raises ``ValueError`` if fewer than two points
    remain or the test point's band has no earlier match.
    """
    time = np.asarray(time, dtype=float)
    m = np.asarray(m, dtype=float)
    unc = np.asarray(unc, dtype=float)
    bands = np.asarray(bands)
    rh = np.asarray(rh, dtype=float)
    delta = np.asarray(delta, dtype=float)
    phase = np.asarray(phase, dtype=float)

    order = np.argsort(time, kind="stable")
    time, m, unc, bands, rh, delta, phase = (
        a[order] for a in (time, m, unc, bands, rh, delta, phase)
    )

    dt = time - time[-1]
    keep = (dt > -window) & (dt <= 0)
    time, m, unc, bands, rh, delta, phase, dt = (
        a[keep] for a in (time, m, unc, bands, rh, delta, phase, dt)
    )
    if len(m) < 2:
        raise ValueError("Need at least two points in the window.")

    ostats, color, color_unc = outburst_statistic(
        rh, delta, phase, m, unc, bands, rh_slope, delta_slope, phase_function
    )
    geom = scale_by_geometry(rh, delta, phase, rh_slope, delta_slope, phase_function)
    c = np.array([color[band] for band in bands])

    return {
        "median_o": float(np.nanmedian(ostats)),
        "n_points": len(m),
        "test_value": float(m[-1]),
        "ostats": ostats,
        "dt": dt,
        "bands": bands,
        "unc": unc,
        "m": m,  # apparent
        "H": m + geom,  # geometry-corrected
        "H_color": m + geom - c,  # colour-removed
        "color": color,
        "color_unc": color_unc,
    }
