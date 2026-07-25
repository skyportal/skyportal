# pyright: reportMissingTypeStubs=false
"""Bulk analysis tools using ztfquery for large-scale data operations."""

import json

from ..server import mcp
from . import code_templates


@mcp.tool()
async def generate_bulk_lightcurve_code(
    sources: str,
    filters: str = "ztfg,ztfr,ztfi",
    include_plots: bool = True,
) -> str:
    """Generate a Jupyter notebook to bulk download ZTF light curves from Fritz.

    Creates a ready-to-run .ipynb notebook that uses ztfquery's Fritz
    integration to download **alert photometry** (detection epochs) for
    multiple sources with multiprocessing, save results to CSV, and create
    interactive Plotly plots.

    **Note:** This downloads alert photometry, not forced photometry.
    For forced photometry (including non-detections/upper limits), use the
    IRSA ZTF forced photometry service.

    **Requires:** ztfquery + Fritz API token.
    Setup: `from ztfquery.io import set_account; set_account('fritz', token_based=True)`

    Args:
        sources: Comma-separated list of ZTF source names, or JSON array.
                Example: "ZTF24aaaaaaa,ZTF24aaaaaab,ZTF24aaaaaac"
                Or: '["ZTF24aaaaaaa", "ZTF24aaaaaab"]'
        filters: Comma-separated filter names (default: "ztfg,ztfr,ztfi")
        include_plots: Generate interactive Plotly light curve plots (default: True)

    Returns:
        Path to the generated Jupyter notebook in ztf_lightcurves/ directory.
        The notebook downloads data from Fritz, saves per-source CSVs,
        and plots interactive light curves with Plotly.

    Example:
        sources = "ZTF21aaaaaaa,ZTF21aaaaaab,ZTF21aaaaaac"
        filters = "ztfg,ztfr"
        → Generates notebook to download g/r photometry for 3 sources
    """
    # Parse sources (handle both comma-separated and JSON)
    if sources.strip().startswith("["):
        source_list = json.loads(sources)
    else:
        source_list = [s.strip() for s in sources.split(",") if s.strip()]

    # Parse filters
    filter_list = [f.strip() for f in filters.split(",") if f.strip()]

    if not source_list:
        return "Error: No sources provided"

    if not filter_list:
        return "Error: No filters provided"

    return code_templates.generate_bulk_lightcurve_query(
        source_list=source_list,
        filters=filter_list,
        include_plots=include_plots,
    )


@mcp.tool()
async def generate_cone_search_code(
    coordinates: str,
    radius_arcsec: float = 2.0,
) -> str:
    """Generate code to perform ZTF cone searches at multiple positions.

    This tool generates Python code that searches for ZTF detections within
    a radius of specified sky coordinates. Useful for cross-matching catalogs
    or checking if known positions have ZTF coverage.

    **Use Case:** When you have a list of coordinates (e.g., from a catalog,
    TNS, or previous observations) and want to find all ZTF detections nearby.

    Args:
        coordinates: Comma-separated "RA,Dec" pairs or JSON array of [RA, Dec].
                    RA/Dec in decimal degrees (J2000).
                    Examples:
                    - "150.0,2.5,151.2,3.1,152.5,2.8"  (3 positions)
                    - '[[150.0, 2.5], [151.2, 3.1]]'  (JSON format)
        radius_arcsec: Search radius in arcseconds (default: 2.0)

    Returns:
        Python code for Jupyter notebook that:
        - Performs cone search at each position
        - Saves all detections to 'ztf_cone_search/cone_search_results.csv'
        - Creates summary with detection counts per position
        - Includes query coordinates for cross-reference

    Example:
        coordinates = "150.5,2.3,151.2,3.1"
        radius_arcsec = 5.0
        → Searches within 5" of two positions
    """
    # Parse coordinates
    if coordinates.strip().startswith("["):
        # JSON format: [[ra1, dec1], [ra2, dec2], ...]
        coord_list = json.loads(coordinates)
    else:
        # Comma-separated: ra1,dec1,ra2,dec2,...
        vals = [float(x.strip()) for x in coordinates.split(",")]
        if len(vals) % 2 != 0:
            return "Error: Coordinates must be pairs of (RA, Dec)"
        coord_list = [(vals[i], vals[i + 1]) for i in range(0, len(vals), 2)]

    if not coord_list:
        return "Error: No coordinates provided"

    return code_templates.generate_cone_search_query(
        ra_dec_list=coord_list,
        radius_arcsec=radius_arcsec,
    )


