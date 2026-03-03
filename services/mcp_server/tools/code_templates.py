# pyright: reportMissingTypeStubs=false
"""Code generation templates for bulk analysis using ztfquery."""

import json
from typing import Any


def generate_ztfquery_setup() -> str:
    """Generate setup code for ztfquery authentication."""
    return """# ztfquery Setup and Authentication
# Run this once to configure IRSA credentials:
# from ztfquery import io
# io.set_account('your_irsa_username', 'your_irsa_password')
# Get IRSA account at: https://irsa.ipac.caltech.edu/account/signon/login.do

import warnings
warnings.filterwarnings('ignore')

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from tqdm.auto import tqdm
from pathlib import Path
"""


def generate_bulk_lightcurve_query(
    source_list: list[str], filters: list[str], include_plots: bool = True
) -> str:
    """Generate code to query forced photometry for multiple sources.

    Args:
        source_list: List of ZTF source names
        filters: List of filter names (e.g., ['ztfg', 'ztfr', 'ztfi'])
        include_plots: Include plotting code

    Returns:
        Python code string for notebook
    """
    source_json = json.dumps(source_list, indent=4)
    filter_json = json.dumps(filters)

    code = generate_ztfquery_setup()

    code += f"""
from ztfquery import lightcurve

# Configuration
sources = {source_json}

filters = {filter_json}

# Results storage
output_dir = Path('ztf_lightcurves')
output_dir.mkdir(exist_ok=True)

results = {{}}
errors = []

print(f"Querying forced photometry for {{len(sources)}} sources...")
print(f"Filters: {{', '.join(filters)}}")
print()

# Query each source
for source in tqdm(sources, desc="Downloading light curves"):
    try:
        # Download forced photometry
        lcq = lightcurve.LCQuery.from_name(source)

        # Get data as DataFrame
        lc_data = lcq.data

        if lc_data is not None and len(lc_data) > 0:
            # Filter by requested bands
            lc_filtered = lc_data[lc_data['filter'].isin(filters)]

            # Save to CSV
            output_file = output_dir / f"{{source}}_lc.csv"
            lc_filtered.to_csv(output_file, index=False)

            results[source] = {{
                'data': lc_filtered,
                'n_points': len(lc_filtered),
                'filters': lc_filtered['filter'].unique().tolist(),
                'file': str(output_file)
            }}

            print(f"✓ {{source}}: {{len(lc_filtered)}} points")
        else:
            print(f"✗ {{source}}: No data")
            errors.append({{'source': source, 'error': 'No data returned'}})

    except Exception as e:
        print(f"✗ {{source}}: {{str(e)}}")
        errors.append({{'source': source, 'error': str(e)}})

print()
print(f"Successfully downloaded: {{len(results)}}/{{len(sources)}}")
print(f"Failed: {{len(errors)}}")

# Save summary
summary = pd.DataFrame([
    {{'source': src, 'n_points': info['n_points'],
      'filters': ','.join(info['filters']), 'file': info['file']}}
    for src, info in results.items()
])
summary.to_csv(output_dir / 'summary.csv', index=False)
print(f"\\nSummary saved to: {{output_dir / 'summary.csv'}}")

if errors:
    error_df = pd.DataFrame(errors)
    error_df.to_csv(output_dir / 'errors.csv', index=False)
    print(f"Errors saved to: {{output_dir / 'errors.csv'}}")
"""

    if include_plots:
        code += """
# Plot light curves
print("\\nGenerating plots...")

fig_dir = output_dir / 'plots'
fig_dir.mkdir(exist_ok=True)

for source, info in tqdm(results.items(), desc="Creating plots"):
    lc_data = info['data']

    # Create figure
    fig, ax = plt.subplots(figsize=(10, 6))

    # Plot each filter
    colors = {'ztfg': 'green', 'ztfr': 'red', 'ztfi': 'orange'}

    for filt in info['filters']:
        mask = lc_data['filter'] == filt
        filt_data = lc_data[mask]

        # Only plot detections (mag is not null)
        detections = filt_data[filt_data['mag'].notna()]

        if len(detections) > 0:
            ax.errorbar(
                detections['mjd'],
                detections['mag'],
                yerr=detections['magerr'],
                fmt='o',
                label=filt,
                color=colors.get(filt, 'gray'),
                alpha=0.7,
                capsize=3
            )

    ax.invert_yaxis()
    ax.set_xlabel('MJD', fontsize=12)
    ax.set_ylabel('AB Magnitude', fontsize=12)
    ax.set_title(f'{source} Light Curve', fontsize=14, fontweight='bold')
    ax.legend()
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(fig_dir / f'{source}_lc.png', dpi=150, bbox_inches='tight')
    plt.close()

print(f"Plots saved to: {fig_dir}")
"""

    return code


