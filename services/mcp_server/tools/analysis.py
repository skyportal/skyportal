# pyright: reportMissingTypeStubs=false
"""Light curve and color analysis tools for transients."""

import httpx
import numpy as np

from ..server import SKYPORTAL_URL, get_skyportal_token, mcp
from .source_products import resolve_source_id


@mcp.tool()
async def analyze_light_curve(
    source_name: str,
    filter_names: str = "ztfg,ztfr",
    baseline_threshold: float = 0.3,
    output_format: str = "notebook",
) -> str:
    """Analyze light curve evolution for multiple photometric bands.

    Calculates key temporal properties of a transient's light curve including
    rise time, fade time, total duration, and pre-peak variability (flares)
    for each requested photometric band.

    Handles incomplete light curves:
    - Still rising: Reports time from first detection to current
    - Still fading: Reports time from peak to current
    - Returned to baseline: Reports complete rise + fade times

    Generates CSV data file + Jupyter notebook with interactive Plotly plots
    showing all bands overlaid, plus editable analysis code cells.

    Args:
        source_name: Source identifier - SkyPortal obj_id, ZTF name, or TNS name
        filter_names: Comma-separated photometric filters (default: "ztfg,ztfr")
                     Examples: "ztfg,ztfr", "ztfg,ztfr,ztfi", "sdssr"
        baseline_threshold: Magnitude difference from peak to consider "baseline"
                          (default: 0.3 mag, i.e., source must fade by >0.3 mag
                          from peak to be considered at baseline)
        output_format: Output format - "notebook" (default) generates Jupyter notebook + CSV,
                      "text" returns summary in chat

    Returns:
        - If output_format="notebook": Creates directory with CSV data file (all bands)
          and Jupyter notebook with interactive Plotly plots and editable analysis code
        - If output_format="text": Formatted text summary with rise/fade times,
          duration, rates, and variability metrics for all bands
    """
    token = get_skyportal_token()
    if not token:
        return "Not authenticated. Configure SKYPORTAL_TOKEN or send Bearer token."

    # Resolve source name
    obj_id = await resolve_source_id(source_name)
    if not obj_id:
        return f"Error: Could not resolve '{source_name}' to a SkyPortal source."

    # Parse filter list
    filters = [f.strip() for f in filter_names.split(",")]

    # Fetch photometry once for all filters
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{SKYPORTAL_URL}/api/sources/{obj_id}/photometry",
                headers={"Authorization": f"token {token}"},
                params={"format": "mag", "magsys": "ab"},
            )
        resp.raise_for_status()
        all_data = resp.json().get("data", [])
    except Exception as e:
        return f"Error fetching photometry: {e}"

    if not all_data:
        return f"No photometry found for {obj_id}"

    # Process each filter and calculate metrics
    filter_data = {}
    for filter_name in filters:
        phot = [
            p
            for p in all_data
            if p.get("filter") == filter_name
            and p.get("mag") is not None
            and p.get("magerr") is not None
        ]

        if len(phot) < 2:
            continue  # Skip filters with insufficient data

        phot.sort(key=lambda p: p["mjd"])

        mjds = np.array([p["mjd"] for p in phot])
        mags = np.array([p["mag"] for p in phot])
        magerrs = np.array([p["magerr"] for p in phot])

        # Find peak (minimum magnitude = brightest)
        peak_idx = np.argmin(mags)
        peak_mjd = mjds[peak_idx]
        peak_mag = mags[peak_idx]
        peak_magerr = magerrs[peak_idx]

        first_mjd = mjds[0]
        first_mag = mags[0]
        last_mjd = mjds[-1]
        last_mag = mags[-1]

        rise_time = peak_mjd - first_mjd
        rise_mag = first_mag - peak_mag

        still_rising = peak_idx == len(mjds) - 1

        if still_rising:
            fade_time = None
            fade_mag = None
            fade_rate = None
            status = "Still rising"
            duration = None
        else:
            post_peak_mags = mags[peak_idx:]
            faded = post_peak_mags - peak_mag
            baseline_reached = np.any(faded > baseline_threshold)

            if baseline_reached:
                baseline_idx = peak_idx + np.where(faded > baseline_threshold)[0][0]
                fade_time = mjds[baseline_idx] - peak_mjd
                fade_mag = (
                    post_peak_mags[np.where(faded > baseline_threshold)[0][0]]
                    - peak_mag
                )
                status = "Complete light curve"
                duration = rise_time + fade_time
            else:
                fade_time = last_mjd - peak_mjd
                fade_mag = last_mag - peak_mag
                status = "Still fading"
                duration = None

            fade_rate = fade_mag / fade_time if fade_time and fade_time > 0 else None

        rise_rate = rise_mag / rise_time if rise_time > 0 else None

        # Pre-peak variability
        if peak_idx > 1:
            pre_peak_mags = mags[:peak_idx]
            mag_diffs = np.diff(pre_peak_mags)
            brightening_events = int(np.sum(mag_diffs < -0.1))
            variability_rms = float(np.std(pre_peak_mags))
        else:
            brightening_events = 0
            variability_rms = 0.0

        filter_data[filter_name] = {
            "mjds": mjds,
            "mags": mags,
            "magerrs": magerrs,
            "peak_mjd": peak_mjd,
            "peak_mag": peak_mag,
            "peak_magerr": peak_magerr,
            "first_mjd": first_mjd,
            "last_mjd": last_mjd,
            "rise_time": rise_time,
            "rise_mag": rise_mag,
            "rise_rate": rise_rate,
            "fade_time": fade_time,
            "fade_mag": fade_mag,
            "fade_rate": fade_rate,
            "duration": duration,
            "status": status,
            "still_rising": still_rising,
            "brightening_events": brightening_events,
            "variability_rms": variability_rms,
            "n_points": len(mjds),
        }

    if not filter_data:
        return f"No sufficient photometry for any requested filters: {filter_names}"

    # Generate output
    if output_format == "notebook":
        return _generate_lightcurve_notebook(obj_id, filter_data, baseline_threshold)
    else:
        return _generate_lightcurve_text(obj_id, filter_data)


