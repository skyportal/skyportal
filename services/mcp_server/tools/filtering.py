# pyright: reportMissingTypeStubs=false
"""Candidate and source filtering tools."""

import json
from pathlib import Path

import httpx

from ..server import SKYPORTAL_URL, get_skyportal_token, mcp

RESOURCES_DIR = Path(__file__).parent.parent / "resources"


@mcp.resource("skyportal://filters/reference")
def get_filter_docs() -> str:
    """Candidate and source filtering reference guide"""
    return (RESOURCES_DIR / "candidate_filter_reference.md").read_text()


@mcp.tool()
def get_candidate_filter_reference() -> str:
    """Get the reference for filtering candidates and sources on Fritz/SkyPortal.

    Returns documentation on available query parameters for the /api/candidates
    endpoint: annotation-based filters for ML scores (real/bogus, star/galaxy),
    classification filters, redshift, photometry annotations, and more.

    Call this when a user asks to filter, search, or scan for specific types
    of transients. It tells you what's filterable via API queries vs what
    requires fetching data and doing custom computation.

    Note: This is for query-time filtering (scanning page searches), NOT for
    creating alert-time MongoDB filters that run on Kowalski.
    """
    return (RESOURCES_DIR / "candidate_filter_reference.md").read_text()


@mcp.tool()
async def filter_candidates(
    group_id: int | None = None,
    saved_status: str = "all",
    classifications: str | None = None,
    classifications_reject: str | None = None,
    min_redshift: float | None = None,
    max_redshift: float | None = None,
    annotation_filters: str | None = None,
    saved_after: str | None = None,
    saved_before: str | None = None,
    first_detected_after: str | None = None,
    last_detected_before: str | None = None,
    num_per_page: int = 100,
    page_number: int = 1,
) -> str:
    """Search for candidates matching specific criteria on the scanning page.

    This performs query-time filtering of existing candidates (not alert-time
    filtering). Use this to search the scanning page for candidates matching
    specific properties.

    IMPORTANT - Parameter Validation:
    Before executing this tool, ALWAYS confirm with the user that the filter
    parameters are reasonable. Explain what the filter will return and ask if
    they want to proceed. Examples:
    - "I'll search for SNe Ia with braai score > 0.9 saved after 2024-01-01. Proceed?"
    - "This will find likely galaxy transients (sgScore < 0.3). OK?"
    - "Filtering for TDE candidates with ACAI_score > 0.8. Sound good?"

    IMPORTANT - After Results:
    After showing results, offer to display the filter configuration JSON so
    the user can save it for future use or configure it in the UI.

    Args:
        group_id: Search within specific group ID (optional)
        saved_status: Saved status filter. Options:
            - "all" (default): all candidates
            - "savedToAllSelected": saved to all selected groups
            - "savedToAnySelected": saved to any selected group
            - "savedToAnyAccessible": saved to any accessible group
            - "notSavedToAnyAccessible": not saved to any accessible group
            - "notSavedToAnySelected": not saved to any selected group
            - "notSavedToAllSelected": not saved to all selected groups
        classifications: Comma-separated classifications to INCLUDE
            (e.g., "SN Ia,SN Ib/c,SN II")
        classifications_reject: Comma-separated classifications to EXCLUDE
            (e.g., "AGN,varstar,bogus")
        min_redshift: Minimum redshift (float)
        max_redshift: Maximum redshift (float)
        annotation_filters: JSON-encoded list of annotation filters. Each filter
            is an object with:
            - "origin": annotation origin (e.g., "braai", "kowalski", "Kowalski")
            - "key": annotation key (e.g., "braai", "sgScore", "ACAI_score")
            - "min": minimum value (optional, for range filters)
            - "max": maximum value (optional, for range filters)
            - "value": exact value (optional, for exact match filters)

            Common examples:
            - Real/bogus: [{"origin":"braai","key":"braai","min":0.8}]
            - Star/galaxy: [{"origin":"kowalski","key":"sgScore","max":0.3}]
            - ACAI score: [{"origin":"Kowalski","key":"ACAI_score","min":0.8}]
            - Combined: [{"origin":"braai","key":"braai","min":0.9},{"origin":"kowalski","key":"sgScore","max":0.3}]

            Note: Available annotations depend on your instance. Use
            get_candidate_filter_reference() or inspect sources to discover
            annotation origins/keys available.
        saved_after: Only candidates saved after this date (ISO: "2024-01-15")
        saved_before: Only candidates saved before this date (ISO)
        first_detected_after: Only sources first detected after this date
        last_detected_before: Only sources last detected before this date
        num_per_page: Number of results (default 100, max 500)
        page_number: Page number for pagination (default 1)

    Returns:
        CSV table with: obj_id, ra, dec, redshift, latest_mag, latest_filter,
        saved_at, classifications, and ML scores from annotation_filters.
        Includes summary header with total matches and filter criteria.
        At the end, includes the filter configuration JSON for saving/reuse.
    """
    token = get_skyportal_token()
    if not token:
        return "Not authenticated. Configure SKYPORTAL_TOKEN or send Bearer token."

    # Build query parameters
    params = {
        "numPerPage": min(num_per_page, 500),  # Cap at 500
        "pageNumber": page_number,
        "savedStatus": saved_status,
    }

    if group_id is not None:
        params["groupIDs"] = str(group_id)
    if classifications:
        params["classifications"] = classifications
    if classifications_reject:
        params["classificationsReject"] = classifications_reject
    if min_redshift is not None:
        params["minRedshift"] = min_redshift
    if max_redshift is not None:
        params["maxRedshift"] = max_redshift
    if saved_after:
        params["savedAfter"] = saved_after
    if saved_before:
        params["savedBefore"] = saved_before
    if first_detected_after:
        params["firstDetectedAfter"] = first_detected_after
    if last_detected_before:
        params["lastDetectedBefore"] = last_detected_before

    # Parse annotation filters
    parsed_annotation_filters = []
    if annotation_filters:
        try:
            parsed_annotation_filters = json.loads(annotation_filters)
            if not isinstance(parsed_annotation_filters, list):
                return (
                    "Error: annotation_filters must be a JSON array of filter objects"
                )
            params["annotationFilterList"] = ",".join(
                json.dumps(f) for f in parsed_annotation_filters
            )
        except json.JSONDecodeError as e:
            return f"Error parsing annotation_filters JSON: {e}"

    # Query API
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{SKYPORTAL_URL}/api/candidates",
                headers={"Authorization": f"token {token}"},
                params=params,
            )
        resp.raise_for_status()
    except httpx.HTTPStatusError as e:
        return f"HTTP Error {e.response.status_code}: {e.response.text}"
    except Exception as e:
        return f"Error fetching candidates: {e}"

    data = resp.json().get("data", {})
    candidates = data.get("candidates", [])
    total_matches = data.get("totalMatches", 0)

    # Build filter config JSON for saving
    filter_config = _build_filter_config(
        group_id,
        saved_status,
        classifications,
        classifications_reject,
        min_redshift,
        max_redshift,
        parsed_annotation_filters,
        saved_after,
        saved_before,
        first_detected_after,
        last_detected_before,
    )

    if not candidates:
        filter_summary = _build_filter_summary(
            group_id,
            saved_status,
            classifications,
            classifications_reject,
            min_redshift,
            max_redshift,
            parsed_annotation_filters,
            saved_after,
            saved_before,
            first_detected_after,
            last_detected_before,
        )
        result = f"No candidates found matching criteria.\n{filter_summary}\n\n"
        result += "--- Filter Configuration (for saving/reuse) ---\n"
        result += filter_config
        return result

    # Build summary header
    lines = [f"# Found {total_matches} candidates (showing page {page_number})"]
    lines.append(
        _build_filter_summary(
            group_id,
            saved_status,
            classifications,
            classifications_reject,
            min_redshift,
            max_redshift,
            parsed_annotation_filters,
            saved_after,
            saved_before,
            first_detected_after,
            last_detected_before,
        )
    )
    lines.append("")

    # Determine annotation columns to include
    annotation_columns = []
    if parsed_annotation_filters:
        for filt in parsed_annotation_filters:
            origin = filt.get("origin", "")
            key = filt.get("key", "")
            col_name = f"{origin}_{key}"
            if col_name not in annotation_columns:
                annotation_columns.append(col_name)

    # CSV header
    header = "obj_id,ra,dec,redshift,latest_mag,latest_filter,saved_at,classifications"
    if annotation_columns:
        header += "," + ",".join(annotation_columns)
    lines.append(header)

    # Format each candidate
    for cand in candidates:
        obj_id = cand.get("id", "")
        ra = cand.get("ra", "")
        dec = cand.get("dec", "")
        redshift = cand.get("redshift", "")

        # Get latest photometry
        latest_mag = ""
        latest_filter = ""
        photometry = cand.get("photometry", [])
        if photometry:
            sorted_phot = sorted(
                photometry, key=lambda p: p.get("mjd", 0), reverse=True
            )
            if sorted_phot:
                latest = sorted_phot[0]
                latest_mag = latest.get("mag", "")
                latest_filter = latest.get("filter", "")

        # Get saved date
        saved_at = cand.get("saved_at", "")
        if saved_at and "T" in saved_at:
            saved_at = saved_at.split("T")[0]

        # Get classifications
        class_list = cand.get("classifications", [])
        if class_list:
            class_names = [c.get("classification", "") for c in class_list]
            classifications_str = ";".join(class_names)
        else:
            classifications_str = ""

        # Get annotation values
        annotation_values = {}
        annotations = cand.get("annotations", [])
        for annot in annotations:
            origin = annot.get("origin", "")
            annot_data = annot.get("data", {})
            for key, value in annot_data.items():
                col_name = f"{origin}_{key}"
                annotation_values[col_name] = value

        # Format numeric values
        if ra:
            ra = f"{float(ra):.6f}"
        if dec:
            dec = f"{float(dec):+.6f}"
        if redshift:
            redshift = f"{float(redshift):.4f}"
        if latest_mag:
            latest_mag = f"{float(latest_mag):.2f}"

        # Build row
        row = f"{obj_id},{ra},{dec},{redshift},{latest_mag},{latest_filter},{saved_at},{classifications_str}"
        for col_name in annotation_columns:
            value = annotation_values.get(col_name, "")
            if value and isinstance(value, int | float):
                value = f"{float(value):.3f}"
            row += f",{value}"
        lines.append(row)

    # Add filter config at the end
    lines.append("")
    lines.append("--- Filter Configuration (save this for reuse) ---")
    lines.append(filter_config)

    return "\n".join(lines)


