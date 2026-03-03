# pyright: reportMissingTypeStubs=false
"""Light curve and color analysis tools for transients."""

import httpx
import numpy as np

from ..server import SKYPORTAL_URL, get_skyportal_token, mcp
from .source_products import resolve_source_id


@mcp.tool()
async def analyze_light_curve(
    source_name: str,
    filter_name: str = "ztfr",
    baseline_threshold: float = 0.3,
    output_format: str = "text",
) -> str:
    """Analyze light curve evolution: rise, fade, duration, and variability.

    Calculates key temporal properties of a transient's light curve including
    rise time, fade time, total duration, and pre-peak variability (flares).

    Handles incomplete light curves:
    - Still rising: Reports time from first detection to current
    - Still fading: Reports time from peak to current
    - Returned to baseline: Reports complete rise + fade times

    **IMPORTANT - User Preference:**
    Before calling this tool, ask the user: "Would you like the analysis as
    (1) text summary in chat, or (2) interactive plot in a notebook?"
    - If (1): Use output_format="text" (default)
    - If (2): Use output_format="notebook" and insert returned code into notebook

    Args:
        source_name: Source identifier - SkyPortal obj_id, ZTF name, or TNS name
        filter_name: Photometric filter to analyze (default: "ztfr")
        baseline_threshold: Magnitude difference from peak to consider "baseline"
                          (default: 0.3 mag, i.e., source must fade by >0.3 mag
                          from peak to be considered at baseline)
        output_format: Output format - "text" for chat summary or "notebook" for
                      Python code to plot in a Jupyter notebook (default: "text")

    Returns:
        - If output_format="text": Formatted text summary with rise/fade times,
          duration, rates, and variability metrics
        - If output_format="notebook": Python code that creates an interactive
          plot with embedded data and prints analysis results
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

    # Filter by requested band and valid detections
    phot = [
        p
        for p in data
        if p.get("filter") == filter_name
        and p.get("mag") is not None
        and p.get("magerr") is not None
    ]

    if len(phot) < 2:
        return f"Insufficient photometry in {filter_name} band (need at least 2 points)"

    # Sort by time
    phot.sort(key=lambda p: p["mjd"])

    # Extract arrays
    mjds = np.array([p["mjd"] for p in phot])
    mags = np.array([p["mag"] for p in phot])
    magerrs = np.array([p["magerr"] for p in phot])

    # Find peak (minimum magnitude = brightest)
    peak_idx = np.argmin(mags)
    peak_mjd = mjds[peak_idx]
    peak_mag = mags[peak_idx]

    # First and last detection
    first_mjd = mjds[0]
    first_mag = mags[0]
    last_mjd = mjds[-1]
    last_mag = mags[-1]

    # Rise time: first detection to peak
    rise_time = peak_mjd - first_mjd
    rise_mag = first_mag - peak_mag  # How much it brightened

    # Check if still rising (peak is last point)
    still_rising = peak_idx == len(mjds) - 1

    # Fade analysis
    if still_rising:
        fade_time = None
        fade_mag = None
        fade_rate = None
        status = "Still rising"
        duration = None
    else:
        # Post-peak data
        post_peak_mjds = mjds[peak_idx:]
        post_peak_mags = mags[peak_idx:]

        # Check if returned to baseline (faded by > threshold mag)
        faded = post_peak_mags - peak_mag
        baseline_reached = np.any(faded > baseline_threshold)

        if baseline_reached:
            # Find first point where baseline is reached
            baseline_idx = peak_idx + np.where(faded > baseline_threshold)[0][0]
            baseline_mjd = mjds[baseline_idx]
            fade_time = baseline_mjd - peak_mjd
            fade_mag = (
                post_peak_mags[np.where(faded > baseline_threshold)[0][0]] - peak_mag
            )
            status = "Complete light curve"
            duration = rise_time + fade_time
        else:
            # Still fading
            fade_time = last_mjd - peak_mjd
            fade_mag = last_mag - peak_mag
            status = "Still fading"
            duration = None

        fade_rate = fade_mag / fade_time if fade_time > 0 else None

    # Rise rate
    rise_rate = rise_mag / rise_time if rise_time > 0 else None

    # Pre-peak variability analysis (detect flares)
    if peak_idx > 1:
        pre_peak_mags = mags[:peak_idx]
        # Check for magnitude increases before peak (flares)
        mag_diffs = np.diff(pre_peak_mags)
        brightening_events = np.sum(mag_diffs < -0.1)  # Brightening by >0.1 mag
        variability_rms = np.std(pre_peak_mags)
    else:
        brightening_events = 0
        variability_rms = 0.0

    # Generate notebook code if requested
    if output_format == "notebook":
        # Convert arrays to Python lists for embedding in code
        mjd_list = mjds.tolist()
        mag_list = mags.tolist()
        magerr_list = magerrs.tolist()

        code = f'''import matplotlib.pyplot as plt
                import numpy as np

                # Light curve data for {obj_id} ({filter_name} band)
                mjd = {mjd_list}
                mag = {mag_list}
                magerr = {magerr_list}

                # Analysis results
                peak_mjd = {peak_mjd}
                peak_mag = {peak_mag}
                first_mjd = {first_mjd}
                rise_time = {rise_time}
                rise_mag = {rise_mag}
                status = "{status}"

                # Create figure
                fig, ax = plt.subplots(figsize=(12, 6))

                # Plot photometry
                ax.errorbar(mjd, mag, yerr=magerr, fmt='o', markersize=6,
                            capsize=3, label='{filter_name} photometry', alpha=0.7)

                # Mark peak
                ax.axvline(peak_mjd, color='red', linestyle='--', linewidth=2,
                        label=f'Peak: MJD {{peak_mjd:.2f}}')
                ax.plot(peak_mjd, peak_mag, 'r*', markersize=20, label=f'Peak mag: {{peak_mag:.2f}}')

                # Formatting
                ax.invert_yaxis()  # Brighter = lower magnitude
                ax.set_xlabel('MJD', fontsize=12)
                ax.set_ylabel('AB Magnitude', fontsize=12)
                ax.set_title(f'{obj_id} Light Curve Analysis ({filter_name})', fontsize=14, fontweight='bold')
                ax.legend(loc='best', fontsize=10)
                ax.grid(True, alpha=0.3)

                plt.tight_layout()
                plt.show()

                # Print analysis results
                print("=" * 60)
                print(f"LIGHT CURVE ANALYSIS: {obj_id}")
                print(f"Filter: {filter_name}")
                print("=" * 60)
                print()
                print("## OVERVIEW")
                print(f"Status:           {{status}}")
                print(f"Total points:     {{len(mjd)}}")
                print(f"Time span:        {{min(mjd):.1f}} - {{max(mjd):.1f}} MJD ({{max(mjd) - min(mjd):.1f}} days)")
                print()
                print("## PEAK PROPERTIES")
                print(f"Peak magnitude:   {{peak_mag:.2f}} mag")
                print(f"Peak time:        MJD {{peak_mjd:.2f}}")
                print(f"Peak epoch:       Day {{peak_mjd - first_mjd:.1f}} (from first detection)")
                print()
                print("## RISE PROPERTIES")
                print(f"Rise time:        {{rise_time:.1f}} days")
                print(f"Rise amplitude:   {{rise_mag:.2f}} mag")'''

        if rise_rate:
            code += f'\nprint(f"Rise rate:        {{{rise_rate:.3f}}} mag/day")'
        if still_rising:
            code += '\nprint("Note:             Source is still rising (peak = last detection)")'

        code += '\nprint()\nprint("## FADE PROPERTIES")'

        if fade_time:
            code += f"""