def _generate_lightcurve_notebook(obj_id, filter_data, baseline_threshold):
    """Generate CSV + Jupyter notebook for multi-band light curve analysis."""
    import csv
    import json
    from pathlib import Path

    # SkyPortal filter colors
    filter_colors = {
        "ztfg": "#28a745",
        "ztfr": "#dc3545",
        "ztfi": "#8b0000",
        "sdssr": "#dc3545",
    }

    # Create output directory
    output_dir = Path(f"{obj_id}_lightcurve_analysis")
    output_dir.mkdir(exist_ok=True)

    # === Write CSV with all bands ===
    csv_path = output_dir / f"{obj_id}_lightcurve_data.csv"
    with open(csv_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["filter", "mjd", "mag", "magerr"])
        for filter_name, data in filter_data.items():
            for i in range(len(data["mjds"])):
                writer.writerow(
                    [
                        filter_name,
                        data["mjds"][i],
                        data["mags"][i],
                        data["magerrs"][i],
                    ]
                )

    # === Generate Jupyter Notebook ===
    notebook_path = output_dir / f"{obj_id}_lightcurve_analysis.ipynb"
    filter_list_str = ", ".join(filter_data.keys())

    # Build Plotly trace code for each filter
    plot_traces = []
    for filter_name in filter_data:
        color = filter_colors.get(filter_name, "#1f77b4")
        plot_traces.append(
            f"# {filter_name} photometry\n"
            f"df_filt = df[df['filter'] == '{filter_name}']\n"
            f"fig.add_trace(\n"
            f"    go.Scatter(\n"
            f"        x=df_filt['mjd'],\n"
            f"        y=df_filt['mag'],\n"
            f"        error_y=dict(type='data', array=df_filt['magerr'], visible=True, thickness=1.5),\n"
            f"        mode='markers',\n"
            f"        marker=dict(\n"
            f"            size=6,\n"
            f"            color=hex_to_rgba('{color}', 0.6),\n"
            f"            line=dict(color='{color}', width=1.5)\n"
            f"        ),\n"
            f"        name='{filter_name}',\n"
            f"        hovertemplate='MJD: %{{x:.2f}}<br>Mag: %{{y:.3f}}<br>Error: %{{error_y.array:.3f}}<extra></extra>'\n"
            f"    )\n"
            f")\n"
        )

    notebook = {
        "cells": [
            {
                "cell_type": "markdown",
                "metadata": {},
                "source": [
                    f"# Light Curve Analysis: {obj_id}\n\n",
                    f"**Filters**: {filter_list_str}\n\n",
                    "This notebook contains multi-band light curve analysis with editable code cells.\n",
                ],
            },
            {
                "cell_type": "code",
                "execution_count": None,
                "metadata": {},
                "source": [
                    "# Import dependencies\n",
                    "import pandas as pd\n",
                    "import numpy as np\n",
                    "import plotly.graph_objects as go\n",
                    "from plotly.offline import init_notebook_mode, iplot\n\n",
                    "# Initialize Plotly offline mode\n",
                    "init_notebook_mode(connected=True)\n",
                    "print('✓ Plotly offline mode initialized')\n",
                ],
            },
            {
                "cell_type": "code",
                "execution_count": None,
                "metadata": {},
                "source": [
                    f"# Load multi-band light curve data\n",
                    f"df = pd.read_csv('{obj_id}_lightcurve_data.csv')\n",
                    f"print(f'Loaded {{len(df)}} total photometry points across {{df[\"filter\"].nunique()}} bands')\n",
                    "print()\n",
                    "print(df.groupby('filter').size().to_string())\n",
                ],
            },
            {
                "cell_type": "markdown",
                "metadata": {},
                "source": [
                    "## Analysis Code\n\n",
                    "The cells below contain the analysis code used to calculate rise/fade times, peak properties, etc.\n",
                    "Edit these cells to customize the analysis (e.g., change baseline threshold, add new metrics).\n",
                ],
            },
            {
                "cell_type": "code",
                "execution_count": None,
                "metadata": {},
                "source": [
                    "# Analysis parameters (edit as needed)\n",
                    f"baseline_threshold = {baseline_threshold}  # Magnitude difference from peak to consider baseline\n",
                ],
            },
            {
                "cell_type": "code",
                "execution_count": None,
                "metadata": {},
                "source": [
                    "# Function to analyze a single filter\n",
                    "def analyze_filter(df, filter_name, baseline_threshold=0.3):\n",
                    '    """Calculate rise/fade metrics for one photometric band."""\n',
                    "    data = df[df['filter'] == filter_name].sort_values('mjd')\n",
                    "    if len(data) < 2:\n",
                    "        return None\n",
                    "    \n",
                    "    mjds = data['mjd'].values\n",
                    "    mags = data['mag'].values\n",
                    "    magerrs = data['magerr'].values\n",
                    "    \n",
                    "    # Find peak (minimum magnitude = brightest)\n",
                    "    peak_idx = np.argmin(mags)\n",
                    "    peak_mjd = mjds[peak_idx]\n",
                    "    peak_mag = mags[peak_idx]\n",
                    "    \n",
                    "    # Rise time: first detection to peak\n",
                    "    first_mjd = mjds[0]\n",
                    "    rise_time = peak_mjd - first_mjd\n",
                    "    rise_mag = mags[0] - peak_mag\n",
                    "    rise_rate = rise_mag / rise_time if rise_time > 0 else None\n",
                    "    \n",
                    "    # Check if still rising (peak is last point)\n",
                    "    still_rising = peak_idx == len(mjds) - 1\n",
                    "    \n",
                    "    # Fade analysis\n",
                    "    if still_rising:\n",
                    "        status = 'Still rising'\n",
                    "        fade_time = None\n",
                    "        fade_rate = None\n",
                    "        duration = None\n",
                    "    else:\n",
                    "        post_peak_mags = mags[peak_idx:]\n",
                    "        faded = post_peak_mags - peak_mag\n",
                    "        baseline_reached = np.any(faded > baseline_threshold)\n",
                    "        \n",
                    "        if baseline_reached:\n",
                    "            baseline_idx = peak_idx + np.where(faded > baseline_threshold)[0][0]\n",
                    "            fade_time = mjds[baseline_idx] - peak_mjd\n",
                    "            status = 'Complete'\n",
                    "            duration = rise_time + fade_time\n",
                    "        else:\n",
                    "            fade_time = mjds[-1] - peak_mjd\n",
                    "            status = 'Still fading'\n",
                    "            duration = None\n",
                    "        \n",
                    "        fade_rate = (mags[-1] - peak_mag) / fade_time if fade_time and fade_time > 0 else None\n",
                    "    \n",
                    "    # Pre-peak variability\n",
                    "    if peak_idx > 1:\n",
                    "        pre_peak_mags = mags[:peak_idx]\n",
                    "        variability_rms = np.std(pre_peak_mags)\n",
                    "        brightening_events = int(np.sum(np.diff(pre_peak_mags) < -0.1))\n",
                    "    else:\n",
                    "        variability_rms = 0.0\n",
                    "        brightening_events = 0\n",
                    "    \n",
                    "    return {\n",
                    "        'filter': filter_name,\n",
                    "        'n_points': len(mjds),\n",
                    "        'status': status,\n",
                    "        'peak_mag': f'{peak_mag:.2f}',\n",
                    "        'peak_mjd': f'{peak_mjd:.2f}',\n",
                    "        'rise_time': f'{rise_time:.1f}',\n",
                    "        'rise_rate': f'{rise_rate:.3f}' if rise_rate else 'N/A',\n",
                    "        'fade_time': f'{fade_time:.1f}' if fade_time else 'N/A',\n",
                    "        'fade_rate': f'{fade_rate:.3f}' if fade_rate else 'N/A',\n",
                    "        'duration': f'{duration:.1f}' if duration else 'N/A',\n",
                    "        'rms': f'{variability_rms:.3f}',\n",
                    "        'flares': brightening_events,\n",
                    "    }\n",
                ],
            },
            {
                "cell_type": "code",
                "execution_count": None,
                "metadata": {},
                "source": [
                    "# Calculate metrics for all filters\n",
                    "results = []\n",
                    "for filt in df['filter'].unique():\n",
                    "    result = analyze_filter(df, filt, baseline_threshold)\n",
                    "    if result:\n",
                    "        results.append(result)\n\n",
                    "# Display results table\n",
                    "results_df = pd.DataFrame(results)\n",
                    "print('=' * 80)\n",
                    f"print('LIGHT CURVE ANALYSIS: {obj_id}')\n",
                    "print('=' * 80)\n",
                    "print()\n",
                    "print(results_df.to_string(index=False))\n",
                    "print()\n",
                    "print('=' * 80)\n",
                ],
            },
            {
                "cell_type": "markdown",
                "metadata": {},
                "source": [
                    "## Multi-band Light Curve Plot\n",
                ],
            },
            {
                "cell_type": "code",
                "execution_count": None,
                "metadata": {},
                "source": [
                    "# Create multi-band interactive plot\n",
                    "fig = go.Figure()\n\n",
                    "# Helper function to convert hex to rgba\n",
                    "def hex_to_rgba(hex_color, alpha):\n",
                    "    h = hex_color.lstrip('#')\n",
                    "    rgb = tuple(int(h[i:i+2], 16) for i in (0, 2, 4))\n",
                    "    return f'rgba({rgb[0]},{rgb[1]},{rgb[2]},{alpha})'\n\n",
                    "\n".join(plot_traces) + "\n",
                    "# Update layout\n",
                    "fig.update_xaxes(title_text='MJD')\n",
                    "fig.update_yaxes(title_text='AB Magnitude', autorange='reversed')\n",
                    "fig.update_layout(\n",
                    f"    title='{obj_id} Multi-band Light Curve',\n",
                    "    height=600,\n",
                    "    showlegend=True,\n",
                    "    hovermode='closest',\n",
                    "    template='plotly_white'\n",
                    ")\n\n",
                    "# Display interactive figure\n",
                    "iplot(fig)\n",
                ],
            },
        ],
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            },
            "language_info": {"name": "python", "version": "3.9.0"},
        },
        "nbformat": 4,
        "nbformat_minor": 4,
    }

    with open(notebook_path, "w") as f:
        json.dump(notebook, f, indent=2)

    # Build summary
    summary_lines = [
        "Light curve analysis complete!",
        "",
        f"Output files saved to: {output_dir}/",
        "",
        "Files created:",
        f"- {csv_path.name} - Multi-band light curve data",
        f"- {notebook_path.name} - Interactive Jupyter notebook with analysis code",
        "",
        "Summary:",
        f"- Source: {obj_id}",
        f"- Filters: {', '.join(filter_data.keys())}",
        "",
        "Per-filter metrics:",
    ]

    for filter_name, data in filter_data.items():
        summary_lines.append(f"  {filter_name}:")
        summary_lines.append(
            f"    Points: {data['n_points']}, Status: {data['status']}"
        )
        summary_lines.append(
            f"    Peak: {data['peak_mag']:.2f} mag at MJD {data['peak_mjd']:.2f}"
        )
        summary_lines.append(f"    Rise: {data['rise_time']:.1f} days")
        if data["fade_time"]:
            summary_lines.append(f"    Fade: {data['fade_time']:.1f} days")
        if data["duration"]:
            summary_lines.append(f"    Duration: {data['duration']:.1f} days")

    summary_lines.append("")
    summary_lines.append(
        "Open the notebook to view interactive plots and customize the analysis!"
    )

    return "\n".join(summary_lines)