def generate_cone_search_query(
    ra_dec_list: list[tuple[float, float]], radius_arcsec: float = 2.0
) -> str:
    """Generate code to perform cone search for multiple coordinates.

    Args:
        ra_dec_list: List of (RA, Dec) tuples in degrees
        radius_arcsec: Search radius in arcseconds

    Returns:
        Python code string for notebook
    """
    coords_json = json.dumps(ra_dec_list, indent=4)

    code = generate_ztfquery_setup()

    code += f"""
from ztfquery import query
from astropy.coordinates import SkyCoord
from astropy import units as u

# Configuration
coordinates = {coords_json}  # List of (RA, Dec) in degrees

radius_arcsec = {radius_arcsec}

# Results storage
output_dir = Path('ztf_cone_search')
output_dir.mkdir(exist_ok=True)

results = []
zq = query.ZTFQuery()

print(f"Performing cone search for {{len(coordinates)}} positions...")
print(f"Search radius: {{radius_arcsec}} arcsec")
print()

for i, (ra, dec) in enumerate(tqdm(coordinates, desc="Querying positions")):
    try:
        # Create coordinate
        coord = SkyCoord(ra=ra*u.deg, dec=dec*u.deg, frame='icrs')

        # Query ZTF metadata
        zq.load_metadata(
            radec=[ra, dec],
            radius_arcsec=radius_arcsec
        )

        if zq.metatable is not None and len(zq.metatable) > 0:
            # Add coordinate info to results
            meta = zq.metatable.copy()
            meta['query_ra'] = ra
            meta['query_dec'] = dec
            meta['query_id'] = i

            results.append(meta)

            print(f"✓ Position {{i+1}} ({{ra:.6f}}, {{dec:.6f}}): {{len(meta)}} detections")
        else:
            print(f"✗ Position {{i+1}} ({{ra:.6f}}, {{dec:.6f}}): No detections")

    except Exception as e:
        print(f"✗ Position {{i+1}} ({{ra:.6f}}, {{dec:.6f}}): {{str(e)}}")

# Combine results
if results:
    combined = pd.concat(results, ignore_index=True)

    # Save results
    output_file = output_dir / 'cone_search_results.csv'
    combined.to_csv(output_file, index=False)

    print()
    print(f"Total detections: {{len(combined)}}")
    print(f"Results saved to: {{output_file}}")

    # Summary by position
    summary = combined.groupby('query_id').agg({{
        'query_ra': 'first',
        'query_dec': 'first',
        'obsjd': 'count'
    }}).rename(columns={{'obsjd': 'n_detections'}})

    print("\\nSummary by position:")
    print(summary)

    summary.to_csv(output_dir / 'summary.csv')
else:
    print("\\nNo detections found for any position.")
"""

    return code


def generate_fritz_bulk_query(
    source_list: list[str], include_spectra: bool = True
) -> str:
    """Generate code to query Fritz/SkyPortal for multiple sources.

    Args:
        source_list: List of source names
        include_spectra: Include spectroscopy queries

    Returns:
        Python code string for notebook
    """
    source_json = json.dumps(source_list, indent=4)

    code = generate_ztfquery_setup()

    code += f"""
from ztfquery import fritz
import os

# Configuration
sources = {source_json}

# Fritz API token (set as environment variable or hardcode)
FRITZ_TOKEN = os.getenv('FRITZ_TOKEN', 'YOUR_TOKEN_HERE')

# Results storage
output_dir = Path('fritz_data')
output_dir.mkdir(exist_ok=True)

# Initialize Fritz connection
fq = fritz.FritzAPI(token=FRITZ_TOKEN)

results = {{}}
errors = []

print(f"Querying Fritz for {{len(sources)}} sources...")
print()

# Query each source
for source in tqdm(sources, desc="Querying sources"):
    try:
        # Get source data
        source_data = fq.get_source(source)

        if source_data:
            results[source] = {{}}

            # Save basic source info
            results[source]['info'] = {{
                'id': source_data.get('id'),
                'ra': source_data.get('ra'),
                'dec': source_data.get('dec'),
                'redshift': source_data.get('redshift'),
                'classifications': source_data.get('classifications', []),
            }}

            # Get photometry
            photometry = source_data.get('photometry', [])
            if photometry:
                phot_df = pd.DataFrame(photometry)
                phot_file = output_dir / f"{{source}}_photometry.csv"
                phot_df.to_csv(phot_file, index=False)
                results[source]['photometry_file'] = str(phot_file)
                results[source]['n_phot'] = len(phot_df)
"""

    if include_spectra:
        code += """
            # Get spectra
            spectra = source_data.get('spectra', [])
            if spectra:
                spec_df = pd.DataFrame(spectra)
                spec_file = output_dir / f"{source}_spectra.csv"
                spec_df.to_csv(spec_file, index=False)
                results[source]['spectra_file'] = str(spec_file)
                results[source]['n_spectra'] = len(spec_df)
"""

    code += """
            print(f"✓ {source}: {results[source].get('n_phot', 0)} phot, "
                  f"{results[source].get('n_spectra', 0)} spectra")
        else:
            print(f"✗ {source}: Not found")
            errors.append({'source': source, 'error': 'Source not found'})

    except Exception as e:
        print(f"✗ {source}: {str(e)}")
        errors.append({'source': source, 'error': str(e)}})

print()
print(f"Successfully queried: {len(results)}/{len(sources)}")

# Save summary
summary_data = []
for src, data in results.items():
    info = data.get('info', {})
    summary_data.append({
        'source': src,
        'ra': info.get('ra'),
        'dec': info.get('dec'),
        'redshift': info.get('redshift'),
        'n_photometry': data.get('n_phot', 0),
        'n_spectra': data.get('n_spectra', 0),
    })

summary = pd.DataFrame(summary_data)
summary.to_csv(output_dir / 'summary.csv', index=False)
print(f"\\nSummary saved to: {output_dir / 'summary.csv'}")

if errors:
    error_df = pd.DataFrame(errors)
    error_df.to_csv(output_dir / 'errors.csv', index=False)
"""

    return code


