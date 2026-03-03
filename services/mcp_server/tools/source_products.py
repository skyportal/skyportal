# pyright: reportMissingTypeStubs=false
"""Single-source data product tools: photometry, spectra, classifications, comments."""

import csv
import io

import httpx

from ..server import SKYPORTAL_URL, get_skyportal_token, mcp

# ─── Source ID Resolution Helper ────────────────────────────────────────────


async def resolve_source_id(name_or_id: str) -> str | None:
    """Resolve ZTF name, TNS name, or SkyPortal ID to canonical SkyPortal obj_id.

    Accepts any of:
    - SkyPortal obj_id (e.g., "ZTF21aaaaaaa")
    - ZTF designation (e.g., "ZTF21aaaaaaa")
    - TNS name (e.g., "AT2021abc", "SN2021xyz")

    Returns:
        SkyPortal obj_id if found, None if not found or error
    """
    token = get_skyportal_token()
    if not token:
        return None

    # Try direct lookup first (assume it's already an obj_id)
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"{SKYPORTAL_URL}/api/sources/{name_or_id}",
                headers={"Authorization": f"token {token}"},
            )
        if resp.is_success:
            data = resp.json().get("data", {})
            return data.get("id")
    except Exception:
        pass

    # If direct lookup failed, try searching by name
    # This handles TNS names stored in altdata
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            # Search for sources - SkyPortal's search handles various name formats
            resp = await client.get(
                f"{SKYPORTAL_URL}/api/sources",
                headers={"Authorization": f"token {token}"},
                params={"sourceID": name_or_id, "includeComments": "false"},
            )
        if resp.is_success:
            sources = resp.json().get("data", {}).get("sources", [])
            if sources:
                return sources[0].get("id")
    except Exception:
        pass

    return None


@mcp.tool()
async def get_source_photometry(
    source_name: str,
    format: str = "mag",
    magsys: str = "ab",
    filters: str | None = None,
) -> str:
    """Retrieve photometry for a source as a CSV table.

    Returns all photometry points for the source in CSV format, suitable for
    direct analysis or loading into a pandas DataFrame.

    Columns returned (mag format):
        mjd, filter, mag, magerr, limiting_mag, snr, instrument_name, origin

    Columns returned (flux format):
        mjd, filter, flux, fluxerr, snr, instrument_name, origin

    Args:
        source_name: Source identifier - can be SkyPortal obj_id, ZTF name, or TNS name
        format: Output format — "mag" (default) or "flux"
        magsys: Magnitude system — "ab" (default), "vega", etc.
        filters: Comma-separated photometric filter names to include
                 (e.g., "ztfg,ztfr,ztfi"). If omitted, returns all filters.

    Returns:
        CSV-formatted text with one row per photometry point, sorted by MJD.
        Includes a summary header comment with source ID and number of points.
    """
    token = get_skyportal_token()
    if not token:
        return "Not authenticated. Configure SKYPORTAL_TOKEN or send Bearer token."

    # Resolve source name to obj_id
    source_id = await resolve_source_id(source_name)
    if not source_id:
        return f"Error: Could not resolve '{source_name}' to a SkyPortal source."

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{SKYPORTAL_URL}/api/sources/{source_id}/photometry",
                headers={"Authorization": f"token {token}"},
                params={"format": format, "magsys": magsys},
            )
        resp.raise_for_status()
    except httpx.HTTPStatusError as e:
        return f"HTTP Error {e.response.status_code}: {e.response.text}"
    except Exception as e:
        return f"Error fetching photometry: {e}"

    data = resp.json().get("data", [])
    if not data:
        return f"No photometry found for source {source_id}"

    # Filter by band if requested
    if filters:
        allowed = {f.strip() for f in filters.split(",")}
        data = [p for p in data if p.get("filter") in allowed]
        if not data:
            return f"No photometry found for source {source_id} in filters: {filters}"

    # Sort by MJD
    data.sort(key=lambda p: p.get("mjd", 0))

    # Build CSV
    if format == "flux":
        columns = [
            "mjd",
            "filter",
            "flux",
            "fluxerr",
            "snr",
            "instrument_name",
            "origin",
        ]
    else:
        columns = [
            "mjd",
            "filter",
            "mag",
            "magerr",
            "limiting_mag",
            "snr",
            "instrument_name",
            "origin",
        ]

    output = io.StringIO()
    # Summary comment
    unique_filters = sorted({p.get("filter", "") for p in data})
    output.write(
        f"# {source_id}: {len(data)} points, filters: {', '.join(unique_filters)}\n"
    )

    writer = csv.DictWriter(output, fieldnames=columns, extrasaction="ignore")
    writer.writeheader()
    for point in data:
        row = {col: point.get(col, "") for col in columns}
        # Round numeric values for readability
        for key in ("mjd", "mag", "magerr", "limiting_mag", "flux", "fluxerr", "snr"):
            if key in row and row[key] not in ("", None):
                try:
                    row[key] = round(float(row[key]), 5)
                except (ValueError, TypeError):
                    pass
        writer.writerow(row)

    return output.getvalue()


