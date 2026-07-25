# pyright: reportMissingTypeStubs=false
"""Code generation templates for bulk analysis using ztfquery."""

import json


def _make_code_cell(source: str) -> dict:
    """Create a Jupyter notebook code cell."""
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": source.splitlines(keepends=True),
    }


def _make_markdown_cell(source: str) -> dict:
    """Create a Jupyter notebook markdown cell."""
    return {
        "cell_type": "markdown",
        "metadata": {},
        "source": source.splitlines(keepends=True),
    }


def _common_imports() -> str:
    """Common imports shared by all code templates."""
    return """import warnings
warnings.filterwarnings('ignore')

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from tqdm.auto import tqdm
from pathlib import Path
"""


def generate_fritz_setup() -> str:
    """Generate setup code for Fritz/SkyPortal via ztfquery."""
    return (
        """# ============================================================
# Fritz/SkyPortal Setup (via ztfquery)
# ============================================================
# Prerequisites (run these in your terminal ONCE before using):
#
# 1. Install ztfquery:
#      pip install ztfquery
#
# 2. Get your Fritz API token:
#      Go to https://fritz.science/profile and copy your token.
#
# 3. Configure ztfquery with your Fritz token:
#      python -c "from ztfquery.io import set_account; set_account('fritz', token_based=True)"
#      (It will prompt you for your token and save it to ~/.ztfquery)
#
# Troubleshooting:
#   - If you get 401 errors, re-run step 3 with a fresh token
#   - Token expires? Generate a new one from your Fritz profile
# ============================================================

"""
        + _common_imports()
        + """
from ztfquery import fritz
"""
    )


def generate_irsa_setup() -> str:
    """Generate setup code for IRSA access via ztfquery."""
    return """# ============================================================
# IRSA / ZTF Archive Setup (via ztfquery)
# ============================================================
# Prerequisites (run these in your terminal ONCE before using):
#
# 1. Install ztfquery:
#      pip install ztfquery
#
# 2. Create a free IRSA account (needed for ZTF data access):
#      https://irsa.ipac.caltech.edu/account/signon/login.do
#
# 3. Configure your IRSA credentials:
#      python -c "from ztfquery import io; io.set_account('YOUR_IRSA_USERNAME', 'YOUR_IRSA_PASSWORD')"
#
#    This saves credentials to ~/.ztfquery/config.ini so you
#    only need to do it once.
#
# Troubleshooting:
#   - If you get authentication errors, re-run step 3
#   - If ztfquery is slow, it's downloading from IRSA — be patient
#   - For large queries (>50 sources), consider running overnight
# ============================================================

""" + _common_imports()