def _build_filter_config(
    group_id,
    saved_status,
    classifications,
    classifications_reject,
    min_redshift,
    max_redshift,
    annotation_filters,
    saved_after,
    saved_before,
    first_detected_after,
    last_detected_before,
) -> str:
    """Build JSON configuration for the filter (for saving/reuse)."""
    config = {}
    if group_id is not None:
        config["group_id"] = group_id
    if saved_status != "all":
        config["saved_status"] = saved_status
    if classifications:
        config["classifications"] = classifications
    if classifications_reject:
        config["classifications_reject"] = classifications_reject
    if min_redshift is not None:
        config["min_redshift"] = min_redshift
    if max_redshift is not None:
        config["max_redshift"] = max_redshift
    if annotation_filters:
        config["annotation_filters"] = annotation_filters
    if saved_after:
        config["saved_after"] = saved_after
    if saved_before:
        config["saved_before"] = saved_before
    if first_detected_after:
        config["first_detected_after"] = first_detected_after
    if last_detected_before:
        config["last_detected_before"] = last_detected_before

    return json.dumps(config, indent=2)


def _build_filter_summary(
    group_id,
    saved_status,
    classifications,
    classifications_reject,
    min_redshift,
    max_redshift,
    annotation_filters,
    saved_after,
    saved_before,
    first_detected_after,
    last_detected_before,
) -> str:
    """Build human-readable summary of filter criteria."""
    criteria = []
    if group_id:
        criteria.append(f"group_id={group_id}")
    if saved_status != "all":
        criteria.append(f"saved_status={saved_status}")
    if classifications:
        criteria.append(f"classifications={classifications}")
    if classifications_reject:
        criteria.append(f"exclude={classifications_reject}")
    if min_redshift is not None:
        criteria.append(f"z>={min_redshift}")
    if max_redshift is not None:
        criteria.append(f"z<={max_redshift}")
    if annotation_filters:
        for filt in annotation_filters:
            origin = filt.get("origin", "")
            key = filt.get("key", "")
            if "min" in filt and "max" in filt:
                criteria.append(f"{origin}.{key}=[{filt['min']},{filt['max']}]")
            elif "min" in filt:
                criteria.append(f"{origin}.{key}>={filt['min']}")
            elif "max" in filt:
                criteria.append(f"{origin}.{key}<={filt['max']}")
            elif "value" in filt:
                criteria.append(f"{origin}.{key}={filt['value']}")
    if saved_after:
        criteria.append(f"saved_after={saved_after}")
    if saved_before:
        criteria.append(f"saved_before={saved_before}")
    if first_detected_after:
        criteria.append(f"first_detected_after={first_detected_after}")
    if last_detected_before:
        criteria.append(f"last_detected_before={last_detected_before}")

    if criteria:
        return "# Filters: " + ", ".join(criteria)
    return "# Filters: none (all candidates)"


