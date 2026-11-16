"""SPHEREx archive coverage for a position.

Asking IRSA which spectral images cover a position is cheap, so this runs in an
ordinary service and records the coverage as an annotation. Extracting a
spectrum means fetching a cutout of every one of those images, which belongs in
an analysis service.
"""

ANNOTATION_ORIGIN = "spherex-archive"

# DR1 runs to May 2026; the weekly QR3 releases carry what was taken since.
COLLECTIONS = ("spherex_dr1", "spherex_dr1_deep", "spherex_qr3", "spherex_qr3_deep")

# SIA lists a few hundred images in about a second for most of the sky, but a
# deep field near an ecliptic pole has over 20,000.
SIA_MAXREC = 2000

# Past SIA_MAXREC, IRSA counts the images per collection, detector and day
# itself. Slower (10-30 s) but a few hundred rows wherever the position is.
COVERAGE_QUERY = """
SELECT obs_collection, energy_bandpassname, FLOOR(t_min) AS mjd_day,
       COUNT(*) AS n_images, MIN(em_min) AS em_min, MAX(em_max) AS em_max
FROM spherex.obscore
WHERE obs_collection IN ({collections})
  AND CONTAINS(POINT('ICRS', {ra}, {dec}), s_region) = 1
GROUP BY obs_collection, energy_bandpassname, FLOOR(t_min)
"""

# SPHEREx comes back to a position about every six months and spends a few days
# to two weeks on it, so a longer gap starts a new visit.
VISIT_GAP_DAYS = 30


def _detector(bandpass):
    # IRSA names the detectors' bandpasses "SPHEREx-D1" to "SPHEREx-D6".
    try:
        return int(str(bandpass).rsplit("D", 1)[-1])
    except ValueError:
        return None


def _date(mjd):
    from astropy.time import Time

    return Time(mjd, format="mjd").to_value("iso", subfmt="date")


def _visits(rows):
    per_day = {}
    for row in rows:
        day = int(row["mjd_day"])
        per_day[day] = per_day.get(day, 0) + int(row["n_images"])

    visits = []
    for day in sorted(per_day):
        if visits and day - visits[-1]["last_day"] <= VISIT_GAP_DAYS:
            visits[-1]["last_day"] = day
            visits[-1]["n_images"] += per_day[day]
        else:
            visits.append({"first_day": day, "last_day": day, "n_images": per_day[day]})

    return [
        {
            "start": _date(v["first_day"]),
            "end": _date(v["last_day"]),
            "n_images": v["n_images"],
        }
        for v in visits
    ]


def summarize(rows, ra=None, dec=None):
    """Turn coverage rows into the annotation recorded against an object.

    `collections` names the IRSA collections an analysis service would query
    for the images themselves; `visits` says when SPHEREx looked, which is what
    matters for a transient.
    """
    rows = list(rows or [])

    collections = {}
    for row in rows:
        name = row["obs_collection"]
        collections[name] = collections.get(name, 0) + int(row["n_images"])

    detectors = {_detector(row["energy_bandpassname"]) for row in rows}
    visits = _visits(rows)

    return {
        "observed": bool(rows),
        "n_images": sum(collections.values()),
        "collections": dict(sorted(collections.items())),
        "detectors": sorted(d for d in detectors if d is not None),
        # ObsCore gives the band edges in metres.
        "wavelength_um": (
            [
                round(min(row["em_min"] for row in rows) * 1e6, 3),
                round(max(row["em_max"] for row in rows) * 1e6, 3),
            ]
            if rows
            else None
        ),
        "first_observed": visits[0]["start"] if visits else None,
        "last_observed": visits[-1]["end"] if visits else None,
        "visits": visits,
        "query": {"ra": ra, "dec": dec},
    }


def _count_images(images):
    """Per-image SIA rows, counted the way COVERAGE_QUERY counts them."""
    import math

    counts = {}
    for image in images:
        key = (
            str(image["obs_collection"]),
            str(image["energy_bandpassname"]),
            float(math.floor(image["t_min"])),
        )
        row = counts.setdefault(
            key,
            {
                "obs_collection": key[0],
                "energy_bandpassname": key[1],
                "mjd_day": key[2],
                "n_images": 0,
                "em_min": float(image["em_min"]),
                "em_max": float(image["em_max"]),
            },
        )
        row["n_images"] += 1
        row["em_min"] = min(row["em_min"], float(image["em_min"]))
        row["em_max"] = max(row["em_max"], float(image["em_max"]))
    return list(counts.values())


def query_coverage(ra, dec):
    """Rows counting the SPHEREx images whose footprint contains a position."""
    import astropy.units as u
    from astropy.coordinates import SkyCoord
    from astroquery.ipac.irsa import Irsa

    images = Irsa.query_sia(
        pos=(SkyCoord(ra * u.deg, dec * u.deg), 1 * u.arcsec),
        collection=list(COLLECTIONS),
        maxrec=SIA_MAXREC,
    )
    if len(images) < SIA_MAXREC:
        return _count_images(images)

    query = COVERAGE_QUERY.format(
        collections=", ".join(f"'{c}'" for c in COLLECTIONS),
        ra=float(ra),
        dec=float(dec),
    )
    table = Irsa.query_tap(query).to_table()
    rows = []
    for row in table:
        entry = {}
        for column in table.colnames:
            value = row[column]
            entry[column] = value.item() if hasattr(value, "item") else value
        rows.append(entry)
    return rows