@mcp.tool()
async def get_source_spectra(
    source_name: str,
    format: str = "csv",
) -> str:
    """Retrieve spectra for a source.

    Returns all spectra for the source. For CSV format, returns one spectrum
    per output block with wavelength and flux columns.

    Args:
        source_name: Source identifier - can be SkyPortal obj_id, ZTF name, or TNS name (e.g., "ZTF21aaaaaaa")
        format: Output format — "csv" (default) or "json"

    Returns:
        For CSV: Each spectrum as a separate CSV block with wavelength, flux,
        (and error if available), preceded by a header with metadata.
        For JSON: Raw API response as formatted JSON.
    """
    token = get_skyportal_token()
    if not token:
        return "Not authenticated. Configure SKYPORTAL_TOKEN or send Bearer token."

    # Resolve source name to obj_id
    source_id = await resolve_source_id(source_name)
    if not source_id:
        return f"Error: Could not resolve '{source_name}' to a SkyPortal source."

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{SKYPORTAL_URL}/api/sources/{source_id}/spectra",
                headers={"Authorization": f"token {token}"},
            )
        resp.raise_for_status()
    except httpx.HTTPStatusError as e:
        return f"HTTP Error {e.response.status_code}: {e.response.text}"
    except Exception as e:
        return f"Error fetching spectra: {e}"

    data = resp.json().get("data", [])
    if not data:
        return f"No spectra found for source {source_id}"

    if format == "json":
        import json

        return json.dumps(data, indent=2)

    # CSV format: one spectrum per block
    results = [f"Found {len(data)} spectrum/spectra for {source_id}\n"]

    for i, spec in enumerate(data, 1):
        wavelengths = spec.get("wavelengths", [])
        fluxes = spec.get("fluxes", [])
        errors = spec.get("errors")
        observed_at = spec.get("observed_at", "unknown")
        instrument = spec.get("instrument_name", "unknown")
        origin = spec.get("origin", "")

        if not wavelengths or not fluxes:
            continue

        results.append(
            f"\n# Spectrum {i}: observed {observed_at}, "
            f"instrument: {instrument}, origin: {origin}"
        )
        results.append(f"# {len(wavelengths)} points\n")

        output = io.StringIO()
        if errors:
            writer = csv.writer(output)
            writer.writerow(["wavelength", "flux", "error"])
            for w, f, e in zip(wavelengths, fluxes, errors):
                writer.writerow([w, f, e])
        else:
            writer = csv.writer(output)
            writer.writerow(["wavelength", "flux"])
            for w, f in zip(wavelengths, fluxes):
                writer.writerow([w, f])

        results.append(output.getvalue())

    return "\n".join(results)


