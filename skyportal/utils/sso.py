"""Solar-system photometry math, mirroring BOOM's per-alert statistic (M. Kelley).

Kept in step with the browser copy in static/js/components/plot/ssoTransforms.ts;
skyportal/tests/utils/test_sso.py pins the two together.
"""

import math

# HG1G2 basis splines (Penttila 2016) as precomputed piecewise cubics: `below`
# and `above` extrapolate linearly in x, `segs` are cubic in (x - node).
_PHI1 = {
    "nodes": [
        0.1308996938995747,
        0.5235987755982988,
        1.0471975511965976,
        1.5707963267948966,
        2.0943951023931953,
        2.6179938779914944,
    ],
    "below": [0.999999997761256, -1.9098593],
    "segs": [
        [0.75, -1.9098593, 3.0632059507546687, -2.2709159732016233],
        [0.33486016, -0.5546343292135952, 0.38784609888094346, -0.11619084602803534],
        [0.1341056, -0.244045984668034, 0.20533394473291375, -0.0801973272976482],
        [0.051104756, -0.0949804384372285, 0.07936027759499992, -0.011595447695894826],
        [0.021465687, -0.021411423545129447, 0.06114619094674598, -0.1628628558176266],
    ],
    "above": [0.24273744600146052, -0.091328612],
}

_PHI2 = {
    "nodes": [
        0.1308996938995747,
        0.5235987755982988,
        1.0471975511965976,
        1.5707963267948966,
        2.0943951023931953,
        2.6179938779914944,
    ],
    "below": [1.0000000006373737, -0.5729578],
    "segs": [
        [0.925, -0.5729578, -0.8900289744775439, 1.0914182852955112],
        [0.62884169, -0.7670536698010225, 0.3957679006766861, -0.12651132878679328],
        [0.31755495, -0.45665789065199525, 0.19704437012044826, -0.0369675374435365],
        [0.12716367, -0.28071808963896605, 0.1389758980934878, 0.028512146018874328],
        [0.022373903, -0.11173256932741918, 0.18376267232897514, -0.09812349240793083],
    ],
    "above": [0.0001652835379452825, -8.6573138e-08],
}

_PHI3 = {
    "nodes": [
        0.0,
        0.005235987755982988,
        0.017453292519943295,
        0.03490658503988659,
        0.06981317007977318,
        0.13962634015954636,
        0.20943951023931956,
        0.3490658503988659,
        0.5235987755982988,
    ],
    "below": [1.0, -1.0630097],
    "segs": [
        [1.0, -1.0630097, -9981.672512688505, 787411.2353356931],
        [0.83381185, -40.82886154020155, 2386.9542487348835, -62471.31537685938],
        [0.57735424, -10.478447335501123, 97.26095184116981, -498.53387383171105],
        [0.42144772, -7.538985955965683, 71.1577792479135, -311.4965283708852],
        [0.2317423, -3.709883035770421, 38.53793907629016, -167.78613617153775],
        [0.10348178, -0.7822794793311048, 3.396892891575516, -10.84738319409093],
        [0.061733473, -0.4665902472074776, 1.125022268026889, -0.8857418715332711],
        [0.016107006, -0.20422874491497908, 0.7540035804821168, -0.6452701244191253],
    ],
    "above": [0.0, 0.0],
}


def _polyval(coeffs, x):
    return sum(c * x**i for i, c in enumerate(coeffs))


def _eval_spline(spline, x):
    nodes = spline["nodes"]
    last = len(nodes) - 1
    if x < nodes[0]:
        y = _polyval(spline["below"], x)
    elif x >= nodes[last]:
        y = _polyval(spline["above"], x)
    else:
        i = 0
        while i < last and not (nodes[i] <= x < nodes[i + 1]):
            i += 1
        y = _polyval(spline["segs"][i], x - nodes[i])
    return max(y, 0.0)


def hg12_phase_function(phase_deg, g12=0.5):
    """HG12* reduced-magnitude phase function (mag) at H=0."""
    a = math.radians(phase_deg)
    g1 = 0.84293649 * g12
    g2 = 0.5351335 * (1 - g12)
    phi = (
        g1 * _eval_spline(_PHI1, a)
        + g2 * _eval_spline(_PHI2, a)
        + (1 - g1 - g2) * _eval_spline(_PHI3, a)
    )
    if phi <= 0:
        return float("nan")
    return -2.5 * math.log10(phi)


def reduce_to_unit_geometry(
    m, rh, delta, phase, rh_slope=-2, delta_slope=-2, remove_phase=True
):
    """Reduce to rh = delta = 1 au; rh_slope is the heliocentric flux exponent."""
    out = []
    for mk, rhk, dk, pk in zip(m, rh, delta, phase, strict=True):
        if not (rhk and rhk > 0) or not (dk and dk > 0) or mk is None:
            out.append(float("nan"))
            continue
        v = mk + 2.5 * rh_slope * math.log10(rhk) + 2.5 * delta_slope * math.log10(dk)
        if remove_phase:
            v -= hg12_phase_function(pk)
        out.append(v)
    return out


def scale_by_geometry(rh, delta, phase, rh_slope=-2, delta_slope=-2):
    """Offset (mag) bringing each point to the geometry of the last one."""
    i = len(rh) - 1
    rh_ref, delta_ref = rh[i], delta[i]
    phi_ref = hg12_phase_function(phase[i])
    return [
        -2.5 * math.log10((rh_ref / rhk) ** rh_slope * (delta_ref / dk) ** delta_slope)
        + phi_ref
        - hg12_phase_function(pk)
        for rhk, dk, pk in zip(rh, delta, phase, strict=True)
    ]