def _generate_lightcurve_text(obj_id, filter_data):
    """Generate text summary for multi-band light curve analysis."""
    lines = ["=" * 80]
    lines.append(f"LIGHT CURVE ANALYSIS: {obj_id}")
    lines.append(f"Filters: {', '.join(filter_data.keys())}")
    lines.append("=" * 80)
    lines.append("")

    for filter_name, data in filter_data.items():
        lines.append(f"## {filter_name.upper()} BAND")
        lines.append("")
        lines.append("OVERVIEW")
        lines.append(f"  Status:        {data['status']}")
        lines.append(f"  Total points:  {data['n_points']}")
        lines.append(
            f"  Time span:     {data['first_mjd']:.1f} - {data['last_mjd']:.1f} MJD "
            f"({data['last_mjd'] - data['first_mjd']:.1f} days)"
        )
        lines.append("")

        lines.append("PEAK PROPERTIES")
        lines.append(
            f"  Peak mag:      {data['peak_mag']:.2f} ± {data['peak_magerr']:.2f} mag"
        )
        lines.append(f"  Peak time:     MJD {data['peak_mjd']:.2f}")
        lines.append("")

        lines.append("RISE PROPERTIES")
        lines.append(f"  Rise time:     {data['rise_time']:.1f} days")
        lines.append(f"  Rise mag:      {data['rise_mag']:.2f} mag")
        if data["rise_rate"]:
            lines.append(f"  Rise rate:     {data['rise_rate']:.3f} mag/day")
        if data["still_rising"]:
            lines.append("  Note:          Still rising")
        lines.append("")

        lines.append("FADE PROPERTIES")
        if data["fade_time"]:
            lines.append(f"  Fade time:     {data['fade_time']:.1f} days")
            lines.append(f"  Fade mag:      {data['fade_mag']:.2f} mag")
            if data["fade_rate"]:
                lines.append(f"  Fade rate:     {data['fade_rate']:.3f} mag/day")
        else:
            lines.append("  Fade time:     N/A (still rising)")

        if data["duration"]:
            lines.append(f"  Total duration: {data['duration']:.1f} days")
        lines.append("")

        lines.append("VARIABILITY")
        lines.append(f"  Pre-peak RMS:  {data['variability_rms']:.3f} mag")
        if data["brightening_events"] > 0:
            lines.append(f"  Early flares:  {data['brightening_events']} event(s)")
        else:
            lines.append("  Early flares:  None detected")
        lines.append("")
        lines.append("-" * 80)
        lines.append("")

    lines.append("=" * 80)
    return "\n".join(lines)