def generate_alert_query(source_list: list[str], with_cutouts: bool = True) -> str:
    """Generate code to download ZTF alert packets.

    Args:
        source_list: List of ZTF source names
        with_cutouts: Include cutout image downloads

    Returns:
        Python code string for notebook
    """
    source_json = json.dumps(source_list, indent=4)

    code = generate_ztfquery_setup()

    code += f"""
from ztfquery import alert

# Configuration
sources = {source_json}

with_cutouts = {str(with_cutouts)}

# Results storage
output_dir = Path('ztf_alerts')
output_dir.mkdir(exist_ok=True)

if with_cutouts:
    cutout_dir = output_dir / 'cutouts'
    cutout_dir.mkdir(exist_ok=True)

results = {{}}
errors = []

print(f"Downloading alert packets for {{len(sources)}} sources...")
print(f"Include cutouts: {{with_cutouts}}")
print()

for source in tqdm(sources, desc="Downloading alerts"):
    try:
        # Download alerts for this source
        alertq = alert.AlertQuery.from_name(source)

        if alertq.data is not None and len(alertq.data) > 0:
            # Save alert data
            alert_file = output_dir / f"{{source}}_alerts.json"
            alertq.store(alert_file)

            results[source] = {{
                'n_alerts': len(alertq.data),
                'alert_file': str(alert_file),
            }}
"""

    if with_cutouts:
        code += """
            # Download cutouts if requested
            if with_cutouts:
                try:
                    cutouts = alertq.get_cutouts()
                    cutout_files = []

                    for i, cutout_dict in enumerate(cutouts):
                        for cutout_type, cutout_data in cutout_dict.items():
                            cutout_file = cutout_dir / f"{source}_alert{i}_{cutout_type}.fits"
                            # Save cutout (this depends on ztfquery version)
                            # You may need to adjust this based on actual data structure
                            cutout_files.append(str(cutout_file))

                    results[source]['cutout_files'] = cutout_files
                    results[source]['n_cutouts'] = len(cutout_files)
                except Exception as e:
                    print(f"  Warning: Could not download cutouts for {source}: {e}")
"""

    code += """
            print(f"✓ {source}: {results[source]['n_alerts']} alerts")
        else:
            print(f"✗ {source}: No alerts found")
            errors.append({'source': source, 'error': 'No alerts'})

    except Exception as e:
        print(f"✗ {source}: {str(e)}")
        errors.append({'source': source, 'error': str(e)}})

print()
print(f"Successfully downloaded: {len(results)}/{len(sources)}")

# Save summary
summary = pd.DataFrame([
    {'source': src, 'n_alerts': info['n_alerts'],
     'n_cutouts': info.get('n_cutouts', 0)}
    for src, info in results.items()
])
summary.to_csv(output_dir / 'summary.csv', index=False)
print(f"\\nSummary saved to: {output_dir / 'summary.csv'}")

if errors:
    error_df = pd.DataFrame(errors)
    error_df.to_csv(output_dir / 'errors.csv', index=False)
"""

    return code


def generate_field_visualization(field_id: int, ccd_id: int | None = None) -> str:
    """Generate code to visualize ZTF field/CCD coverage.

    Args:
        field_id: ZTF field ID
        ccd_id: Optional CCD ID (1-16)

    Returns:
        Python code string for notebook
    """
    code = generate_ztfquery_setup()

    code += f"""
from ztfquery import skyvision

# Configuration
field_id = {field_id}
ccd_id = {ccd_id if ccd_id else "None"}

# Create field visualizer
sv = skyvision.SkyVision.from_field(field_id, ccd=ccd_id)

# Plot field coverage
fig = plt.figure(figsize=(12, 10))
ax = fig.add_subplot(111, projection='mollweide')

sv.show(ax=ax, show_ccd={str(ccd_id is not None)})

plt.title(f'ZTF Field {{field_id}}' + (f' CCD {{ccd_id}}' if ccd_id else ''),
          fontsize=14, fontweight='bold')
plt.tight_layout()
plt.show()

# Get field information
print(f"Field {{field_id}} coverage:")
print(f"  RA range: {{sv.ra_range}}")
print(f"  Dec range: {{sv.dec_range}}")
"""

    return code