@mcp.tool()
async def get_source_classifications(source_name: str) -> str:
    """Retrieve classifications for a source.

    Returns all classifications assigned to the source, including the
    classification name, probability, and who made the classification.

    Args:
        source_name: Source identifier - can be SkyPortal obj_id, ZTF name, or TNS name (e.g., "ZTF21aaaaaaa")

    Returns:
        Summary of classifications with classification type, probability,
        classifier name, and classification date.
    """
    token = get_skyportal_token()
    if not token:
        return "Not authenticated. Configure SKYPORTAL_TOKEN or send Bearer token."

    # Resolve source name to obj_id
    source_id = await resolve_source_id(source_name)
    if not source_id:
        return f"Error: Could not resolve '{source_name}' to a SkyPortal source."

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{SKYPORTAL_URL}/api/sources/{source_id}/classifications",
                headers={"Authorization": f"token {token}"},
            )
        resp.raise_for_status()
    except httpx.HTTPStatusError as e:
        return f"HTTP Error {e.response.status_code}: {e.response.text}"
    except Exception as e:
        return f"Error fetching classifications: {e}"

    data = resp.json().get("data", [])
    if not data:
        return f"No classifications found for source {source_id}"

    lines = [f"Classifications for {source_id}:\n"]
    for cls in data:
        classification = cls.get("classification", "Unknown")
        probability = cls.get("probability")
        author = cls.get("author_name", "Unknown")
        created_at = cls.get("created_at", "Unknown")
        taxonomy = cls.get("taxonomy_name", "")

        prob_str = f" (p={probability:.3f})" if probability is not None else ""
        tax_str = f" [{taxonomy}]" if taxonomy else ""

        lines.append(
            f"  • {classification}{prob_str}{tax_str}\n    by {author} on {created_at}"
        )

    return "\n".join(lines)


@mcp.tool()
async def get_source_comments_and_annotations(source_name: str) -> str:
    """Retrieve comments and annotations for a source.

    Returns a summary of user comments and system/ML annotations on the source.
    Comments are human-readable notes; annotations are structured data (e.g.,
    ML scores, cross-match results).

    Args:
        source_name: Source identifier - can be SkyPortal obj_id, ZTF name, or TNS name (e.g., "ZTF21aaaaaaa")

    Returns:
        Summary with comments (text, author, date) and annotations
        (key-value pairs with origin).
    """
    token = get_skyportal_token()
    if not token:
        return "Not authenticated. Configure SKYPORTAL_TOKEN or send Bearer token."

    # Resolve source name to obj_id
    source_id = await resolve_source_id(source_name)
    if not source_id:
        return f"Error: Could not resolve '{source_name}' to a SkyPortal source."

    # Fetch both comments and source data (which includes annotations)
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            # Get comments
            comments_resp = await client.get(
                f"{SKYPORTAL_URL}/api/sources/{source_id}/comments",
                headers={"Authorization": f"token {token}"},
            )
            # Get source (includes annotations)
            source_resp = await client.get(
                f"{SKYPORTAL_URL}/api/sources/{source_id}",
                headers={"Authorization": f"token {token}"},
            )
        comments_resp.raise_for_status()
        source_resp.raise_for_status()
    except httpx.HTTPStatusError as e:
        return f"HTTP Error {e.response.status_code}: {e.response.text}"
    except Exception as e:
        return f"Error fetching comments/annotations: {e}"

    comments = comments_resp.json().get("data", [])
    source_data = source_resp.json().get("data", {})
    annotations = source_data.get("annotations", [])

    lines = [f"Comments and annotations for {source_id}:\n"]

    # Comments section
    if comments:
        lines.append("\n## Comments\n")
        for comment in comments:
            text = comment.get("text", "")
            author = comment.get("author", {}).get("username", "Unknown")
            created_at = comment.get("created_at", "Unknown")
            lines.append(f"  [{created_at}] {author}:")
            lines.append(f"    {text}\n")
    else:
        lines.append("\n## Comments\n  (none)\n")

    # Annotations section
    if annotations:
        lines.append("\n## Annotations\n")
        for annot in annotations:
            origin = annot.get("origin", "Unknown")
            data = annot.get("data", {})
            lines.append(f"  • {origin}:")
            for key, value in data.items():
                lines.append(f"      {key}: {value}")
            lines.append("")
    else:
        lines.append("\n## Annotations\n  (none)\n")

    return "\n".join(lines)