@mcp.tool()
def generate_watchlist_filter(
    targets: str,
    max_distance_arcsec: float = 2.0,
    filter_name: str = "Watchlist",
) -> str:
    """Generate MongoDB filter JSON for a watchlist to monitor specific coordinates.

    Watchlists are alert-time filters that flag new detections near specified
    sky positions. They run on the Kowalski backend as part of Fritz's alert
    stream processing. This tool generates the MongoDB aggregation pipeline JSON
    that you can copy-paste into Fritz's filter creation UI.

    IMPORTANT - This is an ALERT-TIME filter:
    - Cannot be created directly via API (requires Fritz UI)
    - Runs automatically on every incoming alert from the telescope
    - Different from query-time filtering (filter_candidates tool)

    IMPORTANT - After Generation:
    1. Copy the generated JSON
    2. Go to Fritz UI → Filters page
    3. Create new filter and paste the JSON
    4. Set the filter's group and stream
    5. Save to activate monitoring

    Args:
        targets: JSON-encoded list of target objects. Each target must have:
            - "name": Target identifier (e.g., "M31", "NGC1234")
            - "ra": Right ascension in decimal degrees (J2000)
            - "dec": Declination in decimal degrees (J2000)

            Example:
            '[{"name":"M31","ra":10.6847,"dec":41.2687},{"name":"Crab","ra":83.6333,"dec":22.0145}]'

        max_distance_arcsec: Maximum angular separation in arcseconds for a match.
            Alerts within this distance from any target will be flagged.
            Default: 2.0 arcsec (typical for monitoring known sources)

        filter_name: Name for this watchlist filter (for documentation)

    Returns:
        MongoDB aggregation pipeline JSON ready to paste into Fritz filter UI.
        Includes:
        - Instructions for use
        - Complete pipeline with spherical distance calculation
        - Annotations with nearest target name and distance
        - Human-readable summary of watched positions
    """
    # Parse targets
    try:
        targets_list = json.loads(targets)
        if not isinstance(targets_list, list):
            return "Error: targets must be a JSON array of target objects"
        if not targets_list:
            return "Error: targets list cannot be empty"

        # Validate each target
        for i, target in enumerate(targets_list):
            if not isinstance(target, dict):
                return f"Error: target {i} must be an object with name, ra, dec"
            if "name" not in target or "ra" not in target or "dec" not in target:
                return f"Error: target {i} missing required fields (name, ra, dec)"
            # Validate coordinates
            try:
                ra = float(target["ra"])
                dec = float(target["dec"])
                if not (0 <= ra < 360):
                    return f"Error: target {i} RA must be in range [0, 360)"
                if not (-90 <= dec <= 90):
                    return f"Error: target {i} Dec must be in range [-90, 90]"
            except (ValueError, TypeError):
                return f"Error: target {i} ra/dec must be numeric"

    except json.JSONDecodeError as e:
        return f"Error parsing targets JSON: {e}"

    # Build the MongoDB aggregation pipeline
    # This implements spherical distance calculation and filtering
    pipeline = [
        {
            "$addFields": {
                "watchlist_distances": {
                    "$map": {
                        "input": targets_list,
                        "as": "target",
                        "in": {
                            "name": "$$target.name",
                            "distance_arcsec": {
                                "$multiply": [
                                    {
                                        "$atan2": [
                                            {
                                                "$sqrt": {
                                                    "$add": [
                                                        {
                                                            "$pow": [
                                                                {
                                                                    "$subtract": [
                                                                        {
                                                                            "$multiply": [
                                                                                {
                                                                                    "$cos": {
                                                                                        "$degreesToRadians": "$candidate.dec"
                                                                                    }
                                                                                },
                                                                                {
                                                                                    "$sin": {
                                                                                        "$degreesToRadians": {
                                                                                            "$subtract": [
                                                                                                "$candidate.ra",
                                                                                                "$$target.ra",
                                                                                            ]
                                                                                        }
                                                                                    }
                                                                                },
                                                                            ]
                                                                        },
                                                                        0,
                                                                    ]
                                                                },
                                                                2,
                                                            ]
                                                        },
                                                        {
                                                            "$pow": [
                                                                {
                                                                    "$subtract": [
                                                                        {
                                                                            "$subtract": [
                                                                                {
                                                                                    "$multiply": [
                                                                                        {
                                                                                            "$cos": {
                                                                                                "$degreesToRadians": "$$target.dec"
                                                                                            }
                                                                                        },
                                                                                        {
                                                                                            "$sin": {
                                                                                                "$degreesToRadians": "$candidate.dec"
                                                                                            }
                                                                                        },
                                                                                    ]
                                                                                },
                                                                                {
                                                                                    "$multiply": [
                                                                                        {
                                                                                            "$sin": {
                                                                                                "$degreesToRadians": "$$target.dec"
                                                                                            }
                                                                                        },
                                                                                        {
                                                                                            "$cos": {
                                                                                                "$degreesToRadians": "$candidate.dec"
                                                                                            }
                                                                                        },
                                                                                        {
                                                                                            "$cos": {
                                                                                                "$degreesToRadians": {
                                                                                                    "$subtract": [
                                                                                                        "$candidate.ra",
                                                                                                        "$$target.ra",
                                                                                                    ]
                                                                                                }
                                                                                            }
                                                                                        },
                                                                                    ]
                                                                                },
                                                                            ]
                                                                        },
                                                                        0,
                                                                    ]
                                                                },
                                                                2,
                                                            ]
                                                        },
                                                    ]
                                                }
                                            },
                                            {
                                                "$add": [
                                                    {
                                                        "$multiply": [
                                                            {
                                                                "$sin": {
                                                                    "$degreesToRadians": "$$target.dec"
                                                                }
                                                            },
                                                            {
                                                                "$sin": {
                                                                    "$degreesToRadians": "$candidate.dec"
                                                                }
                                                            },
                                                        ]
                                                    },
                                                    {
                                                        "$multiply": [
                                                            {
                                                                "$cos": {
                                                                    "$degreesToRadians": "$$target.dec"
                                                                }
                                                            },
                                                            {
                                                                "$cos": {
                                                                    "$degreesToRadians": "$candidate.dec"
                                                                }
                                                            },
                                                            {
                                                                "$cos": {
                                                                    "$degreesToRadians": {
                                                                        "$subtract": [
                                                                            "$candidate.ra",
                                                                            "$$target.ra",
                                                                        ]
                                                                    }
                                                                }
                                                            },
                                                        ]
                                                    },
                                                ]
                                            },
                                        ]
                                    },
                                    206264.80624709636,  # Convert radians to arcseconds
                                ]
                            },
                        },
                    }
                }
            }
        },
        {
            "$addFields": {
                "watchlist_matches": {
                    "$filter": {
                        "input": "$watchlist_distances",
                        "as": "distance_obj",
                        "cond": {
                            "$lte": [
                                "$$distance_obj.distance_arcsec",
                                max_distance_arcsec,
                            ]
                        },
                    }
                }
            }
        },
        {"$match": {"watchlist_matches": {"$ne": []}}},
        {
            "$project": {
                "_id": 0,
                "candid": 1,
                "objectId": 1,
                "watchlist_matches": 1,
                "closest_watchlist_target": {
                    "$arrayElemAt": ["$watchlist_matches.name", 0]
                },
                "closest_watchlist_distance_arcsec": {
                    "$arrayElemAt": ["$watchlist_matches.distance_arcsec", 0]
                },
            }
        },
    ]

    # Format output with instructions
    output_lines = [
        f"# Watchlist Filter: {filter_name}",
        f"# Monitoring {len(targets_list)} target(s) within {max_distance_arcsec} arcsec",
        "",
        "## Targets:",
    ]

    for target in targets_list:
        output_lines.append(
            f"#   - {target['name']}: RA={target['ra']:.6f}°, Dec={target['dec']:+.6f}°"
        )

    output_lines.extend(
        [
            "",
            "## Instructions:",
            "# 1. Copy the JSON pipeline below",
            "# 2. Go to Fritz UI → Filters page → Create Filter",
            "# 3. Paste into the 'Pipeline' field",
            "# 4. Set Group and Stream for this filter",
            "# 5. Save to activate monitoring",
            "#",
            "# When alerts match, they'll be annotated with:",
            "#   - closest_watchlist_target: name of nearest target",
            "#   - closest_watchlist_distance_arcsec: angular separation",
            "#   - watchlist_matches: list of all matching targets",
            "",
            "## MongoDB Pipeline JSON:",
            "",
            json.dumps(pipeline, indent=2),
        ]
    )

    return "\n".join(output_lines)