def generate_bulk_lightcurve_query(
    source_list: list[str], filters: list[str], include_plots: bool = True
) -> str:
    """Generate a Jupyter notebook to bulk download light curves from Fritz.

    Args:
        source_list: List of ZTF source names
        filters: List of filter names (e.g., ['ztfg', 'ztfr', 'ztfi'])
        include_plots: Include Plotly plotting cells

    Returns:
        JSON string of a Jupyter notebook, to be saved as .ipynb
    """
    from pathlib import Path

    source_json = json.dumps(source_list, indent=4)
    filter_json = json.dumps(filters)

    output_dir = Path("ztf_lightcurves")
    output_dir.mkdir(exist_ok=True)
    notebook_path = output_dir / "bulk_lightcurve_download.ipynb"

    cells = []

    # Cell 0: Info markdown
    cells.append(
        _make_markdown_cell(
            "# Bulk ZTF Light Curve Download\n"
            "\n"
            "Downloads **alert photometry** (detection-epoch data) from Fritz/SkyPortal.\n"
            "\n"
            "> **Need forced photometry?** (includes non-detections & upper limits)\n"
            "> Use the [IRSA ZTF forced photometry service]"
            "(https://irsa.ipac.caltech.edu/cgi-bin/ZTF/nph_light_curves) instead.\n"
            "> Forced photometry requires a free IRSA account."
        )
    )

    # Cell 1: Setup & imports
    cells.append(
        _make_code_cell(
            "# Fritz/SkyPortal Setup (via ztfquery)\n"
            "# Prerequisites (run ONCE in your terminal before using):\n"
            "#   1. pip install ztfquery\n"
            "#   2. Get your Fritz API token from https://fritz.science/profile\n"
            "#   3. python -c \"from ztfquery.io import set_account; set_account('fritz', token_based=True)\"\n"
            "#      (saves token to ~/.ztfquery)\n"
            "\n"
            "import warnings\n"
            "warnings.filterwarnings('ignore')\n"
            "\n"
            "import numpy as np\n"
            "import pandas as pd\n"
            "from pathlib import Path\n"
            "from ztfquery import fritz\n"
            "\n"
            "import plotly.graph_objects as go\n"
            "from plotly.offline import init_notebook_mode, iplot\n"
            "init_notebook_mode(connected=True)"
        )
    )

    # Cell 2: Configuration
    cells.append(
        _make_code_cell(
            f"# Configuration — edit these as needed\n"
            f"sources = {source_json}\n"
            f"\n"
            f"filters = {filter_json}\n"
            f"\n"
            f"output_dir = Path('ztf_lightcurves')\n"
            f"output_dir.mkdir(exist_ok=True)"
        )
    )

    # Cell 3: Download
    cells.append(
        _make_code_cell(
            "# Download light curves from Fritz (multiprocessed)\n"
            "print(f'Downloading light curves for {len(sources)} sources from Fritz...')\n"
            "print(f'Filters: {filters}')\n"
            "print()\n"
            "\n"
            "fritz.bulk_download('lightcurve', sources, nprocess=4, store=True)\n"
            "print('\\nBulk download complete.')"
        )
    )

    # Cell 4: Load, filter, save CSVs
    cells.append(
        _make_code_cell(
            "# Load downloaded data, filter by band, save CSVs\n"
            "results = {}\n"
            "errors = []\n"
            "\n"
            "for source in sources:\n"
            "    try:\n"
            "        # download_lightcurve returns a DataFrame directly\n"
            "        # Data is already cached locally from bulk_download above\n"
            "        lc_data = fritz.download_lightcurve(source, store=True)\n"
            "\n"
            "        if lc_data is not None and len(lc_data) > 0:\n"
            "            lc_filtered = lc_data[lc_data['filter'].isin(filters)].copy()\n"
            "\n"
            "            output_file = output_dir / f'{source}_lc.csv'\n"
            "            lc_filtered.to_csv(output_file, index=False)\n"
            "\n"
            "            results[source] = {\n"
            "                'data': lc_filtered,\n"
            "                'n_points': len(lc_filtered),\n"
            "                'filters': lc_filtered['filter'].unique().tolist(),\n"
            "                'file': str(output_file)\n"
            "            }\n"
            "            print(f'✓ {source}: {len(lc_filtered)} points')\n"
            "        else:\n"
            "            print(f'✗ {source}: No data')\n"
            "            errors.append({'source': source, 'error': 'No data'})\n"
            "    except Exception as e:\n"
            "        print(f'✗ {source}: {e}')\n"
            "        errors.append({'source': source, 'error': str(e)})\n"
            "\n"
            "print(f'\\nLoaded: {len(results)}/{len(sources)}')\n"
            "\n"
            "# Save summary\n"
            "summary = pd.DataFrame([\n"
            "    {'source': src, 'n_points': info['n_points'],\n"
            "     'filters': ','.join(info['filters']), 'file': info['file']}\n"
            "    for src, info in results.items()\n"
            "])\n"
            "summary.to_csv(output_dir / 'summary.csv', index=False)\n"
            "print(f'Summary saved to: {output_dir / \"summary.csv\"}')"
        )
    )

    # Cell 5: Plotly interactive plots (one per source)
    if include_plots:
        cells.append(
            _make_code_cell(
                "# Interactive Plotly light curve plots\n"
                "filter_colors = {\n"
                "    'ztfg': '#28a745', 'ztfr': '#dc3545', 'ztfi': '#8b0000',\n"
                "    'sdssg': '#28a745', 'sdssr': '#dc3545', 'sdssi': '#8b0000',\n"
                "}\n"
                "\n"
                "def hex_to_rgba(hex_color, alpha):\n"
                "    h = hex_color.lstrip('#')\n"
                "    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)\n"
                "    return f'rgba({r},{g},{b},{alpha})'\n"
                "\n"
                "for source, info in results.items():\n"
                "    df = info['data'].copy()\n"
                "    fig = go.Figure()\n"
                "\n"
                "    for filt in info['filters']:\n"
                "        df_f = df[(df['filter'] == filt) & df['mag'].notna()].sort_values('mjd')\n"
                "        if len(df_f) == 0:\n"
                "            continue\n"
                "        color = filter_colors.get(filt, '#1f77b4')\n"
                "        fig.add_trace(go.Scatter(\n"
                "            x=df_f['mjd'], y=df_f['mag'],\n"
                "            error_y=dict(type='data', array=df_f['magerr'], visible=True, thickness=1.5),\n"
                "            mode='markers',\n"
                "            marker=dict(size=6, color=hex_to_rgba(color, 0.6),\n"
                "                        line=dict(color=color, width=1.5)),\n"
                "            name=filt,\n"
                "            hovertemplate='MJD: %{x:.2f}<br>Mag: %{y:.3f}<extra></extra>'\n"
                "        ))\n"
                "\n"
                "    fig.update_layout(\n"
                "        title=f'{source} Light Curve',\n"
                "        xaxis_title='MJD', yaxis_title='AB Magnitude',\n"
                "        yaxis=dict(autorange='reversed'),\n"
                "        template='plotly_white', width=900, height=500\n"
                "    )\n"
                "    iplot(fig)"
            )
        )

    # Build notebook JSON
    notebook = {
        "nbformat": 4,
        "nbformat_minor": 5,
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            },
            "language_info": {"name": "python", "version": "3.11.0"},
        },
        "cells": cells,
    }

    with open(notebook_path, "w") as f:
        json.dump(notebook, f, indent=1)

    return (
        f"Notebook saved to: {notebook_path}\n"
        f"Open it in VS Code or Jupyter and run the cells to download "
        f"light curves for {len(source_list)} sources from Fritz."
    )


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

    code = generate_irsa_setup()

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

    code = generate_fritz_setup()

    code += f"""
# Configuration
sources = {source_json}

# Results storage
output_dir = Path('fritz_data')
output_dir.mkdir(exist_ok=True)

results = {{}}
errors = []

# ---- Bulk download photometry ----
print(f"Downloading photometry + spectra for {{len(sources)}} sources from Fritz...")
print()

fritz.bulk_download("lightcurve", sources, nprocess=4, store=True)
"""

    if include_spectra:
        code += """
fritz.bulk_download("spectra", sources, nprocess=4, store=True)
"""

    code += f"""
# ---- Load and save results ----
for source in sources:
    try:
        results[source] = {{}}

        # download_lightcurve returns a DataFrame directly
        # Data is already cached locally from bulk_download above
        lc_data = fritz.download_lightcurve(source, store=True)
        if lc_data is not None and len(lc_data) > 0:
            phot_file = output_dir / f"{{source}}_photometry.csv"
            lc_data.to_csv(phot_file, index=False)
            results[source]['n_phot'] = len(lc_data)
"""

    if include_spectra:
        code += """
        # download_spectra returns spectral data
        try:
            spec_data = fritz.download_spectra(source, store=True)
            if spec_data is not None and len(spec_data) > 0:
                spec_file = output_dir / f"{source}_spectra.csv"
                if hasattr(spec_data, 'to_csv'):
                    spec_data.to_csv(spec_file, index=False)
                results[source]['n_spectra'] = len(spec_data)
        except Exception:
            pass  # spectra not available for all sources
"""

    code += """
        n_phot = results[source].get('n_phot', 0)
        n_spec = results[source].get('n_spectra', 0)
        print(f"✓ {source}: {n_phot} phot, {n_spec} spectra")

    except Exception as e:
        print(f"✗ {source}: {str(e)}")
        errors.append({'source': source, 'error': str(e)})

print()
print(f"Successfully loaded: {len(results)}/{len(sources)}")

# Save summary
summary_data = []
for src, data in results.items():
    summary_data.append({
        'source': src,
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

    code = generate_irsa_setup()

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
        errors.append({'source': source, 'error': str(e)})

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
    code = generate_irsa_setup()

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