@mcp.tool()
async def generate_fritz_bulk_query_code(
    sources: str,
    include_spectra: bool = True,
) -> str:
    """Generate code to bulk query Fritz/SkyPortal for multiple sources.

    This tool generates code that uses ztfquery's Fritz interface to download
    photometry, spectra, and metadata for multiple sources from Fritz.

    **Use Case:** When you need to download data products from Fritz for
    many sources at once (faster than individual API calls).

    **Note:** Requires Fritz API token.
    Setup: `from ztfquery.io import set_account; set_account('fritz', token_based=True)`

    Args:
        sources: Comma-separated source names or JSON array
                Example: "ZTF24aaaaaaa,AT2024abc,SN2024xyz"
        include_spectra: Download spectra in addition to photometry (default: True)

    Returns:
        Python code for Jupyter notebook that:
        - Queries Fritz API for each source
        - Downloads photometry and (optionally) spectra
        - Saves individual files: {source}_photometry.csv, {source}_spectra.csv
        - Creates summary with redshifts, classifications, data counts
        - Saves to 'fritz_data/' directory

    Example:
        sources = "ZTF21aaaaaaa,AT2021abc"
        include_spectra = True
        → Downloads photometry + spectra for both sources
    """
    # Parse sources
    if sources.strip().startswith("["):
        source_list = json.loads(sources)
    else:
        source_list = [s.strip() for s in sources.split(",") if s.strip()]

    if not source_list:
        return "Error: No sources provided"

    return code_templates.generate_fritz_bulk_query(
        source_list=source_list,
        include_spectra=include_spectra,
    )


@mcp.tool()
async def generate_alert_download_code(
    sources: str,
    with_cutouts: bool = True,
) -> str:
    """Generate code to download ZTF alert packets for multiple sources.

    This tool generates code that downloads raw ZTF alert packets, which contain
    the full alert history including candidate info, cutouts, and previous detections.

    **Use Case:** When you need complete alert history or want to access alert-level
    data that isn't available in forced photometry.

    Args:
        sources: Comma-separated ZTF source names or JSON array
                Example: "ZTF24aaaaaaa,ZTF24aaaaaab"
        with_cutouts: Download cutout images (science, ref, diff) (default: True)

    Returns:
        Python code for Jupyter notebook that:
        - Downloads alert packets for each source
        - Saves alerts as JSON files
        - Optionally downloads FITS cutouts (science, reference, difference)
        - Saves to 'ztf_alerts/' and 'ztf_alerts/cutouts/' directories
        - Creates summary with alert counts

    Example:
        sources = "ZTF21aaaaaaa,ZTF21aaaaaab"
        with_cutouts = True
        → Downloads full alert history + cutouts for both sources
    """
    # Parse sources
    if sources.strip().startswith("["):
        source_list = json.loads(sources)
    else:
        source_list = [s.strip() for s in sources.split(",") if s.strip()]

    if not source_list:
        return "Error: No sources provided"

    return code_templates.generate_alert_query(
        source_list=source_list,
        with_cutouts=with_cutouts,
    )


@mcp.tool()
async def generate_field_visualization_code(
    field_id: int,
    ccd_id: int | None = None,
) -> str:
    """Generate code to visualize ZTF field and CCD coverage.

    This tool generates code to create sky maps showing ZTF field footprints
    and CCD layouts. Useful for understanding coverage and planning observations.

    **Use Case:** When you need to visualize which parts of the sky are covered
    by specific ZTF fields or CCDs.

    Args:
        field_id: ZTF field ID (1-1895)
        ccd_id: Optional CCD ID to highlight (1-16). If None, shows full field.

    Returns:
        Python code for Jupyter notebook that:
        - Creates Mollweide projection sky map
        - Shows field footprint on sky
        - Highlights specific CCD if requested
        - Displays RA/Dec coverage information

    Example:
        field_id = 300
        ccd_id = 8
        → Shows field 300 with CCD 8 highlighted
    """
    return code_templates.generate_field_visualization(
        field_id=field_id,
        ccd_id=ccd_id,
    )