@mcp.tool()
async def analyze_color_evolution(
    source_name: str,
    band1: str = "ztfg",
    band2: str = "ztfr",
    max_time_gap: float = 0.5,
    max_data_gap: float = 3.0,
    output_format: str = "notebook",
) -> str:
    """Analyze color evolution and color at peak brightness.

    Calculates color curves (band1 - band2) using BOTH methods:
    - **Matched**: Day-to-day colors (pairs close observations)
    - **Interpolated**: Rolling/continuous colors (interpolates for smooth curve)

    Generates CSV data file + Jupyter notebook with overlaid plots.

    Args:
        source_name: Source identifier - SkyPortal obj_id, ZTF name, or TNS name
        band1: First photometric filter (default: "ztfg")
        band2: Second photometric filter (default: "ztfr")
        max_time_gap: For matched method - maximum time difference (days) to
                     pair observations (default: 0.5 days)
        max_data_gap: For matched method - if gap between consecutive observations
                     in either band exceeds this, don't calculate colors across
                     the gap (default: 3.0 days). Prevents spurious colors during
                     observing gaps.
        output_format: Output format - "notebook" (default) generates Jupyter notebook + CSV,
                      "text" returns summary in chat

    Returns:
        - If output_format="notebook": Path to generated notebook and CSV files
        - If output_format="text": Formatted text summary with color measurements
    """
    token = get_skyportal_token()
    if not token:
        return "Not authenticated. Configure SKYPORTAL_TOKEN or send Bearer token."

    # Resolve source name
    obj_id = await resolve_source_id(source_name)
    if not obj_id:
        return f"Error: Could not resolve '{source_name}' to a SkyPortal source."

    # Fetch photometry
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{SKYPORTAL_URL}/api/sources/{obj_id}/photometry",
                headers={"Authorization": f"token {token}"},
                params={"format": "mag", "magsys": "ab"},
            )
        resp.raise_for_status()
        data = resp.json().get("data", [])
    except Exception as e:
        return f"Error fetching photometry: {e}"

    if not data:
        return f"No photometry found for {obj_id}"

    # Separate by filter
    phot1 = [
        p
        for p in data
        if p.get("filter") == band1
        and p.get("mag") is not None
        and p.get("magerr") is not None
    ]
    phot2 = [
        p
        for p in data
        if p.get("filter") == band2
        and p.get("mag") is not None
        and p.get("magerr") is not None
    ]

    if not phot1 or not phot2:
        return f"Insufficient photometry in {band1} and/or {band2} bands"

    # Sort by time
    phot1.sort(key=lambda p: p["mjd"])
    phot2.sort(key=lambda p: p["mjd"])

    # Extract arrays
    mjds1 = np.array([p["mjd"] for p in phot1])
    mags1 = np.array([p["mag"] for p in phot1])
    errs1 = np.array([p["magerr"] for p in phot1])

    mjds2 = np.array([p["mjd"] for p in phot2])
    mags2 = np.array([p["mag"] for p in phot2])
    errs2 = np.array([p["magerr"] for p in phot2])

    # === Calculate MATCHED colors ===
    matched_colors = []
    for i, p1 in enumerate(phot1):
        mjd1 = p1["mjd"]
        mag1 = p1["mag"]
        err1 = p1["magerr"]

        # Check if this observation is in a large gap
        if i > 0:
            prev_gap = mjd1 - phot1[i - 1]["mjd"]
        else:
            prev_gap = 0

        if i < len(phot1) - 1:
            next_gap = phot1[i + 1]["mjd"] - mjd1
        else:
            next_gap = 0

        in_large_gap = (prev_gap > max_data_gap) or (next_gap > max_data_gap)

        # Find closest observation in band2
        time_diffs = np.abs(mjds2 - mjd1)
        closest_idx = np.argmin(time_diffs)

        if time_diffs[closest_idx] <= max_time_gap and not in_large_gap:
            # Also check if band2 observation is in a large gap
            if closest_idx > 0:
                prev_gap2 = mjds2[closest_idx] - mjds2[closest_idx - 1]
            else:
                prev_gap2 = 0

            if closest_idx < len(mjds2) - 1:
                next_gap2 = mjds2[closest_idx + 1] - mjds2[closest_idx]
            else:
                next_gap2 = 0

            in_large_gap2 = (prev_gap2 > max_data_gap) or (next_gap2 > max_data_gap)

            if not in_large_gap2:
                mag2 = mags2[closest_idx]
                err2 = errs2[closest_idx]

                color = mag1 - mag2
                color_err = np.sqrt(err1**2 + err2**2)

                matched_colors.append(
                    {
                        "mjd": mjd1,
                        "color": color,
                        "color_err": color_err,
                        "mag1": mag1,
                        "mag2": mag2,
                    }
                )

    # === Calculate INTERPOLATED colors ===
    from scipy.interpolate import interp1d

    interpolated_colors = []
    try:
        interp_func = interp1d(
            mjds2, mags2, kind="linear", bounds_error=False, fill_value=np.nan
        )
        interp_err_func = interp1d(
            mjds2, errs2, kind="linear", bounds_error=False, fill_value=np.nan
        )

        for i, mjd1 in enumerate(mjds1):
            mag1 = mags1[i]
            err1 = errs1[i]

            # Interpolate band2
            mag2_interp = interp_func(mjd1)
            err2_interp = interp_err_func(mjd1)

            # Only use if interpolation is valid (within band2 time range)
            if not np.isnan(mag2_interp):
                color = mag1 - mag2_interp
                color_err = np.sqrt(err1**2 + err2_interp**2)

                interpolated_colors.append(
                    {
                        "mjd": mjd1,
                        "color": color,
                        "color_err": color_err,
                        "mag1": mag1,
                        "mag2": mag2_interp,
                    }
                )
    except Exception as e:
        return f"Error in interpolation: {e}"

    if len(matched_colors) < 2 and len(interpolated_colors) < 2:
        return f"Insufficient color measurements. Try adjusting max_time_gap parameter."

    # Find peak in each band
    peak_idx1 = np.argmin(mags1)
    peak_idx2 = np.argmin(mags2)
    peak_mjd1 = mjds1[peak_idx1]
    peak_mjd2 = mjds2[peak_idx2]
    peak_mag1 = mags1[peak_idx1]
    peak_mag2 = mags2[peak_idx2]

    # Use matched colors for statistics (more reliable)
    if len(matched_colors) >= 2:
        peak_mjd_avg = (peak_mjd1 + peak_mjd2) / 2
        color_mjds = np.array([c["mjd"] for c in matched_colors])
        peak_color_idx = np.argmin(np.abs(color_mjds - peak_mjd_avg))
        peak_color = matched_colors[peak_color_idx]

        color_vals = np.array([c["color"] for c in matched_colors])
        mean_color = np.mean(color_vals)
        color_range = np.ptp(color_vals)
        color_std = np.std(color_vals)

        if len(matched_colors) > 2:
            color_mjds_centered = color_mjds - color_mjds[0]
            slope, _ = np.polyfit(color_mjds_centered, color_vals, 1)
            trend = (
                "bluing" if slope < -0.01 else "reddening" if slope > 0.01 else "stable"
            )
        else:
            slope = 0
            trend = "insufficient data"
    else:
        peak_color = {"color": np.nan, "color_err": np.nan, "mjd": np.nan}
        mean_color = np.nan
        color_range = np.nan
        color_std = np.nan
        slope = 0
        trend = "insufficient matched data"

    # Generate output
    if output_format == "notebook":
        import csv
        import json
        from pathlib import Path

        # Create output directory
        output_dir = Path.cwd() / f"{obj_id}_color_analysis"
        output_dir.mkdir(exist_ok=True)

        # === Generate CSV file ===
        csv_path = output_dir / f"{obj_id}_color_data.csv"
        with open(csv_path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(
                [
                    "mjd",
                    f"mag_{band1}",
                    f"magerr_{band1}",
                    f"mag_{band2}",
                    f"magerr_{band2}",
                    "color_matched",
                    "color_matched_err",
                    "color_interpolated",
                    "color_interpolated_err",
                ]
            )

            # Build lookup dicts for colors
            matched_dict = {
                c["mjd"]: (c["color"], c["color_err"]) for c in matched_colors
            }
            interp_dict = {
                c["mjd"]: (c["color"], c["color_err"]) for c in interpolated_colors
            }

            # Write all band1 observations with corresponding colors
            for i in range(len(mjds1)):
                mjd = mjds1[i]
                matched_val, matched_err = matched_dict.get(mjd, (None, None))
                interp_val, interp_err = interp_dict.get(mjd, (None, None))

                writer.writerow(
                    [
                        mjd,
                        mags1[i],
                        errs1[i],
                        None,
                        None,
                        matched_val,
                        matched_err,
                        interp_val,
                        interp_err,
                    ]
                )

            # Write band2-only observations
            for i in range(len(mjds2)):
                mjd = mjds2[i]
                if mjd not in mjds1:
                    writer.writerow(
                        [mjd, None, None, mags2[i], errs2[i], None, None, None, None]
                    )

        # === Generate Jupyter Notebook ===
        notebook_path = output_dir / f"{obj_id}_color_analysis.ipynb"

        notebook = {
            "cells": [
                {
                    "cell_type": "markdown",
                    "metadata": {},
                    "source": [
                        f"# Color Evolution Analysis: {obj_id}\n\n",
                        f"**Color**: {band1} - {band2}\n\n",
                        f"This notebook shows both **matched** (day-to-day) and **interpolated** (rolling) color measurements overlaid.\n",
                    ],
                },
                {
                    "cell_type": "markdown",
                    "metadata": {},
                    "source": [
                        "## Dependencies\n\n",
                        "This notebook requires the following packages:\n",
                        "```bash\n",
                        "pip install pandas plotly nbformat\n",
                        "```\n",
                    ],
                },
                {
                    "cell_type": "code",
                    "execution_count": None,
                    "metadata": {},
                    "source": [
                        "# Import dependencies\n",
                        "import pandas as pd\n",
                        "import plotly.graph_objects as go\n",
                        "from plotly.subplots import make_subplots\n",
                        "from plotly.offline import init_notebook_mode, iplot\n\n",
                        "# Initialize Plotly offline mode for notebooks\n",
                        "init_notebook_mode(connected=True)\n",
                        "print('✓ Plotly offline mode initialized')\n",
                    ],
                },
                {
                    "cell_type": "code",
                    "execution_count": None,
                    "metadata": {},
                    "source": [
                        f"# Load data\n",
                        f"df = pd.read_csv('{obj_id}_color_data.csv')\n",
                        f"df_band1 = df[df['mag_{band1}'].notna()]\n",
                        f"df_band2 = df[df['mag_{band2}'].notna()]\n",
                        f"print(f'Loaded {{len(df)}} rows from {obj_id}_color_data.csv')\n",
                    ],
                },
                {
                    "cell_type": "code",
                    "execution_count": None,
                    "metadata": {},
                    "source": [
                        f"# Analysis results\n",
                        f"peak_mjd_{band1} = {peak_mjd1:.2f}\n",
                        f"peak_mag_{band1} = {peak_mag1:.2f}\n",
                        f"peak_mjd_{band2} = {peak_mjd2:.2f}\n",
                        f"peak_mag_{band2} = {peak_mag2:.2f}\n",
                        f"peak_color = {peak_color['color']:.3f}\n",
                        f"mean_color = {mean_color:.3f}\n",
                        f"trend = '{trend}'\n\n",
                        f"print(f'Peak in {band1}: {{peak_mag_{band1}:.2f}} mag at MJD {{peak_mjd_{band1}:.2f}}')\n",
                        f"print(f'Peak in {band2}: {{peak_mag_{band2}:.2f}} mag at MJD {{peak_mjd_{band2}:.2f}}')\n",
                        f"print(f'Color at peak: {{peak_color:.3f}} mag')\n",
                        f"print(f'Mean color: {{mean_color:.3f}} mag')\n",
                        f"print(f'Trend: {{trend}}')\n",
                    ],
                },
                {
                    "cell_type": "code",
                    "execution_count": None,
                    "metadata": {},
                    "source": [
                        f"# Create interactive overlay plot with Plotly\n",
                        f"fig = make_subplots(\n",
                        f"    rows=2, cols=1,\n",
                        f"    subplot_titles=('{obj_id}: {band1}-{band2} Multi-band Light Curves',\n",
                        f"                   'Color Evolution (Both Methods Overlaid)'),\n",
                        f"    vertical_spacing=0.12,\n",
                        f"    shared_xaxes=True\n",
                        f")\n\n",
                        f"# SkyPortal filter colors\n",
                        f"filter_colors = {{'ztfg': '#28a745', 'ztfr': '#dc3545', 'ztfi': '#8b0000', 'sdssr': '#dc3545'}}\n",
                        f"color1 = filter_colors.get('{band1}', '#1f77b4')\n",
                        f"color2 = filter_colors.get('{band2}', '#ff7f0e')\n\n",
                        f"# Helper function to convert hex to rgba\n",
                        f"def hex_to_rgba(hex_color, alpha):\n",
                        f"    h = hex_color.lstrip('#')\n",
                        f"    rgb = tuple(int(h[i:i+2], 16) for i in (0, 2, 4))\n",
                        f"    return f'rgba({{rgb[0]}},{{rgb[1]}},{{rgb[2]}},{{alpha}})'\n\n",
                        f"# Top panel: Light curves with error bars\n",
                        f"# {band1} photometry\n",
                        f"fig.add_trace(\n",
                        f"    go.Scatter(\n",
                        f"        x=df_band1['mjd'],\n",
                        f"        y=df_band1['mag_{band1}'],\n",
                        f"        error_y=dict(type='data', array=df_band1['magerr_{band1}'], visible=True, thickness=1.5),\n",
                        f"        mode='markers',\n",
                        f"        marker=dict(\n",
                        f"            size=6,\n",
                        f"            color=hex_to_rgba(color1, 0.6),\n",
                        f"            line=dict(color=color1, width=1.5)\n",
                        f"        ),\n",
                        f"        name='{band1}',\n",
                        f"        hovertemplate='MJD: %{{x:.2f}}<br>Mag: %{{y:.3f}}<br>Error: %{{error_y.array:.3f}}<extra></extra>'\n",
                        f"    ),\n",
                        f"    row=1, col=1\n",
                        f")\n\n",
                        f"# {band2} photometry\n",
                        f"fig.add_trace(\n",
                        f"    go.Scatter(\n",
                        f"        x=df_band2['mjd'],\n",
                        f"        y=df_band2['mag_{band2}'],\n",
                        f"        error_y=dict(type='data', array=df_band2['magerr_{band2}'], visible=True, thickness=1.5),\n",
                        f"        mode='markers',\n",
                        f"        marker=dict(\n",
                        f"            size=6,\n",
                        f"            color=hex_to_rgba(color2, 0.6),\n",
                        f"            line=dict(color=color2, width=1.5)\n",
                        f"        ),\n",
                        f"        name='{band2}',\n",
                        f"        hovertemplate='MJD: %{{x:.2f}}<br>Mag: %{{y:.3f}}<br>Error: %{{error_y.array:.3f}}<extra></extra>'\n",
                        f"    ),\n",
                        f"    row=1, col=1\n",
                        f")\n\n",
                        f"# Peak vertical lines\n",
                        f"fig.add_vline(x=peak_mjd_{band1}, line_dash='dash', line_color=color1, opacity=0.5,\n",
                        f"             annotation_text='Peak {band1}', annotation_position='top',\n",
                        f"             row=1, col=1)\n",
                        f"fig.add_vline(x=peak_mjd_{band2}, line_dash='dash', line_color=color2, opacity=0.5,\n",
                        f"             annotation_text='Peak {band2}', annotation_position='top',\n",
                        f"             row=1, col=1)\n\n",
                        f"# Bottom panel: Color evolution (matched in back, interpolated in front)\n",
                        f"df_matched = df[df['color_matched'].notna()]\n",
                        f"df_interp = df[df['color_interpolated'].notna()]\n\n",
                        f"# Matched (grey) - behind with lower opacity\n",
                        f"fig.add_trace(\n",
                        f"    go.Scatter(\n",
                        f"        x=df_matched['mjd'],\n",
                        f"        y=df_matched['color_matched'],\n",
                        f"        error_y=dict(type='data', array=df_matched['color_matched_err'], visible=True, thickness=1.5),\n",
                        f"        mode='markers',\n",
                        f"        marker=dict(\n",
                        f"            size=6,\n",
                        f"            color='rgba(128, 128, 128, 0.5)',\n",
                        f"            line=dict(color='rgba(128, 128, 128, 1.0)', width=1.5)\n",
                        f"        ),\n",
                        f"        name='Matched (day-to-day)',\n",
                        f"        hovertemplate='MJD: %{{x:.2f}}<br>Color: %{{y:.3f}}<br>Error: %{{error_y.array:.3f}}<extra></extra>'\n",
                        f"    ),\n",
                        f"    row=2, col=1\n",
                        f")\n\n",
                        f"# Interpolated (black) - in front\n",
                        f"fig.add_trace(\n",
                        f"    go.Scatter(\n",
                        f"        x=df_interp['mjd'],\n",
                        f"        y=df_interp['color_interpolated'],\n",
                        f"        error_y=dict(type='data', array=df_interp['color_interpolated_err'], visible=True, thickness=1.5),\n",
                        f"        mode='markers',\n",
                        f"        marker=dict(\n",
                        f"            size=6,\n",
                        f"            color='rgba(0, 0, 0, 0.6)',\n",
                        f"            line=dict(color='rgba(0, 0, 0, 1.0)', width=1.5)\n",
                        f"        ),\n",
                        f"        name='Interpolated (rolling)',\n",
                        f"        hovertemplate='MJD: %{{x:.2f}}<br>Color: %{{y:.3f}}<br>Error: %{{error_y.array:.3f}}<extra></extra>'\n",
                        f"    ),\n",
                        f"    row=2, col=1\n",
                        f")\n\n",
                        f"# Color at peak line\n",
                        f"fig.add_hline(y=peak_color, line_dash='dash', line_color='red', line_width=2, opacity=0.4,\n",
                        f"             annotation_text=f'Color at peak: {{peak_color:.3f}} mag',\n",
                        f"             annotation_position='right',\n",
                        f"             row=2, col=1)\n\n",
                        f"# Update layout\n",
                        f"fig.update_xaxes(title_text='MJD', row=2, col=1)\n",
                        f"fig.update_yaxes(title_text='AB Magnitude', autorange='reversed', row=1, col=1)\n",
                        f"fig.update_yaxes(title_text='{band1} - {band2} (mag)', row=2, col=1)\n",
                        f"fig.update_layout(\n",
                        f"    height=800,\n",
                        f"    showlegend=True,\n",
                        f"    hovermode='closest',\n",
                        f"    template='plotly_white'\n",
                        f")\n\n",
                        f"# Display the interactive figure\n",
                        f"iplot(fig)\n",
                    ],
                },
            ],
            "metadata": {
                "kernelspec": {
                    "display_name": "Python 3",
                    "language": "python",
                    "name": "python3",
                },
                "language_info": {"name": "python", "version": "3.9.0"},
            },
            "nbformat": 4,
            "nbformat_minor": 4,
        }

        with open(notebook_path, "w") as f:
            json.dump(notebook, f, indent=2)

        return f"""Analysis complete! Generated files in: {output_dir}

Files created:
  • {csv_path.name} - Color data (both methods)
  • {notebook_path.name} - Jupyter notebook with plots

Summary:
  • Matched colors: {len(matched_colors)} measurements
  • Interpolated colors: {len(interpolated_colors)} measurements
  • Peak color: {peak_color["color"]:.3f} ± {peak_color["color_err"]:.3f} mag
  • Trend: {trend}

Open the notebook to see interactive plots with both methods overlaid!"""

    else:  # text format
        lines = ["=" * 60]
        lines.append(f"COLOR EVOLUTION ANALYSIS: {obj_id}")
        lines.append(f"Color: {band1} - {band2}")
        lines.append(f"Max time gap: {max_time_gap} days")
        lines.append(f"Max data gap: {max_data_gap} days")
        lines.append("=" * 60)
        lines.append("")

        lines.append("## PEAK PROPERTIES")
        lines.append(f"Peak in {band1}:     {peak_mag1:.2f} mag at MJD {peak_mjd1:.2f}")
        lines.append(f"Peak in {band2}:     {peak_mag2:.2f} mag at MJD {peak_mjd2:.2f}")
        if not np.isnan(peak_color["color"]):
            lines.append(
                f"Color at peak:       {peak_color['color']:.3f} ± {peak_color['color_err']:.3f} mag"
            )
            lines.append(
                f"                     (measured at MJD {peak_color['mjd']:.2f})"
            )
        lines.append("")

        lines.append("## COLOR EVOLUTION")
        lines.append(f"Matched measurements:        {len(matched_colors)}")
        lines.append(f"Interpolated measurements:   {len(interpolated_colors)}")
        if not np.isnan(mean_color):
            lines.append(
                f"Mean color (matched):        {mean_color:.3f} ± {color_std:.3f} mag"
            )
            lines.append(f"Color range:                 {color_range:.3f} mag")
            lines.append(f"Trend:                       {trend} ({slope:.4f} mag/day)")
        lines.append("")

        if len(matched_colors) > 0:
            lines.append("## MATCHED COLOR MEASUREMENTS")
            lines.append("MJD          Color      Error")
            lines.append("-" * 35)
            for c in matched_colors[:20]:  # Limit to first 20
                lines.append(
                    f"{c['mjd']:10.2f}   {c['color']:6.3f}   {c['color_err']:6.3f}"
                )
            if len(matched_colors) > 20:
                lines.append(f"... and {len(matched_colors) - 20} more")
            lines.append("")

        lines.append("=" * 60)
        lines.append("\nTo generate interactive plots, use output_format='notebook'")

        return "\n".join(lines)
