# pyright: reportMissingTypeStubs=false, reportUnknownMemberType=false
# pyright: reportUnknownVariableType=false, reportUnknownArgumentType=false
"""Astronomical utility tools: time conversion, survey links, ZTF cutouts."""

import csv
import io
from urllib.parse import quote

import httpx
from astropy.time import Time

from ..server import SKYPORTAL_URL, get_skyportal_token, mcp

# ─── Coordinate formatting helpers ───────────────────────────────────────────


def _ra_to_hms(ra_deg: float, sep: str | None = ":") -> str:
    """Convert RA in decimal degrees to HH:MM:SS string."""
    from astropy.coordinates import Angle

    a = Angle(ra_deg, unit="deg")
    kwargs: dict = {"unit": "hour", "precision": 2, "pad": True}
    if sep is not None:
        kwargs["sep"] = sep
    return a.to_string(**kwargs)


def _dec_to_dms(dec_deg: float, sep: str | None = ":") -> str:
    """Convert Dec in decimal degrees to DD:MM:SS string."""
    from astropy.coordinates import Angle

    a = Angle(dec_deg, unit="deg")
    kwargs: dict = {"unit": "deg", "precision": 2, "alwayssign": True, "pad": True}
    if sep is not None:
        kwargs["sep"] = sep
    return a.to_string(**kwargs)


# ─── Time conversion ────────────────────────────────────────────────────────


@mcp.tool()
def convert_time(
    value: str,
    from_format: str = "auto",
    to_format: str = "auto",
) -> str:
    """Convert between MJD, JD, ISO datetime, and Unix timestamps.

    Args:
        value: The time value to convert (e.g., "60400.5", "2024-03-15T12:00:00",
               "2024-03-15", "1710504000")
        from_format: Input format — one of "mjd", "jd", "iso", "unix", or "auto"
                     to detect automatically
        to_format: Desired output format — one of "mjd", "jd", "iso", "unix", or
                   "auto" (returns all formats)
    """
    format_map = {"mjd": "mjd", "jd": "jd", "iso": "isot", "unix": "unix"}

    try:
        if from_format == "auto":
            try:
                float_val = float(value)
                if float_val > 2_400_000:
                    t = Time(float_val, format="jd")
                elif float_val > 100_000:
                    t = Time(float_val, format="mjd")
                else:
                    t = Time(float_val, format="mjd")
            except ValueError:
                t = Time(value, format="isot")
        else:
            fmt = format_map.get(from_format)
            if fmt is None:
                return f"Unknown from_format '{from_format}'. Use: mjd, jd, iso, unix, auto"
            val = float(value) if fmt != "isot" else value
            t = Time(val, format=fmt)

        if to_format != "auto":
            fmt = format_map.get(to_format)
            if fmt is None:
                return f"Unknown to_format '{to_format}'. Use: mjd, jd, iso, unix, auto"
            return f"{getattr(t, fmt)}"

        return f"ISO: {t.isot}\nMJD: {t.mjd}\nJD:  {t.jd}\nUnix: {t.unix}"
    except Exception as e:
        return f"Conversion error: {e}"


# ─── Survey links ───────────────────────────────────────────────────────────


