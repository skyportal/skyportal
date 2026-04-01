# SkyPortal MCP Tools Reference

Quick reference for all available MCP tools. For detailed API endpoint documentation, see `api_info` resource.

---

## 📋 User Interaction Guidelines

Some tools benefit from asking the user for preferences before execution. Below are tools that should prompt for user input:

### When to Prompt Users

1. **`get_tns_summary`** - After generating summary, ask what additional information they need (discovery context, follow-up plans, references, etc.). Display output in markdown text block (```text).

2. **`analyze_light_curve`** and **`analyze_color_evolution`** - Generate Jupyter notebooks by default:

   - **analyze_color_evolution:** Generates CSV data + Jupyter notebook with BOTH matched (day-to-day) AND interpolated (rolling) colors overlaid
   - **analyze_light_curve:** Generates CSV data + Jupyter notebook with light curve analysis
   - Both support `output_format="text"` for quick summaries in chat
   - **Default behavior:** Create interactive notebooks - no prompting needed unless user explicitly wants text-only

3. **`get_source_observability`** - If multiple telescopes available and user doesn't specify, ask which telescope they want to use or offer to check all.

4. **`filter_candidates`** - For broad queries, consider asking if they want to narrow filters (date range, classification, etc.).

---

## ⭐ Most Commonly Used Tools

### TNS/AstroNote Reports

- **`get_tns_summary(source_name)`** - ONE tool for complete TNS reports
  - Use this instead of calling photometry/spectra/classifications separately
  - Returns formatted summary ready for TNS submission or AstroNotes
  - **After calling:** Display output in markdown text block and ask what additional info user needs (discovery context, follow-up plans, comparison to similar events, references, special notes)

### Source Data Retrieval

- **`get_source_photometry(source_name, format, magsys, filters)`** - Light curve data as CSV
- **`get_source_spectra(source_name, format)`** - Spectroscopic data
- **`get_source_classifications(source_name)`** - Classification history
- **`get_source_host_galaxy(source_name)`** - Host galaxy information

**Note:** All source tools accept flexible identifiers (obj_id, ZTF name, or TNS name)

---

## Analysis Tools

### Light Curve Analysis

- **`analyze_light_curve(source_name, filter_names, baseline_threshold, output_format)`**
  - Multi-band analysis: rise time, fade time, duration per filter
  - Rise/fade rates (mag/day)
  - Pre-peak variability and flare detection
  - Handles incomplete light curves (still rising/fading)
  - Default filters: "ztfg,ztfr" (comma-separated, pulls both g and r band)
  - **Output modes:**
    - `output_format="notebook"` (default): Generates CSV file + Jupyter notebook
      - CSV contains all requested bands (filter, mjd, mag, magerr)
      - Notebook includes editable analysis code cells and interactive Plotly plots
      - All bands overlaid on one plot with SkyPortal colors
    - `output_format="text"`: Text summary with per-band metrics

### Color Analysis

- **`analyze_color_evolution(source_name, band1, band2, max_time_gap, max_data_gap, output_format)`**
  - Color at peak brightness and evolution over time
  - **Calculates BOTH methods automatically:**
    - **Matched** (day-to-day): Pairs close observations, respects data gaps. Best for sparse sampling.
    - **Interpolated** (rolling): Continuous color using interpolation. Best for well-sampled light curves.
  - **Output modes:**
    - `output_format="notebook"` (default): Generates CSV file + Jupyter notebook with overlaid plots
      - CSV contains both matched and interpolated colors
      - Notebook shows both methods overlaid (matched=darker, interpolated=lighter)
    - `output_format="text"`: Text summary in chat
  - Default: g-r color with both methods
  - **Files generated:** `{source}_color_data.csv` and `{source}_color_analysis.ipynb` in `{source}_color_analysis/` directory

---

## Candidate Filtering & Scanning

**Note on Alert-Time Filters**: Fritz now recommends using [MongoDB Compass](https://github.com/fritz-marshal/fritz/blob/main/doc/filter_tutorial.md) for developing alert-time filters. The MCP tools below can generate filter templates compatible with this workflow.

### Filtering Tools

- **`filter_candidates(...)`** - Query candidates with detailed filters

  - Date ranges, classification, redshift, coordinates
  - Magnitude, RB score, spatial searches
  - Returns paginated results
  - See `candidate_filter_reference` resource for all parameters

- **`generate_watchlist_filter(targets, max_distance_arcsec, filter_name)`**
  - Creates MongoDB aggregation pipeline for position monitoring
  - Takes JSON list of coordinates (name, RA, Dec)
  - Returns MongoDB pipeline compatible with Fritz filters
  - **Recommended**: Use with [MongoDB Compass workflow](https://github.com/fritz-marshal/fritz/blob/main/doc/filter_tutorial.md)
  - Can be used as starting point or imported directly

### Filter Documentation

- **`get_candidate_filter_reference()`** - Complete parameter guide
  - All available filter parameters
  - Watchlist setup instructions
  - Examples for common queries

---

## Bulk Analysis & ztfquery

**⚠️ Important:** These tools generate Python code for users to run locally in Jupyter notebooks.
They do NOT execute queries directly. The generated code uses `ztfquery` for efficient bulk operations.

**Setup Required:**

- Install ztfquery: `pip install ztfquery`
- Configure IRSA credentials (first time): `ztfquery.io.set_account('username', 'password')`
- Get IRSA account: https://irsa.ipac.caltech.edu/account/signon/login.do

### Bulk Photometry

- **`generate_bulk_lightcurve_code(sources, filters, include_plots)`**
  - Generates a Jupyter notebook to bulk download ZTF **alert photometry** from Fritz
  - Uses `ztfquery.fritz.bulk_download()` with multiprocessing
  - Sources: comma-separated or JSON array of ZTF names
  - Filters: ztfg, ztfr, ztfi (comma-separated)
  - Saves per-source CSVs + interactive Plotly plots
  - Requires: ztfquery + Fritz API token. Setup: `from ztfquery.io import set_account; set_account('fritz', token_based=True)`
  - **Note:** Downloads alert photometry (detection epochs only).
    For forced photometry (non-detections/upper limits), use IRSA.
  - Example: `sources="ZTF21aaaaaaa,ZTF21aaaaaab"` → notebook in `ztf_lightcurves/`

### Coordinate Searches

- **`generate_cone_search_code(coordinates, radius_arcsec)`**
  - Generate code to search ZTF detections near coordinates
  - Coordinates: "ra1,dec1,ra2,dec2,..." or JSON: [[ra1,dec1], [ra2,dec2]]
  - RA/Dec in decimal degrees (J2000)
  - Returns all ZTF detections within radius
  - Use case: Cross-match catalog with ZTF

### Fritz Bulk Queries

- **`generate_fritz_bulk_query_code(sources, include_spectra)`**
  - Generate code to bulk download from Fritz API
  - Downloads photometry, spectra, metadata for multiple sources
  - Requires Fritz token. Setup: `from ztfquery.io import set_account; set_account('fritz', token_based=True)`
  - Faster than individual API calls

### Alert Packets

- **`generate_alert_download_code(sources, with_cutouts)`**
  - Generate code to download raw ZTF alert packets
  - Includes full alert history + optional FITS cutouts
  - Use case: Need alert-level data not in forced photometry

### Field Visualization

- **`generate_field_visualization_code(field_id, ccd_id)`**
  - Generate code to visualize ZTF field/CCD coverage
  - Creates Mollweide sky map with footprints
  - Optional: highlight specific CCD (1-16)

---

## Observability & Planning

### Target Observability

- **`get_source_observability(source_id, ra, dec, max_airmass, telescopes, date)`**
  - Compute observing windows from specified telescopes
  - Returns rise/set times, transit, peak altitude, airmass
  - Accepts source_id (auto-resolves coords) or explicit ra/dec
  - Built-in telescopes: Keck, Lick, Palomar, APO, CTIO, Gemini-N/S, VLT, Subaru, LDT, LCO sites
  - Can query Fritz for all configured telescopes with `telescopes="fritz"`

---

## Astronomical Utilities

### Time Conversion

- **`convert_time(value, from_format, to_format)`**
  - Convert between MJD, JD, ISO datetime, and Unix timestamps
  - Formats: "mjd", "jd", "iso", "unix", or "auto" (detects automatically)
  - Example: MJD → ISO date

### External Survey Links

- **`get_survey_urls(ra, dec, obj_id)`**
  - 15+ survey links (SIMBAD, NED, VizieR, etc.)
  - Finding charts, catalogs, archives
  - TNS, ALeRCE, ATLAS, ZTF (IRSA), etc.

---

## Tool Categories

### By Use Case

**TNS Reporting:**

- `get_tns_summary` ⭐ (use this one!)

**Follow-up Planning:**

- `get_source_observability`

**Candidate Review:**

- `filter_candidates`
- `get_candidate_filter_reference`
- `generate_watchlist_filter`

**Source Investigation:**

- `get_source_photometry`
- `get_source_spectra`
- `get_source_classifications`
- `get_source_host_galaxy`
- `get_source_comments_and_annotations`

**Scientific Analysis:**

- `analyze_light_curve`
- `analyze_color_evolution`

**Context & Cross-matching:**

- `get_survey_urls`
- `search_sources_near_position`

**Bulk Operations (ztfquery code generation):**

- `generate_bulk_lightcurve_code` ⭐ (alert photometry for many sources via Fritz)
- `generate_cone_search_code` (cross-match coordinates)
- `generate_fritz_bulk_query_code` (bulk Fritz downloads)
- `generate_alert_download_code` (alert packets)
- `generate_field_visualization_code` (ZTF field maps)

---

## Common Workflows

### 1. Review and Classify a Candidate

```
1. filter_candidates(saved_after="2024-01-01", num_per_page=50)
2. get_source_photometry(source_name="ZTF21...", filters="ztfg,ztfr")
3. analyze_light_curve(source_name="ZTF21...", filter_name="ztfr")
4. get_survey_urls(obj_id="ZTF21...")
5. get_source_spectra(source_name="ZTF21...")
```

### 2. Prepare TNS Report

```
1. get_tns_summary(source_name="ZTF21...")  # ONE tool!
2. (Claude asks for additional context)
```

### 3. Plan Tonight's Observations

```
1. get_source_observability(source_id="ZTF21...", telescopes="Keck,Palomar")
2. (Check multiple telescopes for best observing window)
3. (Use Fritz UI for detailed observing run planning)
```

### 4. Monitor TNS Targets

```
1. (Prepare JSON list of coordinates from TNS)
2. generate_watchlist_filter(targets="<JSON>", max_distance_arcsec=2.0)
3. (Option A) Import JSON to MongoDB Compass for testing/refinement
4. (Option B) Import JSON directly to Fritz
5. See: https://github.com/fritz-marshal/fritz/blob/main/doc/filter_tutorial.md
```

### 5. Analyze Transient Evolution

```
1. analyze_light_curve(source_name="ZTF21...", filter_name="ztfr")
2. analyze_color_evolution(source_name="ZTF21...", band1="ztfg", band2="ztfr")
3. get_source_classifications(source_name="ZTF21...")
```

### 6. Bulk Download Photometry (>10 sources)

```
1. generate_bulk_lightcurve_code(sources="ZTF21aaa,ZTF21aab,...", filters="ztfg,ztfr")
2. (Notebook saved to ztf_lightcurves/bulk_lightcurve_download.ipynb)
3. (User opens notebook and runs cells — downloads from Fritz via ztfquery)
4. (Per-source CSVs + interactive Plotly plots saved to ztf_lightcurves/)
```

### 7. Cross-Match Catalog with ZTF

```
1. (User has list of RA/Dec coordinates from catalog/TNS)
2. generate_cone_search_code(coordinates="150.0,2.5,151.2,3.1,...", radius_arcsec=2.0)
3. (Claude inserts code into notebook)
4. (User runs to find all ZTF detections near coordinates)
```

### 8. Download Complete Alert History

```
1. generate_alert_download_code(sources="ZTF21aaa,ZTF21aab", with_cutouts=True)
2. (Claude inserts code into notebook)
3. (User runs to download alert packets + FITS cutouts)
4. (Results saved to ztf_alerts/ directory)
```

---

## Important Notes

### Source Identifiers

All `source_name` parameters accept:

- SkyPortal obj_id (e.g., `"ZTF21aaaaaaa"`)
- ZTF names (e.g., `"ZTF21aaaaaaa"`)
- TNS names (e.g., `"AT2021abc"`, `"SN2021xyz"`)

The tools automatically resolve to the correct SkyPortal source.

### Rate Limits & Bulk Operations

- MCP tools respect SkyPortal API rate limits
- For <5 sources: Use individual tools (get_source_photometry, etc.)
- For >10 sources: Use bulk analysis tools (generate_bulk_lightcurve_code, etc.)
- Bulk tools generate ztfquery code that runs locally - much faster than API calls

### Error Handling

- All tools return descriptive error messages
- Common errors:
  - Source not found → Check identifier spelling
  - No photometry → Source may not have data in that filter
  - Permission denied → Check group access

---

## Resources

In addition to tools, these resources are available:

- **`api_info`** - SkyPortal API endpoint reference
- **`candidate_filter_reference`** - Candidate filter parameter guide
- **`tools_reference`** - This document

Use these for understanding the SkyPortal data model and available operations.