print(f"Fade time:        {fade_time:.1f} days")
print(f"Fade amplitude:   {fade_mag:.2f} mag")"""
            if fade_rate:
                code += f"""
print(f"Fade rate:        {fade_rate:.3f} mag/day")"""
        else:
            code += '\nprint("Fade time:        Not yet available (still rising)")'

        if duration:
            code += f"""
print(f"Total duration:   {duration:.1f} days (rise + fade)")"""
        else:
            code += '\nprint("Total duration:   Not yet determined (light curve incomplete)")'

        code += f"""
print()
print("## VARIABILITY")
print(f"Pre-peak RMS:     {variability_rms:.3f} mag")"""

        if brightening_events > 0:
            code += f"""
print(f"Early flares:     {brightening_events} brightening event(s) detected before peak")
print("                  (magnitude increases >0.1 mag)")"""
        else:
            code += '\nprint("Early flares:     None detected")'

        code += '\nprint()\nprint("=" * 60)'

        return code

    # Format text output
    lines = ["=" * 60]
    lines.append(f"LIGHT CURVE ANALYSIS: {obj_id}")
    lines.append(f"Filter: {filter_name}")
    lines.append("=" * 60)
    lines.append("")

    lines.append("## OVERVIEW")
    lines.append(f"Status:           {status}")
    lines.append(f"Total points:     {len(phot)}")
    lines.append(
        f"Time span:        {first_mjd:.1f} - {last_mjd:.1f} MJD ({last_mjd - first_mjd:.1f} days)"
    )
    lines.append("")

    lines.append("## PEAK PROPERTIES")
    lines.append(f"Peak magnitude:   {peak_mag:.2f} ± {magerrs[peak_idx]:.2f} mag")
    lines.append(f"Peak time:        MJD {peak_mjd:.2f}")
    lines.append(
        f"Peak epoch:       Day {peak_mjd - first_mjd:.1f} (from first detection)"
    )
    lines.append("")

    lines.append("## RISE PROPERTIES")
    lines.append(f"Rise time:        {rise_time:.1f} days")
    lines.append(f"Rise amplitude:   {rise_mag:.2f} mag")
    if rise_rate:
        lines.append(f"Rise rate:        {rise_rate:.3f} mag/day")
    if still_rising:
        lines.append("Note:             Source is still rising (peak = last detection)")
    lines.append("")

    lines.append("## FADE PROPERTIES")
    if fade_time:
        lines.append(f"Fade time:        {fade_time:.1f} days")
        lines.append(f"Fade amplitude:   {fade_mag:.2f} mag")
        if fade_rate:
            lines.append(f"Fade rate:        {fade_rate:.3f} mag/day")
    else:
        lines.append("Fade time:        Not yet available (still rising)")

    if duration:
        lines.append(f"Total duration:   {duration:.1f} days (rise + fade)")
    else:
        lines.append("Total duration:   Not yet determined (light curve incomplete)")
    lines.append("")

    lines.append("## VARIABILITY")
    lines.append(f"Pre-peak RMS:     {variability_rms:.3f} mag")
    if brightening_events > 0:
        lines.append(
            f"Early flares:     {brightening_events} brightening event(s) detected before peak"
        )
        lines.append("                  (magnitude increases >0.1 mag)")
    else:
        lines.append("Early flares:     None detected")
    lines.append("")

    lines.append("=" * 60)

    return "\n".join(lines)


@mcp.tool()
async def analyze_color_evolution(
    source_name: str,
    band1: str = "ztfg",
    band2: str = "ztfr",
    method: str = "matched",
    max_time_gap: float = 0.5,
    max_data_gap: float = 3.0,
    output_format: str = "text",
) -> str:
    """Analyze color evolution and color at peak brightness.

    Calculates color curves (band1 - band2) over time using two methods:

    1. **Matched observations** (method="matched"): Pairs observations from
       each band that are close in time, but avoids calculating colors
       across large gaps in the data.

    2. **Interpolated** (method="interpolated"): Interpolates one band to
       match the other's observation times, creating a rolling/continuous
       color measurement. More measurements but assumes smooth evolution.

    **IMPORTANT - User Preferences:**
    Before calling this tool, ask the user TWO questions:
    1. "Would you like day-to-day colors (matched method) or rolling/continuous
       colors (interpolated method)?"
    2. "Would you like the analysis as text in chat or interactive plot in notebook?"

    Args:
        source_name: Source identifier - SkyPortal obj_id, ZTF name, or TNS name
        band1: First photometric filter (default: "ztfg")
        band2: Second photometric filter (default: "ztfr")
        method: Calculation method - "matched" or "interpolated" (default: "matched")
        max_time_gap: For matched method - maximum time difference (days) to
                     pair observations (default: 0.5 days)
        max_data_gap: For matched method - if gap between consecutive observations
                     in either band exceeds this, don't calculate colors across
                     the gap (default: 3.0 days). Prevents spurious colors during
                     observing gaps.
        output_format: Output format - "text" for chat summary or "notebook" for
                      Python code to plot in a Jupyter notebook (default: "text")

    Returns:
        - If output_format="text": Formatted text summary with color at peak,
          evolution statistics, and CSV table of measurements
        - If output_format="notebook": Python code that creates interactive plots
          (light curves + color evolution) with embedded data and analysis results
    """
    token = get_skyportal_token()
    if not token:
        return "Not authenticated. Configure SKYPORTAL_TOKEN or send Bearer token."

    if method not in ("matched", "interpolated"):
        return "Error: method must be 'matched' or 'interpolated'"

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

    # Calculate colors based on method
    colors = []

    if method == "matched":
        # Matched observations - pair close observations but respect gaps
        for i, p1 in enumerate(phot1):
            mjd1 = p1["mjd"]
            mag1 = p1["mag"]
            err1 = p1["magerr"]

            # Check if this observation is in a large gap
            # (if time to prev/next obs > max_data_gap, skip)
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

                    colors.append(
                        {
                            "mjd": mjd1,
                            "color": color,
                            "color_err": color_err,
                            "mag1": mag1,
                            "mag2": mag2,
                        }
                    )

    else:  # interpolated
        # Interpolate band2 to match band1 times
        # Use linear interpolation
        from scipy.interpolate import interp1d

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
                    # Conservative error: add interpolation uncertainty
                    color_err = np.sqrt(err1**2 + err2_interp**2)

                    colors.append(
                        {
                            "mjd": mjd1,
                            "color": color,
                            "color_err": color_err,
                            "mag1": mag1,
                            "mag2": mag2_interp,
                        }
                    )
        except Exception as e:
            return f"Error in interpolation: {e}. Try 'matched' method instead."

    if len(colors) < 2:
        return f"Insufficient color measurements (got {len(colors)}, need at least 2). Try adjusting max_time_gap or method."

    # Find peak in each band
    peak_idx1 = np.argmin(mags1)
    peak_idx2 = np.argmin(mags2)
    peak_mjd1 = mjds1[peak_idx1]
    peak_mjd2 = mjds2[peak_idx2]
    peak_mag1 = mags1[peak_idx1]
    peak_mag2 = mags2[peak_idx2]

    # Find color closest to peak time (use average of peak times)
    peak_mjd_avg = (peak_mjd1 + peak_mjd2) / 2
    color_mjds = np.array([c["mjd"] for c in colors])
    peak_color_idx = np.argmin(np.abs(color_mjds - peak_mjd_avg))
    peak_color = colors[peak_color_idx]

    # Color evolution statistics
    color_vals = np.array([c["color"] for c in colors])
    mean_color = np.mean(color_vals)
    color_range = np.ptp(color_vals)
    color_std = np.std(color_vals)

    # Simple linear trend (slope)
    if len(colors) > 2:
        color_mjds_centered = color_mjds - color_mjds[0]
        slope, _ = np.polyfit(color_mjds_centered, color_vals, 1)
        trend = "bluing" if slope < -0.01 else "reddening" if slope > 0.01 else "stable"
    else:
        slope = 0
        trend = "insufficient data"

    # Generate notebook code if requested
    if output_format == "notebook":
        # Convert to lists for embedding
        mjd1_list = mjds1.tolist()
        mag1_list = mags1.tolist()
        err1_list = errs1.tolist()
        mjd2_list = mjds2.tolist()
        mag2_list = mags2.tolist()
        err2_list = errs2.tolist()
        color_mjd_list = color_mjds.tolist()
        color_val_list = color_vals.tolist()
        color_err_list = [c["color_err"] for c in colors]

        code = f'''import matplotlib.pyplot as plt
import numpy as np

# Photometry data for {obj_id}
mjd_{band1} = {mjd1_list}
mag_{band1} = {mag1_list}
err_{band1} = {err1_list}

mjd_{band2} = {mjd2_list}
mag_{band2} = {mag2_list}
err_{band2} = {err2_list}

# Color measurements ({band1} - {band2})
color_mjd = {color_mjd_list}
color = {color_val_list}
color_err = {color_err_list}

# Analysis results
peak_mjd_{band1} = {peak_mjd1}
peak_mag_{band1} = {peak_mag1}
peak_mjd_{band2} = {peak_mjd2}
peak_mag_{band2} = {peak_mag2}
peak_color = {peak_color["color"]}
mean_color = {mean_color}
trend = "{trend}"

# Create figure with two subplots
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10), sharex=True)

# Top panel: Light curves
ax1.errorbar(mjd_{band1}, mag_{band1}, yerr=err_{band1}, fmt='o',
             label='{band1}', color='blue', alpha=0.7, capsize=3)
ax1.errorbar(mjd_{band2}, mag_{band2}, yerr=err_{band2}, fmt='s',
             label='{band2}', color='red', alpha=0.7, capsize=3)
ax1.axvline(peak_mjd_{band1}, color='blue', linestyle='--', alpha=0.5)
ax1.axvline(peak_mjd_{band2}, color='red', linestyle='--', alpha=0.5)
ax1.invert_yaxis()
ax1.set_ylabel('AB Magnitude', fontsize=12)
ax1.set_title(f'{obj_id} Multi-band Light Curves', fontsize=14, fontweight='bold')
ax1.legend(loc='best', fontsize=10)
ax1.grid(True, alpha=0.3)

# Bottom panel: Color evolution
ax2.errorbar(color_mjd, color, yerr=color_err, fmt='o',
             color='purple', markersize=6, capsize=3, alpha=0.7)
ax2.axhline(peak_color, color='red', linestyle='--', linewidth=2,
            label=f'Color at peak: {{peak_color:.3f}} mag')
ax2.axhline(mean_color, color='gray', linestyle=':', linewidth=1.5,
            label=f'Mean color: {{mean_color:.3f}} mag')
ax2.set_xlabel('MJD', fontsize=12)
ax2.set_ylabel(f'{{"{band1}"}} - {{"{band2}"}} (mag)', fontsize=12)
ax2.set_title(f'Color Evolution ({{"{method}"}} method)', fontsize=12)
ax2.legend(loc='best', fontsize=10)
ax2.grid(True, alpha=0.3)

plt.tight_layout()
plt.show()

# Print analysis results
print("=" * 60)
print(f"COLOR EVOLUTION ANALYSIS: {obj_id}")
print(f"Color: {band1} - {band2}")
print(f"Method: {method}")'''

        if method == "matched":
            code += f"""