@mcp.tool()
async def get_survey_urls(
    ra: float | None = None,
    dec: float | None = None,
    source_id: str | None = None,
) -> str:
    """Get URLs to browse a sky position in common astronomical surveys.

    Provide either ra/dec coordinates or a source_id to auto-resolve
    coordinates from SkyPortal.

    Args:
        ra: Right ascension in decimal degrees (J2000). Not needed if
            source_id is provided.
        dec: Declination in decimal degrees (J2000). Not needed if
             source_id is provided.
        source_id: SkyPortal source ID (e.g., "ZTF21aaaaaaa"). RA/Dec
                   will be looked up automatically. Requires authentication.

    Returns:
        Resolved coordinates (RA/Dec in decimal degrees and sexagesimal)
        followed by clickable links for ZTF, Legacy Survey, PanSTARRS,
        SDSS, NED, SIMBAD, VizieR, WISE, DSS, ADS, TNS, Aladin, and more.
        For ZTF (IRSA), the link goes to the search page with instructions
        to enter the coordinates manually.
    """
    # Resolve coordinates from source_id if needed
    if source_id and (ra is None or dec is None):
        token = get_skyportal_token()
        if not token:
            return "Authentication required to look up source coordinates. Provide ra/dec directly or authenticate."
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(
                    f"{SKYPORTAL_URL}/api/sources/{source_id}",
                    headers={"Authorization": f"token {token}"},
                )
            resp.raise_for_status()
            src = resp.json().get("data", {})
            ra = src.get("ra")
            dec = src.get("dec")
            if ra is None or dec is None:
                return f"Could not resolve coordinates for source {source_id}"
        except Exception as e:
            return f"Error looking up source {source_id}: {e}"

    if ra is None or dec is None:
        return "Provide either source_id or both ra and dec."

    ra_hms = _ra_to_hms(ra)
    dec_dms = _dec_to_dms(dec)
    ra_hms_space = _ra_to_hms(ra, " ")
    dec_dms_space = _dec_to_dms(dec, " ")

    sign = "%2B" if dec > 0 else ""

    surveys = {
        "ZTF (IRSA)": (
            f"https://irsa.ipac.caltech.edu/applications/ztf/"
            f"\n    NOTE: Enter coordinates RA={ra:.6f}, Dec={dec:+.6f} in the search box."
        ),
        "Legacy Survey": f"https://www.legacysurvey.org/viewer?ra={ra}&dec={dec}&zoom=14",
        "PanSTARRS": (
            f"https://ps1images.stsci.edu/cgi-bin/ps1cutouts"
            f"?pos={ra}+{dec}&filter=color&filter=g&filter=r&filter=i"
            f"&filter=z&filter=y&filetypes=stack&size=240"
        ),
        "SDSS": f"https://skyserver.sdss.org/dr18/VisualTools/navi?opt=G&ra={ra}&dec={dec}&scale=0.1",
        "NED": f"https://ned.ipac.caltech.edu/cgi-bin/nph-objsearch?lon={ra}d&lat={dec}d&radius=1.0&search_type=Near+Position+Search",
        "SIMBAD": f"http://simbad.u-strasbg.fr/simbad/sim-coo?protocol=html&NbIdent=30&Radius.unit=arcsec&CooFrame=FK5&CooEpoch=2000&CooEqui=2000&Coord={ra}d+{dec}d",
        "VizieR": f"https://vizier.cds.unistra.fr/viz-bin/VizieR?-source=&-out.add=_r&-sort=_r&-out.max=20&-c={ra_hms}+{dec_dms}&-c.rs=10",
        "TNS": f"https://wis-tns.org/search?&ra={ra}&decl={dec}&radius=10&coords_unit=arcsec",
        "ADS": f"https://ui.adsabs.harvard.edu/search/q=object%22{ra}%20{sign}{dec}%3A0%201%22&sort=date%20desc",
        "DSS2": f"https://archive.stsci.edu/cgi-bin/dss_search?v=poss2ukstu_red&r={ra}&d={dec}&e=J2000&h=15.0&w=15.0&f=gif",
        "WISE (IRSA SIA)": (
            f"https://irsa.ipac.caltech.edu/SIA?COLLECTION=wise_allwise"
            f"&POS=circle+{ra}+{dec}+0.01&RESPONSEFORMAT=CSV"
        ),
        "Gaia DR2 (VizieR)": f"https://vizier.cds.unistra.fr/viz-bin/VizieR?-source=I/345/gaia2&-out.add=_r&-sort=_r&-out.max=20&-c={ra_hms}+{dec_dms}&-c.rs=10",
        "Aladin": (
            f"https://aladin.cds.unistra.fr/AladinLite/"
            f"?target={quote(ra_hms_space)}{sign}{quote(dec_dms_space)}"
            f"&fov=0.08&survey=P%2FPanSTARRS%2FDR1%2Fcolor-z-zg-g"
        ),
        "Extinction (NED)": (
            f"https://ned.ipac.caltech.edu/extinction_calculator"
            f"?in_csys=Equatorial&in_equinox=J2000.0&obs_epoch=2000.0"
            f"&ra={_ra_to_hms(ra, None)}&dec={_dec_to_dms(dec, None)}"
        ),
        "HEASARC": (
            f"https://heasarc.gsfc.nasa.gov/cgi-bin/vo/datascope/jds.pl"
            f"?position={quote(ra_hms_space)}%2C{quote(dec_dms_space)}&size=0.25"
        ),
    }

    header = "Survey links for"
    if source_id:
        header += f" {source_id} —"
    header += f" RA={ra:.6f}, Dec={dec:+.6f} ({ra_hms}, {dec_dms}):\n"

    lines = [header]
    for name, url in surveys.items():
        lines.append(f"  {name}: {url}")
    return "\n".join(lines)