def _weighted_mean(xs, uncs):
    sw = swx = 0.0
    for x, u in zip(xs, uncs, strict=True):
        if math.isfinite(x) and math.isfinite(u) and u > 0:
            w = u**-2
            sw += w
            swx += w * x
    if sw == 0:
        return float("nan"), float("nan")
    return swx / sw, sw**-0.5


def _median(values):
    v = sorted(x for x in values if math.isfinite(x))
    if not v:
        return float("nan")
    mid = len(v) // 2
    return v[mid] if len(v) % 2 else (v[mid - 1] + v[mid]) / 2


def color_scales(m, unc, bands):
    """Colour offsets onto the (excluded) last point's band."""
    target = bands[-1]
    avg = {}
    for band in dict.fromkeys(bands):
        xs = [m[k] for k, b in enumerate(bands) if b == band and k != len(bands) - 1]
        us = [unc[k] for k, b in enumerate(bands) if b == band and k != len(bands) - 1]
        avg[band] = _weighted_mean(xs, us)[0]
    return {b: (0.0 if b == target else avg[b] - avg[target]) for b in avg}


# Reference band when several are equally well observed, best first.
REFERENCE_PREFERENCE = ["r", "g", "i", "z", "y", "u"]


def fittable(points):
    """Points a fit may use: a rejected measurement is someone saying it is wrong."""
    return [p for p in points if not p.get("rejected")]


def fit_band_colors(points, rh_slope=-2, delta_slope=-2):
    """Fit per-band colours pairing within a night, which cancels geometry and rotation."""
    usable = [
        p
        for p in fittable(points)
        if p["mag"] is not None
        and math.isfinite(p["mag"])
        and p["rh"] > 0
        and p["delta"] > 0
    ]
    if not usable:
        return None
    reduced = reduce_to_unit_geometry(
        [p["mag"] for p in usable],
        [p["rh"] for p in usable],
        [p["delta"] for p in usable],
        [p["phase"] for p in usable],
        rh_slope=rh_slope,
        delta_slope=delta_slope,
    )

    # One mean per band per night; a night is a whole MJD.
    nightly = {}
    for p, r in zip(usable, reduced, strict=True):
        if not math.isfinite(r):
            continue
        nightly.setdefault(math.floor(p["time"]), {}).setdefault(p["band"], []).append(
            r
        )
    if not nightly:
        return None

    nights_per_band = {}
    for bands in nightly.values():
        for band in bands:
            nights_per_band[band] = nights_per_band.get(band, 0) + 1
    points_per_band = {}
    for p in usable:
        points_per_band[p["band"]] = points_per_band.get(p["band"], 0) + 1

    def preference(band):
        return (
            REFERENCE_PREFERENCE.index(band)
            if band in REFERENCE_PREFERENCE
            else len(REFERENCE_PREFERENCE)
        )

    # Most nights wins; ties go to the redder workhorse band, as colours are quoted.
    reference = sorted(
        nights_per_band,
        key=lambda b: (
            -nights_per_band[b],
            -points_per_band.get(b, 0),
            preference(b),
            b,
        ),
    )[0]

    colors = {
        reference: {
            "offset": 0.0,
            "uncertainty": 0.0,
            "nights": nights_per_band[reference],
        }
    }
    for band in nights_per_band:
        if band == reference:
            continue
        diffs = [
            sum(bands[band]) / len(bands[band])
            - sum(bands[reference]) / len(bands[reference])
            for bands in nightly.values()
            if bands.get(band) and bands.get(reference)
        ]
        if not diffs:
            continue
        offset = sum(diffs) / len(diffs)
        if len(diffs) < 2:
            unc = float("nan")
        else:
            var = sum((d - offset) ** 2 for d in diffs) / (len(diffs) - 1)
            unc = math.sqrt(var) / math.sqrt(len(diffs))
        colors[band] = {"offset": offset, "uncertainty": unc, "nights": len(diffs)}
    return {"reference": reference, "colors": colors}


def outburst_report(points, window=14, rh_slope=-2, delta_slope=-2):
    """Outburst statistic on the trailing `window` days; the most recent point is tested."""
    ordered = sorted(fittable(points), key=lambda p: p["time"])
    if len(ordered) < 2:
        return None
    t_last = ordered[-1]["time"]
    win = [p for p in ordered if -window < p["time"] - t_last <= 0]
    if len(win) < 2:
        return None

    m = [p["mag"] for p in win]
    unc = [p["magerr"] for p in win]
    bands = [p["band"] for p in win]
    test_band, test_mag, test_unc = bands[-1], m[-1], unc[-1]
    # Without another point in the test band there is no colour to place it on.
    if test_band not in bands[:-1]:
        return None

    geom = scale_by_geometry(
        [p["rh"] for p in win],
        [p["delta"] for p in win],
        [p["phase"] for p in win],
        rh_slope,
        delta_slope,
    )
    h = [mk + g for mk, g in zip(m, geom, strict=True)]
    color = color_scales(h, unc, bands)
    h_color = [hk - color[b] for hk, b in zip(h, bands, strict=True)]
    ostats = [
        (h_color[k] - test_mag) / math.sqrt(test_unc**2 + unc[k] ** 2)
        for k in range(len(m) - 1)
    ]
    return {
        "median_o": _median(ostats),
        "n_points": len(m),
        "test_value": test_mag,
        "test_band": test_band,
        "dt": [p["time"] - t_last for p in win],
        "bands": bands,
        "ostats": ostats,
        "color": color,
    }