@mcp.tool()
async def get_source_host_galaxy(source_name: str) -> str:
    """Retrieve host galaxy information for a source.

    Returns the associated host galaxy from SkyPortal's galaxy catalogs,
    including angular separation (offset) and physical distance.

    SkyPortal can link sources to host galaxies from catalogs like GLADE+.
    If a host association exists, this returns the galaxy's properties.

    Args:
        source_name: Source identifier - can be SkyPortal obj_id, ZTF name, or TNS name (e.g., "ZTF21aaaaaaa")

    Returns:
        Host galaxy summary with name, position, redshift, distance, stellar mass,
        angular offset from source, and physical separation. If no host is
        associated, returns a message indicating this.
    """
    token = get_skyportal_token()
    if not token:
        return "Not authenticated. Configure SKYPORTAL_TOKEN or send Bearer token."

    # Resolve source name to obj_id
    source_id = await resolve_source_id(source_name)
    if not source_id:
        return f"Error: Could not resolve '{source_name}' to a SkyPortal source."

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{SKYPORTAL_URL}/api/sources/{source_id}",
                headers={"Authorization": f"token {token}"},
            )
        resp.raise_for_status()
    except httpx.HTTPStatusError as e:
        return f"HTTP Error {e.response.status_code}: {e.response.text}"
    except Exception as e:
        return f"Error fetching source: {e}"

    data = resp.json().get("data", {})
    host = data.get("host")

    if not host:
        return f"No host galaxy associated with source {source_id}"

    # Extract key host galaxy properties
    name = host.get("name", "Unknown")
    alt_name = host.get("alt_name")
    ra = host.get("ra")
    dec = host.get("dec")
    redshift = host.get("redshift")
    redshift_error = host.get("redshift_error")
    distmpc = host.get("distmpc")
    distmpc_unc = host.get("distmpc_unc")
    mstar = host.get("mstar")
    magb = host.get("magb")
    magk = host.get("magk")
    catalog_name = host.get("catalog_name", "Unknown")

    # Get offset and distance computed by SkyPortal
    host_offset = data.get("host_offset")  # arcsec
    host_distance = data.get("host_distance")  # kpc

    lines = [f"Host galaxy for {source_id}:\n"]

    # Galaxy identification
    lines.append(f"  Name: {name}")
    if alt_name:
        lines.append(f"  Alt. name: {alt_name}")
    lines.append(f"  Catalog: {catalog_name}\n")

    # Position
    if ra is not None and dec is not None:
        lines.append(f"  Position: RA={ra:.6f}, Dec={dec:+.6f} (J2000)")

    # Separation from source
    if host_offset is not None:
        lines.append(f"  Angular offset: {host_offset:.2f} arcsec")
    if host_distance is not None:
        lines.append(f"  Physical distance: {host_distance:.2f} kpc\n")
    else:
        lines.append("")

    # Redshift and distance
    if redshift is not None:
        z_str = f"z = {redshift:.6f}"
        if redshift_error is not None:
            z_str += f" ± {redshift_error:.6f}"
        lines.append(f"  Redshift: {z_str}")

    if distmpc is not None:
        dist_str = f"D = {distmpc:.1f} Mpc"
        if distmpc_unc is not None:
            dist_str += f" ± {distmpc_unc:.1f} Mpc"
        lines.append(f"  Distance: {dist_str}\n")
    else:
        lines.append("")

    # Galaxy properties
    if mstar is not None:
        lines.append(f"  Stellar mass: log(M*/M☉) = {mstar:.2f}")
    if magb is not None:
        lines.append(f"  B-band magnitude: {magb:.2f} mag")
    if magk is not None:
        lines.append(f"  K-band magnitude: {magk:.2f} mag")

    return "\n".join(lines)