# ─── ZTF cutout URLs ────────────────────────────────────────────────────────


@mcp.tool()
async def get_ztf_cutout_urls(
    ra: float,
    dec: float,
    size_arcmin: float = 1.0,
) -> str:
    """Query IRSA for ZTF image cutout URLs at a given position.

    Searches the IRSA ZTF archive for science and reference images covering
    the position, and returns direct download URLs for the FITS files.

    Args:
        ra: Right ascension in decimal degrees (J2000)
        dec: Declination in decimal degrees (J2000)
        size_arcmin: Search region size in arcminutes (default 1.0)
    """
    size_deg = size_arcmin / 60.0
    base_search = "https://irsa.ipac.caltech.edu/ibe/search/ztf/products"
    base_data = "https://irsa.ipac.caltech.edu/ibe/data/ztf/products"

    results = []

    # Query for science images
    sci_url = f"{base_search}/sci?POS={ra:.6f},{dec:.6f}&SIZE={size_deg:.6f}&ct=csv"
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(sci_url)
        if resp.is_success and resp.text.strip():
            reader = csv.DictReader(io.StringIO(resp.text))
            rows = list(reader)
            if rows:
                results.append(f"Found {len(rows)} science image(s).\n")
                for i, row in enumerate(rows[:5]):
                    field = row.get("field", "").zfill(6)
                    filt = row.get("filtercode", "")
                    ccdid = row.get("ccdid", "").zfill(2)
                    qid = row.get("qid", "")
                    filefracday = row.get("filefracday", "")
                    imgtypecode = row.get("imgtypecode", "o")
                    fits_url = (
                        f"{base_data}/sci/{filefracday[:4]}/{filefracday[4:8]}"
                        f"/{filefracday}/ztf_{filefracday}_{field}_{filt}"
                        f"_c{ccdid}_{imgtypecode}_q{qid}_sciimg.fits"
                    )
                    results.append(
                        f"  Science #{i + 1}: filter={filt} field={field} "
                        f"ccd={ccdid} quad={qid}\n    {fits_url}"
                    )
            else:
                results.append("No science images found at this position.")
    except Exception as e:
        results.append(f"Science image search error: {e}")

    # Query for reference images
    ref_url = f"{base_search}/ref?POS={ra:.6f},{dec:.6f}&SIZE={size_deg:.6f}&ct=csv"
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(ref_url)
        if resp.is_success and resp.text.strip():
            reader = csv.DictReader(io.StringIO(resp.text))
            rows = list(reader)
            if rows:
                results.append(f"\nFound {len(rows)} reference image(s).\n")
                for i, row in enumerate(rows[:5]):
                    field = row.get("field", "").zfill(6)
                    filt = row.get("filtercode", "")
                    ccdid = row.get("ccdid", "").zfill(2)
                    qid = row.get("qid", "")
                    fits_url = (
                        f"{base_data}/ref/{field[:3]}/field{field}/{filt}"
                        f"/ccd{ccdid}/q{qid}"
                        f"/ztf_{field}_{filt}_c{ccdid}_q{qid}_refimg.fits"
                    )
                    results.append(
                        f"  Reference #{i + 1}: filter={filt} field={field} "
                        f"ccd={ccdid} quad={qid}\n    {fits_url}"
                    )
            else:
                results.append("\nNo reference images found at this position.")
    except Exception as e:
        results.append(f"\nReference image search error: {e}")

    viewer_url = (
        f"https://irsa.ipac.caltech.edu/applications/ztf/"
        f"#id=Hydra_ztf_ztf_image_pos&RequestClass=ServerRequest"
        f"&DoSearch=true&intersect=CENTER&subsize=0.139"
        f"&mcenter=all&dpLevel=sci,ref,diff"
        f"&UserTargetWorldPt={ra};{dec};EQ_J2000"
    )
    results.append(f"\nInteractive IRSA ZTF viewer: {viewer_url}")

    return "\n".join(results)


# ─── SkyPortal cone search ──────────────────────────────────────────────────


