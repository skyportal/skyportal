# SkyPortal MCP Tools Reference

Quick reference for all available MCP tools. For detailed API endpoint documentation, see `api_info` resource.

---

## 📋 User Interaction Guidelines

Some tools benefit from asking the user for preferences before execution. Below are tools that should prompt for user input:

### When to Prompt Users

1. **`get_tns_summary`** - After generating summary, ask what additional information they need (discovery context, follow-up plans, references, etc.). Display output in markdown text block (```text).

2. **`analyze_light_curve`** and **`analyze_color_evolution`** - ALWAYS prompt before calling:

   - **For analyze_color_evolution:** Ask TWO questions:
     1. Method: "Would you like day-to-day colors (matched) or rolling/continuous colors (interpolated)?"
     2. Output: "Would you like the analysis as text in chat or an interactive plot in a notebook?"
   - **For analyze_light_curve:** Ask ONE question:
     - Output: "Would you like the analysis as text in chat or an interactive plot in a notebook?"

   **IMPORTANT:** Claude Code and Claude Desktop cannot display images in chat. Make this clear when prompting:

   - Text mode: Results shown directly in chat
   - Notebook mode: Python code inserted into notebook cell for user to run and see plots

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

- **`analyze_light_curve(source_name, filter_name, baseline_threshold, output_format)`**
  - Rise time, fade time, duration
  - Rise/fade rates (mag/day)
  - Pre-peak variability and flare detection
  - Handles incomplete light curves (still rising/fading)
  - Default filter: ztfr
  - **Dual output modes:**
    - `output_format="text"` (default): Text summary in chat
    - `output_format="notebook"`: Python code with interactive plot for Jupyter notebook
  - **ALWAYS prompt user** for output preference before calling

### Color Analysis

- **`analyze_color_evolution(source_name, band1, band2, method, max_time_gap, max_data_gap, output_format)`**
  - Color at peak brightness
  - Color evolution over time
  - **Two calculation methods:**
    - `"matched"` (default): Pairs close observations, respects data gaps. Best for sparse sampling.
    - `"interpolated"`: Continuous/rolling color using interpolation. Best for well-sampled light curves.
  - **Dual output modes:**
    - `output_format="text"` (default): Text summary with CSV table in chat
    - `output_format="notebook"`: Python code with interactive plots (light curves + color) for Jupyter notebook
  - Default: g-r color using matched method
  - **ALWAYS prompt user** for method AND output preference before calling

---

## Candidate Filtering & Scanning

### Filtering Tools

- **`filter_candidates(...)`** - Query candidates with detailed filters

  - Date ranges, classification, redshift, coordinates
  - Magnitude, RB score, spatial searches
  - Returns paginated results
  - See `candidate_filter_reference` resource for all parameters

- **`generate_watchlist_filter(targets, max_distance_arcsec, filter_name)`**
  - Creates MongoDB filter for TNS position monitoring
  - Takes CSV of coordinates (name, RA, Dec)
  - Returns JSON ready for Fritz UI

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
  - Generate code to download ZTF forced photometry for multiple sources
  - Sources: comma-separated or JSON array of ZTF names
  - Filters: ztfg, ztfr, ztfi (comma-separated)
  - Creates CSV files + optional plots
  - Example: `sources="ZTF21aaaaaaa,ZTF21aaaaaab"` → downloads g/r/i photometry

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
  - Requires Fritz token (set as FRITZ_TOKEN env var)
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

- **`get_source_observability(source_name, telescope_name)`**

  - Tonight's observable windows
  - Best observation time
  - Alt/az at midnight
  - Handles multiple telescopes

- **`list_available_telescopes()`** - Show configured telescopes
  - Name, location, elevation
  - Available for observability queries

### Follow-up Management

- **`list_followup_requests(obj_id, status)`** - View follow-up requests
- **`get_assigned_sources(run_id)`** - Sources in observing run
- **`get_observation_plan(run_id)`** - Tonight's observing plan

---

## Astronomical Utilities

### Time Conversion

- **`convert_time(time_value, input_format, output_format)`**
  - Formats: MJD, JD, ISO, Unix
  - Example: MJD → ISO date

### Coordinate Tools

- **`calculate_sky_distance(ra1, dec1, ra2, dec2)`**
  - Spherical distance between coordinates
  - Returns arcseconds and degrees

### External Survey Links

- **`get_survey_urls(ra, dec, obj_id)`**
  - 15+ survey links (SIMBAD, NED, VizieR, etc.)
  - Finding charts, catalogs, archives
  - TNS, ALeRCE, ATLAS, etc.

### ZTF Image Access

- **`get_ztf_cutout_urls(ra, dec, size, filters, num_days)`**
  - IRSA cutout service links
  - Direct FITS download URLs
  - Science, reference, difference images

---

## Group & Permission Management

- **`list_groups()`** - Show groups user can access
- **`get_user_info()`** - Current user details and permissions

---

## Tool Categories

### By Use Case

**TNS Reporting:**

- `get_tns_summary` ⭐ (use this one!)

**Follow-up Planning:**

- `get_source_observability`
- `list_available_telescopes`
- `get_observation_plan`

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
- `get_ztf_cutout_urls`
- `calculate_sky_distance`

**Bulk Operations (ztfquery code generation):**

- `generate_bulk_lightcurve_code` ⭐ (photometry for many sources)
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
1. list_available_telescopes()
2. get_source_observability(source_name="ZTF21...", telescope_name="P60")
3. get_observation_plan(run_id=123)
```

### 4. Monitor TNS Targets

```
1. (Prepare CSV of coordinates from TNS)
2. generate_watchlist_filter(targets="<CSV>", max_distance_arcsec=2.0)
3. (Copy JSON into Fritz filter UI)
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
2. (Claude inserts code into notebook)
3. (User runs code locally - faster than individual queries)
4. (Results saved to ztf_lightcurves/ directory)
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