print(f"Max time gap: {max_time_gap} days")
print(f"Max data gap: {max_data_gap} days")"""

        code += f"""
print("=" * 60)
print()
print("## PEAK PROPERTIES")
print(f"Peak in {band1}:     {{peak_mag_{band1}:.2f}} mag at MJD {{peak_mjd_{band1}:.2f}}")
print(f"Peak in {band2}:     {{peak_mag_{band2}:.2f}} mag at MJD {{peak_mjd_{band2}:.2f}}")
print(f"Color at peak:       {{peak_color:.3f}} mag")
print()
print("## COLOR EVOLUTION")
print(f"Measurements:        {{len(color)}}")
print(f"Mean color:          {{mean_color:.3f}} mag")
print(f"Color range:         {{np.ptp(color):.3f}} mag")
print(f"Trend:               {{trend}}")
print()
print("=" * 60)"""

        return code

    # Format text output
    lines = ["=" * 60]
    lines.append(f"COLOR EVOLUTION ANALYSIS: {obj_id}")
    lines.append(f"Color: {band1} - {band2}")
    lines.append(f"Method: {method}")
    if method == "matched":
        lines.append(f"Max time gap: {max_time_gap} days")
        lines.append(f"Max data gap: {max_data_gap} days")
    lines.append("=" * 60)
    lines.append("")

    lines.append("## PEAK PROPERTIES")
    lines.append(f"Peak in {band1}:     {peak_mag1:.2f} mag at MJD {peak_mjd1:.2f}")
    lines.append(f"Peak in {band2}:     {peak_mag2:.2f} mag at MJD {peak_mjd2:.2f}")
    lines.append(
        f"Color at peak:       {peak_color['color']:.3f} ± {peak_color['color_err']:.3f} mag"
    )
    lines.append(f"                     (measured at MJD {peak_color['mjd']:.2f})")
    lines.append("")

    lines.append("## COLOR EVOLUTION")
    lines.append(f"Measurements:        {len(colors)}")
    lines.append(f"Mean color:          {mean_color:.3f} ± {color_std:.3f} mag")
    lines.append(f"Color range:         {color_range:.3f} mag")
    lines.append(f"Trend:               {trend} ({slope:.4f} mag/day)")
    lines.append("")

    lines.append("## COLOR MEASUREMENTS")
    lines.append("MJD          Color      Error")
    lines.append("-" * 35)
    for c in colors:
        lines.append(f"{c['mjd']:10.2f}   {c['color']:6.3f}   {c['color_err']:6.3f}")
    lines.append("")

    lines.append("=" * 60)

    return "\n".join(lines)