@mcp.tool()
async def get_tns_summary(source_name: str) -> str:
    """SUMMARY TOOL: Generate complete TNS/AstroNote report for a transient.

    **USE THIS SINGLE TOOL when asked to create TNS reports, AstroNotes, or
    comprehensive source summaries.** It combines all relevant data in one call.

    This tool retrieves and formats ALL information needed for TNS submissions:
    - Source identification (coordinates in deg and HMS/DMS)
    - Discovery information (first detection, magnitude, date, instrument)
    - Latest photometry and peak brightness
    - Classification (type, probability, classifier)
    - Spectroscopy (dates, instruments, redshift)
    - Host galaxy information

    Accepts ANY source identifier: SkyPortal obj_id, ZTF name, or TNS name.

    **When to use:**
    - User asks to "create/generate/write TNS report"
    - User asks to "draft AstroNote" or "prepare ATel"
    - User asks for "summary of [source]"
    - User mentions "TNS submission" or "classification report"

    **Do NOT** call multiple other tools (photometry, spectra, classifications)
    separately when this single tool provides everything together.

    Args:
        source_name: Source identifier - can be:
            - SkyPortal obj_id (e.g., "ZTF21aaaaaaa")
            - ZTF designation (e.g., "ZTF21aaaaaaa")
            - TNS name (e.g., "AT2021abc", "SN2021xyz")

    Returns:
        Formatted text summary with all TNS-relevant information, ready to
        copy into TNS forms or use as AstroNote draft. Includes coordinates,
        discovery data, photometry, classification, spectra, and host info.

        **IMPORTANT:** When presenting this to the user, display the summary
        in a markdown code block (```text) for easy reading and copying.
    """
    token = get_skyportal_token()
    if not token:
        return "Not authenticated. Configure SKYPORTAL_TOKEN or send Bearer token."

    # Resolve source name to obj_id
    obj_id = await resolve_source_id(source_name)
    if not obj_id:
        return f"Error: Could not resolve '{source_name}' to a SkyPortal source. Try using the exact SkyPortal obj_id."

    # Fetch comprehensive source data
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{SKYPORTAL_URL}/api/sources/{obj_id}",
                headers={"Authorization": f"token {token}"},
                params={
                    "includePhotometry": "true",
                    "includeSpectra": "true",
                    "includeComments": "false",
                },
            )
        resp.raise_for_status()
        data = resp.json().get("data", {})
    except httpx.HTTPStatusError as e:
        return f"HTTP Error {e.response.status_code}: {e.response.text}"
    except Exception as e:
        return f"Error fetching source: {e}"

    # Extract key information
    ra = data.get("ra")
    dec = data.get("dec")
    redshift = data.get("redshift")
    redshift_error = data.get("redshift_error")

    # Get TNS info if available
    altdata = data.get("altdata", {})
    tns_info = altdata.get("tns", {}) if altdata else {}
    tns_name = tns_info.get("name")

    # Construct TNS URL if source is already reported
    tns_url = None
    if tns_name:
        # TNS URL format: https://www.wis-tns.org/object/{name}
        tns_url = f"https://www.wis-tns.org/object/{tns_name}"

    # Get classifications
    classifications = data.get("classifications", [])
    latest_class = None
    if classifications:
        sorted_classes = sorted(
            classifications, key=lambda x: x.get("created_at", ""), reverse=True
        )
        latest_class = sorted_classes[0] if sorted_classes else None

    # Get photometry
    photometry = data.get("photometry", [])
    first_det = None
    latest_det = None
    peak_mag = None

    if photometry:
        sorted_phot = sorted(photometry, key=lambda x: x.get("mjd", 0))
        first_det = sorted_phot[0]
        latest_det = sorted_phot[-1]

        # Find peak (brightest = minimum magnitude)
        mags = [p["mag"] for p in photometry if p.get("mag") is not None]
        if mags:
            peak_mag = min(mags)

    # Get spectra
    spectra = data.get("spectra", [])
    latest_spectrum = None
    if spectra:
        sorted_spectra = sorted(
            spectra, key=lambda x: x.get("observed_at", ""), reverse=True
        )
        latest_spectrum = sorted_spectra[0]

    # Build summary
    lines = ["=" * 80]
    lines.append("TNS / ASTRONOTE SUMMARY")
    lines.append("=" * 80)
    lines.append("")

    # Source Identification
    lines.append("## SOURCE IDENTIFICATION")
    lines.append(f"SkyPortal ID:   {obj_id}")
    if tns_name:
        lines.append(f"TNS Name:       {tns_name}")
        if tns_url:
            lines.append(f"TNS Report:     {tns_url}")
            lines.append("                ⚠️  This source is already reported to TNS")
    if ra is not None and dec is not None:
        lines.append(f"RA (J2000):     {ra:.6f}°  ({_deg_to_hms(ra)})")
        lines.append(f"Dec (J2000):    {dec:+.6f}°  ({_deg_to_dms(dec)})")
    lines.append("")

    # Discovery Information
    lines.append("## DISCOVERY INFORMATION")
    if first_det:
        mjd = first_det.get("mjd")
        mag = first_det.get("mag")
        magerr = first_det.get("magerr")
        filt = first_det.get("filter", "")
        instrument = first_det.get("instrument_name", "Unknown")

        if mjd:
            from astropy.time import Time

            t = Time(mjd, format="mjd")
            iso_date = str(t.iso).split()[0]  # YYYY-MM-DD
            lines.append(f"First Detection:  MJD {mjd:.2f} ({iso_date})")
        if mag is not None:
            mag_str = f"{mag:.2f}"
            if magerr:
                mag_str += f" ± {magerr:.2f}"
            lines.append(f"Discovery Mag:    {mag_str} ({filt})")
        lines.append(f"Instrument:       {instrument}")
    else:
        lines.append("No photometry available")
    lines.append("")

    # Latest Photometry
    lines.append("## LATEST PHOTOMETRY")
    if latest_det:
        mjd = latest_det.get("mjd")
        mag = latest_det.get("mag")
        magerr = latest_det.get("magerr")
        filt = latest_det.get("filter", "")

        if mjd:
            from astropy.time import Time

            t = Time(mjd, format="mjd")
            iso_date = str(t.iso).split()[0]
            lines.append(f"Date:       MJD {mjd:.2f} ({iso_date})")
        if mag is not None:
            mag_str = f"{mag:.2f}"
            if magerr:
                mag_str += f" ± {magerr:.2f}"
            lines.append(f"Magnitude:  {mag_str} ({filt})")

        # Summary stats
        if len(photometry) > 1:
            lines.append(
                f"Peak mag:   {peak_mag:.2f} (from {len(photometry)} detections)"
            )
            lines.append("            Note: Peak = min(mag), not from light curve fit")
    lines.append("")

    # Classification
    lines.append("## CLASSIFICATION")
    if latest_class:
        class_name = latest_class.get("classification", "Unknown")
        class_date = latest_class.get("created_at", "")
        probability = latest_class.get("probability")
        author = latest_class.get("author_name", "")

        lines.append(f"Type:        {class_name}")
        if probability is not None:
            lines.append(f"Probability: {probability:.2f}")
        if class_date:
            lines.append(f"Date:        {class_date.split('T')[0]}")
        if author:
            lines.append(f"Classifier:  {author}")
    else:
        lines.append("No classification available")
    lines.append("")

    # Spectroscopy & Redshift
    lines.append("## SPECTROSCOPY & REDSHIFT")
    if redshift is not None:
        z_str = f"{redshift:.4f}"
        if redshift_error:
            z_str += f" ± {redshift_error:.4f}"
        lines.append(f"Redshift:    {z_str}")

    if latest_spectrum:
        spec_date = latest_spectrum.get("observed_at", "")
        instrument = latest_spectrum.get("instrument_name", "")

        if spec_date:
            lines.append(f"Latest Spectrum: {spec_date.split('T')[0]}")
        if instrument:
            lines.append(f"Instrument:      {instrument}")
        lines.append(f"Total Spectra:   {len(spectra)}")

    if not redshift and not latest_spectrum:
        lines.append("No spectroscopic data available")
    lines.append("")

    # Host Galaxy
    lines.append("## HOST GALAXY")
    host_offset = altdata.get("host_offset") if altdata else None
    if host_offset is not None:
        lines.append(f"Host Offset: {host_offset:.2f} arcsec")
    else:
        lines.append("Host information not available")
    lines.append("")

    # Footer
    lines.append("=" * 80)
    lines.append(f"Generated from SkyPortal source: {obj_id}")
    if source_name != obj_id:
        lines.append(f"(Resolved from input: {source_name})")
    lines.append("Ready for TNS submission or AstroNote drafting")
    lines.append("=" * 80)

    return "\n".join(lines)


def _deg_to_hms(deg: float) -> str:
    """Convert RA in degrees to HH:MM:SS.SS format."""
    hours = deg / 15.0
    h = int(hours)
    m = int((hours - h) * 60)
    s = ((hours - h) * 60 - m) * 60
    return f"{h:02d}h{m:02d}m{s:05.2f}s"


def _deg_to_dms(deg: float) -> str:
    """Convert Dec in degrees to DD:MM:SS.S format."""
    sign = "+" if deg >= 0 else "-"
    deg = abs(deg)
    d = int(deg)
    m = int((deg - d) * 60)
    s = ((deg - d) * 60 - m) * 60
    return f"{sign}{d:02d}d{m:02d}m{s:04.1f}s"