@mcp.tool()
async def search_sources_near_position(
    ra: float | None = None,
    dec: float | None = None,
    source_id: str | None = None,
    radius_arcsec: float = 10.0,
    num_per_page: int = 100,
) -> str:
    """Search for sources in SkyPortal near a position (cone search).

    Finds all sources within a specified radius of a sky position. Useful for
    checking if a source already exists in SkyPortal at a given location, or
    finding nearby sources.

    Provide either ra/dec coordinates or a source_id to auto-resolve coordinates.

    Args:
        ra: Right ascension in decimal degrees (J2000). Not needed if
            source_id is provided.
        dec: Declination in decimal degrees (J2000). Not needed if
             source_id is provided.
        source_id: SkyPortal source ID (e.g., "ZTF21aaaaaaa"). RA/Dec
                   will be looked up automatically. Requires authentication.
        radius_arcsec: Search radius in arcseconds (default: 10.0)
        num_per_page: Maximum number of sources to return (default: 100)

    Returns:
        List of sources within the radius, sorted by separation. Includes
        source ID, coordinates, separation, and saved groups.
    """
    token = get_skyportal_token()
    if not token:
        return "Not authenticated. Configure SKYPORTAL_TOKEN or send Bearer token."

    # Resolve coordinates from source_id if needed
    if source_id and (ra is None or dec is None):
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(
                    f"{SKYPORTAL_URL}/api/sources/{source_id}",
                    headers={"Authorization": f"token {token}"},
                )
            resp.raise_for_status()
            src = resp.json().get("data", {})
            ra = src.get("ra")
            dec = src.get("dec")
            if ra is None or dec is None:
                return f"Could not resolve coordinates for source {source_id}"
        except Exception as e:
            return f"Error looking up source {source_id}: {e}"

    if ra is None or dec is None:
        return "Provide either source_id or both ra and dec."

    # Query SkyPortal for all sources (will filter client-side)
    # Note: SkyPortal's /api/sources doesn't have built-in spatial filtering,
    # so we fetch sources and compute separations client-side
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.get(
                f"{SKYPORTAL_URL}/api/sources",
                headers={"Authorization": f"token {token}"},
                params={"numPerPage": num_per_page * 10, "includeComments": False},
            )
        resp.raise_for_status()
    except httpx.HTTPStatusError as e:
        return f"HTTP Error {e.response.status_code}: {e.response.text}"
    except Exception as e:
        return f"Error querying sources: {e}"

    sources = resp.json().get("data", {}).get("sources", [])
    if not sources:
        return "No sources found in SkyPortal (or no access to any groups)."

    # Compute separations using simple angular distance
    import math

    def angular_separation(ra1: float, dec1: float, ra2: float, dec2: float) -> float:
        """Compute angular separation in arcseconds using haversine formula."""
        ra1_rad = math.radians(ra1)
        dec1_rad = math.radians(dec1)
        ra2_rad = math.radians(ra2)
        dec2_rad = math.radians(dec2)

        delta_ra = ra2_rad - ra1_rad
        delta_dec = dec2_rad - dec1_rad

        a = (
            math.sin(delta_dec / 2) ** 2
            + math.cos(dec1_rad) * math.cos(dec2_rad) * math.sin(delta_ra / 2) ** 2
        )
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return math.degrees(c) * 3600  # Convert to arcseconds

    # Filter sources by separation
    nearby_sources = []
    for src in sources:
        src_ra = src.get("ra")
        src_dec = src.get("dec")
        if src_ra is None or src_dec is None:
            continue

        sep = angular_separation(ra, dec, src_ra, src_dec)
        if sep <= radius_arcsec:
            nearby_sources.append(
                {
                    "id": src.get("id", ""),
                    "ra": src_ra,
                    "dec": src_dec,
                    "separation_arcsec": sep,
                    "groups": [g.get("name", "") for g in src.get("groups", [])],
                }
            )

    # Sort by separation
    nearby_sources.sort(key=lambda x: x["separation_arcsec"])

    # Limit to num_per_page
    nearby_sources = nearby_sources[:num_per_page]

    if not nearby_sources:
        return (
            f"No sources found within {radius_arcsec:.1f} arcsec of "
            f"RA={ra:.6f}, Dec={dec:+.6f}"
        )

    # Format output
    ra_hms = _ra_to_hms(ra)
    dec_dms = _dec_to_dms(dec)
    header = f'Sources within {radius_arcsec:.1f}" of RA={ra:.6f}, Dec={dec:+.6f} ({ra_hms}, {dec_dms}):\n'
    lines = [header]

    for src in nearby_sources:
        groups_str = ", ".join(src["groups"]) if src["groups"] else "(no groups)"
        lines.append(
            f'  • {src["id"]}: {src["separation_arcsec"]:.2f}" away '
            f"[RA={src['ra']:.6f}, Dec={src['dec']:+.6f}] — {groups_str}"
        )

    lines.append(f"\nTotal: {len(nearby_sources)} source(s)")

    return "\n".join(lines)
