# MCP Server

SkyPortal includes an [MCP (Model Context Protocol)](https://modelcontextprotocol.io) server that lets AI assistants like Claude interact with SkyPortal on your behalf. Each user authenticates with their own SkyPortal API token, so data access is fully scoped per user.

---

## For Users

### Getting Your API Token

1. Log in to SkyPortal and click your username in the top-right corner to open your profile.
2. Scroll down to the **API Token** section.
3. If no token exists, click **Create New Token**, give it a name, and select the permissions you need.
4. Copy the token — it is a UUID string (e.g. `a1b2c3d4-e5f6-7890-abcd-ef1234567890`).

Keep your token private. It grants the same data access as your SkyPortal account.

---

### Connecting to the MCP Server

The MCP server supports two transport modes:
- **HTTP mode** (default): For production deployments - multi-user, runs as a web server
- **stdio mode**: For local development - single-user, runs as a subprocess

Choose the setup that matches your use case:

#### Option 1: Remote Production Server (HTTP mode)

**For Claude Desktop** - edit `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "skyportal": {
      "command": "npx",
      "args": [
        "-y",
        "mcp-remote",
        "https://your-skyportal-host/mcp",
        "--header",
        "Authorization:${AUTH_HEADER}"
      ],
      "env": {
        "AUTH_HEADER": "Bearer your-api-token-here"
      }
    }
  }
}
```

**For Claude Code:**

```bash
claude mcp add --transport http skyportal https://your-skyportal-host/mcp \
  --header "Authorization: Bearer your-api-token-here"
```

Verify it was added:

```bash
claude mcp list
```

Replace `your-skyportal-host` with your instance URL (e.g., `fritz.science`, `localhost:8000`) and `your-api-token-here` with your API token.

**Requires:** Node.js for `npx` (Claude Desktop only). Restart Claude Desktop after config changes.

#### Option 2: Local Development (stdio mode)

Run the MCP server locally as a subprocess - perfect for testing new tools or connecting to a remote SkyPortal API.

**For Claude Desktop** - edit `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "skyportal-dev": {
      "command": "python",
      "args": ["-m", "services.mcp_server"],
      "cwd": "/path/to/skyportal",
      "env": {
        "MCP_TRANSPORT": "stdio",
        "SKYPORTAL_URL": "https://fritz.science",
        "SKYPORTAL_TOKEN": "your-api-token-here"
      }
    }
  }
}
```

**For Claude Code** - use the CLI command:

```bash
claude mcp add --transport stdio fritz-dev \
  -e MCP_TRANSPORT=stdio \
  -e SKYPORTAL_URL=https://fritz.science \
  -e SKYPORTAL_TOKEN=your-api-token-here \
  -- /path/to/skyportal/skyportal_env/bin/python -m services.mcp_server
```

Replace:
- `/path/to/skyportal` with your local SkyPortal directory (in the Python path)
- `SKYPORTAL_URL` with the API endpoint (remote: `https://fritz.science`, local: `http://localhost:5001`)
- `SKYPORTAL_TOKEN` with your API token

Verify it was added:

```bash
claude mcp list
```

The CLI command will automatically add the configuration to `~/.claude.json` (local project config)

**Use cases for stdio mode:**
- Testing new MCP tools before deploying
- Developing locally against Fritz/production data
- Running your fork with custom tools
- No need to deploy a server

**Important:** In stdio mode, the token is hardcoded in your config file. This is fine for local dev, but never commit configs with tokens!

---

### Claude Desktop vs Claude Code

Both clients connect to the same MCP server, but they're suited for different workflows:

| | Claude Desktop | Claude Code |
|---|---|---|
| **Best for** | Conversational queries, browsing data, quick lookups | Data analysis, writing code, multi-step workflows |
| **Interface** | Chat window in the app | Terminal / IDE integration |
| **Example tasks** | "Show me recent candidates classified as SNe Ia", "When can I observe this source from Keck?", "Get survey links for this position" | "Write a script to compute g-r colors for all sources in group 5", "Fit a light curve model to this source's photometry", "Build a candidate filter for fast-rising blue transients" |
| **Strengths** | Easy to use, good for exploration and planning | Can read/write files, run code, iterate on analysis |

**Rule of thumb:** Use Desktop for asking questions and getting information. Use Code when you need the AI to write and execute analysis code on your data.

---

### Available Tools

#### `call_skyportal_api`

General-purpose tool for querying the SkyPortal API.

| Parameter | Type | Description |
|-----------|------|-------------|
| `endpoint` | `str` | API path, e.g. `/api/sources` |
| `method` | `str` | `GET`, `POST`, `PUT`, or `DELETE` (default: `GET`) |
| `params` | `dict` | URL query parameters (optional) |
| `data` | `dict` | Request body for POST/PUT (optional) |

**Example prompts:**
- *"Show me sources saved in the last 7 days"*
- *"Get the photometry for source ZTF21aaaaaaa"*
- *"List all candidates in group 5 classified as SNe Ia"*

**Note:** All source-specific tools accept flexible source identifiers - you can use SkyPortal obj_id, ZTF names, or TNS names interchangeably.

#### `get_tns_summary`

⭐ **USE THIS SINGLE TOOL** when creating TNS reports or AstroNotes - it combines all relevant data in one call.

Generate a comprehensive summary for TNS (Transient Name Server) reports or AstroNote submissions. Includes discovery info, photometry, classification, spectroscopy, and host galaxy data formatted for easy copy-paste.

| Parameter | Type | Description |
|-----------|------|-------------|
| `source_name` | `str` | Source identifier - SkyPortal obj_id, ZTF name, or TNS name |

**Returns:** Formatted text summary with:
- Source identification (coordinates in decimal and sexagesimal)
- Discovery information (first detection date, mag, instrument)
- Latest photometry and peak magnitude (⚠️ peak = min(mag), not from light curve fit)
- Classifications and probabilities
- Spectroscopy and redshift measurements
- Host galaxy offset

**Example prompts:**
- *"Generate a TNS summary for ZTF21aaaaaaa"*
- *"Create an AstroNote summary for AT2024xyz"*
- *"Give me a report summary for this source"*
- *"Write a TNS classification report for SN2024abc"*

**After generating the summary, Claude should ask:**
> "I've generated the TNS summary. What additional information do you need for your report?"
>
> Common additions:
> - **Discovery context:** Was this from a targeted survey? Any non-detections before discovery?
> - **Follow-up plans:** Are you requesting spectroscopy or additional photometry?
> - **Comparison:** Similar to any known events? Anything unusual?
> - **References:** Any papers, ATels, or GCN circulars to cite?
> - **Notes:** Special observing conditions, calibration issues, or caveats?

---

### Analysis Tools

#### `analyze_light_curve`

Analyze light curve evolution including rise/fade times, duration, and variability.

| Parameter | Type | Description |
|-----------|------|-------------|
| `source_name` | `str` | Source identifier - SkyPortal obj_id, ZTF name, or TNS name |
| `filter_name` | `str` | Photometric filter to analyze (default: "ztfr") |
| `baseline_threshold` | `float` | Mag difference from peak to consider "baseline" (default: 0.3) |
| `output_format` | `str` | `"text"` for chat summary or `"notebook"` for interactive plot (default: "text") |

**Dual output modes:**
1. **Text mode** (`output_format="text"`): Returns formatted text summary directly in chat
2. **Notebook mode** (`output_format="notebook"`): Returns Python code that Claude Code inserts into a notebook cell for the user to run

**Important:** Claude should ALWAYS prompt the user before calling: *"Would you like the analysis as (1) text summary in chat, or (2) interactive plot in a notebook?"*

**Note:** Claude Code and Claude Desktop cannot display images in chat. When prompting, make this clear:
- Text mode: Results shown directly in chat
- Notebook mode: Code inserted into notebook cell for user to run and see plots

**Returns (text mode):** Formatted summary with:
- Peak magnitude and time
- Rise time (first detection to peak) and rate (mag/day)
- Fade time (peak to baseline or current) and rate
- Total duration (rise + fade if light curve complete)
- Pre-peak variability metrics and early flare detection
- Status (still rising, still fading, or complete)

**Returns (notebook mode):** Python code with:
- Embedded photometry data (mjd, mag, magerr arrays)
- Interactive matplotlib plot with peak marked
- Printed analysis results (same as text mode)
- Ready to run in a notebook cell

**Handles incomplete light curves:**
- Still rising: Reports time from first detection to current
- Still fading: Reports time from peak to current
- Returned to baseline: Reports complete rise + fade times

**Example prompts:**
- *"Analyze the light curve for ZTF21aaaaaaa"*
- *"Calculate rise and fade times for AT2024abc"*
- *"Check for early flares in the r-band light curve"*
- *"Plot the light curve analysis for this source"*

#### `analyze_color_evolution`

Analyze color evolution and color at peak brightness using matched or interpolated methods.

| Parameter | Type | Description |
|-----------|------|-------------|
| `source_name` | `str` | Source identifier - SkyPortal obj_id, ZTF name, or TNS name |
| `band1` | `str` | First photometric filter (default: "ztfg") |
| `band2` | `str` | Second photometric filter (default: "ztfr") |
| `method` | `str` | "matched" (default) or "interpolated" |
| `max_time_gap` | `float` | Max time difference to pair observations (default: 0.5 days) |
| `max_data_gap` | `float` | Max gap to avoid spurious colors (default: 3.0 days) |
| `output_format` | `str` | `"text"` for chat summary or `"notebook"` for interactive plots (default: "text") |

**Dual output modes:**
1. **Text mode** (`output_format="text"`): Returns formatted text summary with CSV table
2. **Notebook mode** (`output_format="notebook"`): Returns Python code with interactive plots (light curves + color evolution)

**Important:** Claude should ALWAYS prompt the user TWO questions before calling:
1. *"Would you like day-to-day colors (matched method) or rolling/continuous colors (interpolated method)?"*
2. *"Would you like the analysis as text in chat or interactive plot in notebook?"*

**Returns (text mode):** Formatted summary with:
- Color at peak brightness in each band
- Color evolution statistics (mean, range, trend)
- CSV table of color measurements with uncertainties
- Method used and parameters

**Returns (notebook mode):** Python code with:
- Embedded photometry data for both bands
- Two-panel interactive plot: light curves (top) + color evolution (bottom)
- Color at peak and mean color marked on plot
- Printed analysis results (same as text mode)

**Two calculation methods:**
1. **Matched** (`method="matched"`): Pairs observations from each band that are close in time, but avoids calculating colors across large gaps in the data. More conservative, respects observing gaps.
2. **Interpolated** (`method="interpolated"`): Interpolates one band to match the other's observation times, creating continuous color measurements. More measurements but assumes smooth evolution.

**Example prompts:**
- *"Calculate g-r color evolution for ZTF21aaaaaaa"*
- *"What was the color at peak for this transient?"*
- *"Show me interpolated color evolution in g and r bands"*
- *"Plot the color evolution with matched observations"*

---

### Bulk Analysis Tools (ztfquery)

**Important:** These tools generate Python code for users to run locally in Jupyter notebooks. They do NOT execute queries directly. The generated code uses [`ztfquery`](https://github.com/MickaelRigault/ztfquery) for efficient bulk operations.

**Why code generation instead of direct execution?**
- Bulk queries can be slow - better to run locally where users can monitor progress
- Users can customize the generated code for their specific needs
- ztfquery has its own authentication system (IRSA credentials)
- Provides better performance and flexibility for large-scale data operations

**Prerequisites:**
1. Install ztfquery: `pip install ztfquery`
2. Configure IRSA credentials (first time only):
   ```python
   from ztfquery import io
   io.set_account('your_irsa_username', 'your_irsa_password')
   ```
3. Get IRSA account at: https://irsa.ipac.caltech.edu/account/signon/login.do

**Output Handling:**
When a user asks for bulk analysis, Claude Code will:
1. Call the appropriate bulk tool
2. Receive Python code as the result
3. Automatically insert the code into a new notebook cell (or create a new notebook)
4. User runs the cell to execute the bulk operation locally

#### `generate_bulk_lightcurve_code`

Generate Python code to bulk download ZTF forced photometry using ztfquery.

| Parameter | Type | Description |
|-----------|------|-------------|
| `sources` | `str` | Comma-separated list of ZTF source names, or JSON array (e.g., `"ZTF24aaaaaaa,ZTF24aaaaaab"` or `'["ZTF24aaaaaaa", "ZTF24aaaaaab"]'`) |
| `filters` | `str` | Comma-separated filter names (default: `"ztfg,ztfr,ztfi"`) |
| `include_plots` | `bool` | Generate light curve plots (default: `True`) |

**Returns:** Python code that:
- Creates a `ztf_lightcurves/` directory with results
- Saves individual light curves as CSV files
- Creates `summary.csv` with statistics
- Generates plots in `ztf_lightcurves/plots/` if requested
- Includes progress tracking (tqdm) and error handling

**Example prompts:**
- *"Download photometry for 50 ZTF sources: [list of sources]"*
- *"I need light curves for all sources in this list"*
- *"Bulk download g and r band photometry for these transients"*

#### `generate_cone_search_code`

Generate code to perform ZTF cone searches at multiple sky positions.

| Parameter | Type | Description |
|-----------|------|-------------|
| `coordinates` | `str` | Comma-separated "RA,Dec" pairs or JSON array of [RA, Dec]. RA/Dec in decimal degrees (J2000). Examples: `"150.0,2.5,151.2,3.1"` or `'[[150.0, 2.5], [151.2, 3.1]]'` |
| `radius_arcsec` | `float` | Search radius in arcseconds (default: 2.0) |

**Returns:** Python code that:
- Performs cone search at each position
- Saves all detections to `ztf_cone_search/cone_search_results.csv`
- Creates summary with detection counts per position
- Includes query coordinates for cross-reference

**Use case:** Cross-matching catalogs (TNS, Gaia, etc.) with ZTF to find detections near known positions.

**Example prompts:**
- *"Search for ZTF detections near these coordinates: [list]"*
- *"I have a catalog of 100 positions - check which have ZTF coverage"*
- *"Cross-match this TNS list with ZTF"*

#### `generate_fritz_bulk_query_code`

Generate code to bulk query Fritz/SkyPortal for multiple sources using ztfquery's Fritz interface.

| Parameter | Type | Description |
|-----------|------|-------------|
| `sources` | `str` | Comma-separated source names or JSON array |
| `include_spectra` | `bool` | Download spectra in addition to photometry (default: `True`) |

**Returns:** Python code that:
- Queries Fritz API for each source
- Downloads photometry and (optionally) spectra
- Saves individual files: `{source}_photometry.csv`, `{source}_spectra.csv`
- Creates summary with redshifts, classifications, data counts
- Saves to `fritz_data/` directory

**Note:** Requires Fritz API token. Users should set `FRITZ_TOKEN` environment variable or edit the generated code.

**Example prompts:**
- *"Download Fritz data for these 20 sources"*
- *"Bulk query photometry and spectra from Fritz for my source list"*

#### `generate_alert_download_code`

Generate code to download ZTF alert packets for multiple sources.

| Parameter | Type | Description |
|-----------|------|-------------|
| `sources` | `str` | Comma-separated ZTF source names or JSON array |
| `with_cutouts` | `bool` | Download cutout images (science, ref, diff) (default: `True`) |

**Returns:** Python code that:
- Downloads alert packets for each source
- Saves alerts as JSON files
- Optionally downloads FITS cutouts
- Saves to `ztf_alerts/` and `ztf_alerts/cutouts/` directories

**Use case:** When you need complete alert history or alert-level data not available in forced photometry.

**Example prompts:**
- *"Download all alert packets for these sources"*
- *"I need the raw ZTF alerts with cutouts for this list"*

#### `generate_field_visualization_code`

Generate code to visualize ZTF field and CCD coverage.

| Parameter | Type | Description |
|-----------|------|-------------|
| `field_id` | `int` | ZTF field ID (1-1895) |
| `ccd_id` | `int` or `None` | Optional CCD ID to highlight (1-16) |

**Returns:** Python code that:
- Creates Mollweide projection sky map
- Shows field footprint on sky
- Highlights specific CCD if requested
- Displays RA/Dec coverage information

**Example prompts:**
- *"Show me ZTF field 300's sky coverage"*
- *"Visualize field 450 with CCD 12 highlighted"*
- *"Map the footprint of this ZTF field"*

---

### Source Data Tools

#### `get_source_photometry`

Retrieve photometry for a source as a CSV table. Returns all photometry points sorted by MJD, ready for analysis or loading into a pandas DataFrame.

| Parameter | Type | Description |
|-----------|------|-------------|
| `source_id` | `str` | Source/object ID (e.g., `ZTF21aaaaaaa`) |
| `format` | `str` | `"mag"` (default) or `"flux"` |
| `magsys` | `str` | Magnitude system: `"ab"` (default), `"vega"`, etc. |
| `filters` | `str` | Comma-separated filter names to include (optional, e.g., `"ztfg,ztfr"`) |

**Example prompts:**
- *"Get the light curve for ZTF21aaaaaaa"*
- *"Show me the g-band and r-band photometry for source ZTF22abcdefg"*
- *"Save the photometry to a CSV file"* (Claude Code will write the returned data to a file)

#### `get_source_spectra`

Retrieve spectra for a source. Returns all spectra as CSV (one per block) or JSON format.

| Parameter | Type | Description |
|-----------|------|-------------|
| `source_id` | `str` | Source/object ID (e.g., `ZTF21aaaaaaa`) |
| `format` | `str` | `"csv"` (default) or `"json"` |

**Example prompts:**
- *"Get the spectra for ZTF21aaaaaaa"*
- *"Show me all spectroscopic observations of this source"*

#### `get_source_classifications`

Retrieve classifications for a source. Returns all classifications with type, probability, classifier, and date.

| Parameter | Type | Description |
|-----------|------|-------------|
| `source_id` | `str` | Source/object ID (e.g., `ZTF21aaaaaaa`) |

**Example prompts:**
- *"What is ZTF21aaaaaaa classified as?"*
- *"Show me all classifications for this source"*
- *"Has anyone classified this as a supernova?"*

#### `get_source_comments_and_annotations`

Retrieve comments and annotations for a source. Returns user comments (text notes) and system annotations (ML scores, cross-match results, etc.).

| Parameter | Type | Description |
|-----------|------|-------------|
| `source_id` | `str` | Source/object ID (e.g., `ZTF21aaaaaaa`) |

**Example prompts:**
- *"What have people said about ZTF21aaaaaaa?"*
- *"Show me the comments and ML scores for this source"*
- *"What annotations does this source have?"*

#### `get_source_host_galaxy`

Retrieve host galaxy information for a source. Returns the associated host galaxy from SkyPortal's galaxy catalogs (e.g., GLADE+), including angular separation (offset) and physical distance.

SkyPortal can link sources to host galaxies. If a host association exists, this returns the galaxy's name, position, redshift, distance, stellar mass, magnitudes, and both the angular offset (arcsec) and physical separation (kpc) from the source.

| Parameter | Type | Description |
|-----------|------|-------------|
| `source_id` | `str` | Source/object ID (e.g., `ZTF21aaaaaaa`) |

**Example prompts:**
- *"What is the host galaxy of ZTF21aaaaaaa?"*
- *"Show me the host galaxy information for this source"*
- *"How far is this source from its host galaxy?"*
- *"What galaxy is this supernova in?"*

#### `convert_time`

Convert between common astronomical time formats: MJD, JD, ISO datetime, and Unix timestamps.

| Parameter | Type | Description |
|-----------|------|-------------|
| `value` | `str` | The time value to convert |
| `from_format` | `str` | `"mjd"`, `"jd"`, `"iso"`, `"unix"`, or `"auto"` (default) |
| `to_format` | `str` | `"mjd"`, `"jd"`, `"iso"`, `"unix"`, or `"auto"` (returns all) |

**Example prompts:**
- *"Convert MJD 60400.5 to a date"*
- *"What's the MJD for 2024-06-15?"*

#### `get_survey_urls`

Get URLs to browse a sky position across common astronomical surveys (ZTF, Legacy Survey, PanSTARRS, SDSS, NED, SIMBAD, VizieR, WISE, and more). Accepts either explicit coordinates or a source ID to auto-resolve coordinates.

| Parameter | Type | Description |
|-----------|------|-------------|
| `ra` | `float` | Right ascension in decimal degrees (J2000). Not needed if `source_id` provided. |
| `dec` | `float` | Declination in decimal degrees (J2000). Not needed if `source_id` provided. |
| `source_id` | `str` | SkyPortal source ID (e.g., `ZTF21aaaaaaa`). RA/Dec resolved automatically. |

**Example prompts:**
- *"Give me survey links for RA=150.1, Dec=+2.2"*
- *"Where can I look up ZTF21aaaaaaa in other surveys?"*
- *"Show me PanSTARRS and Legacy Survey images for this source"*

#### `get_ztf_cutout_urls`

Query IRSA for ZTF science and reference image cutout URLs at a given position.

| Parameter | Type | Description |
|-----------|------|-------------|
| `ra` | `float` | Right ascension in decimal degrees (J2000) |
| `dec` | `float` | Declination in decimal degrees (J2000) |
| `size_arcmin` | `float` | Search region size in arcminutes (default: 1.0) |

**Example prompts:**
- *"Get ZTF images near RA=180.0, Dec=-5.0"*
- *"Find ZTF reference images for this source's position"*

#### `get_source_observability`

Compute observing windows for a source from specified telescopes. Returns exact time windows (rise/set), transit time, peak altitude, and airmass — in both UTC and the telescope's local time. Accepts either a source ID (auto-resolves coordinates) or explicit RA/Dec.

| Parameter | Type | Description |
|-----------|------|-------------|
| `source_id` | `str` | SkyPortal source ID (e.g., `ZTF20abwysqy`). RA/Dec resolved automatically. |
| `ra` | `float` | Right ascension in decimal degrees (not needed if `source_id` given) |
| `dec` | `float` | Declination in decimal degrees (not needed if `source_id` given) |
| `max_airmass` | `float` | Maximum airmass limit (default: 2.0) |
| `telescopes` | `str` | Comma-separated names (default: `"Keck,Palomar,Gemini-N,Gemini-S,VLT"`). Use `"all"` for all built-in telescopes or `"fritz"` to query your SkyPortal instance. |
| `date` | `str` | Date in ISO format (default: tonight) |

Built-in telescopes: Keck, Lick, Palomar, APO, CTIO, Gemini-N, Gemini-S, VLT, Subaru, LDT, LCO-COJ, LCO-ELP, LCO-LSC, LCO-OGG, LCO-CPT, LCO-TFN.

**Example prompts:**
- *"When can I observe ZTF20abwysqy from Keck tonight?"*
- *"Is this source visible from any Southern hemisphere telescope?"*
- *"Show me the observability for RA=120, Dec=+45 from all telescopes on June 15"*

#### `get_candidate_filter_reference`

Returns documentation on available query parameters for filtering candidates and sources on Fritz/SkyPortal: annotation-based ML score filters, classification filters, redshift ranges, photometry annotations, and more.

**Important**: This covers **query-time filtering** (searching existing candidates on the scanning page), NOT **alert-time filtering** (MongoDB pipelines that run when alerts arrive). If users want to create permanent alert-time filters, direct them to the Fritz UI Filters page and the filter tutorial.

No parameters — call it to load the reference into context.

**Example prompts:**
- *"How do I filter for candidates with a real/bogus score above 0.8?"*
- *"Show me how to search for Type Ia supernovae candidates"*
- *"What filters can I apply when scanning candidates?"*

**If user asks about creating alert-time filters:**
Tell them: "Alert-time filters (MongoDB pipelines) must be created in the Fritz UI. See the Filters page and tutorial at https://github.com/fritz-marshal/fritz/blob/main/doc/filter_tutorial.md. The MCP server can only search existing candidates, not create filters that process incoming alerts."

#### `filter_candidates`

Search for candidates matching specific criteria on the scanning page. This performs **query-time filtering** of existing candidates (searching what's already on the scanning page), NOT **alert-time filtering** (creating MongoDB pipelines that process incoming alerts).

**What this tool does:**
- Searches candidates already on the scanning page
- Returns CSV table with results
- Provides filter configuration JSON for saving/reuse
- Ad-hoc searches (not permanent)

**What this tool CANNOT do:**
- Create permanent alert-time filters (MongoDB pipelines)
- Access alert packet history (`prv_candidates` array)
- Process incoming alerts before they become candidates

**If user wants alert-time filters:** Direct them to the Fritz UI Filters page and tutorial: https://github.com/fritz-marshal/fritz/blob/main/doc/filter_tutorial.md

**Important**: The tool will always ask for user confirmation of filter parameters before executing, and will return the filter configuration JSON at the end.

| Parameter | Type | Description |
|-----------|------|-------------|
| `group_id` | `int` | Search within specific group ID (optional) |
| `saved_status` | `str` | Saved status: `"all"` (default), `"savedToAllSelected"`, `"savedToAnySelected"`, `"savedToAnyAccessible"`, `"notSavedToAnyAccessible"`, `"notSavedToAnySelected"`, `"notSavedToAllSelected"` |
| `classifications` | `str` | Comma-separated classifications to INCLUDE (e.g., `"SN Ia,SN Ib/c"`) |
| `classifications_reject` | `str` | Comma-separated classifications to EXCLUDE (e.g., `"AGN,varstar"`) |
| `min_redshift` | `float` | Minimum redshift |
| `max_redshift` | `float` | Maximum redshift |
| `annotation_filters` | `str` | JSON array of annotation filters for ML scores. Each filter object contains: `"origin"` (annotation source), `"key"` (score name), and `"min"`/`"max"`/`"value"` for filtering. Examples: `'[{"origin":"braai","key":"braai","min":0.9}]'` for high real/bogus score, `'[{"origin":"kowalski","key":"sgScore","max":0.3}]'` for likely galaxies, `'[{"origin":"Kowalski","key":"ACAI_score","min":0.8}]'` for TDE candidates |
| `saved_after` | `str` | Only candidates saved after this date (ISO format: `"2024-01-15"`) |
| `saved_before` | `str` | Only candidates saved before this date |
| `first_detected_after` | `str` | Only sources first detected after this date |
| `last_detected_before` | `str` | Only sources last detected before this date |
| `num_per_page` | `int` | Number of results (default 100, max 500) |
| `page_number` | `int` | Page number for pagination (default 1) |

**Example prompts:**
- *"Find SNe Ia with braai score > 0.9 saved in the last week"*
- *"Search for likely galaxy transients (sgScore < 0.3) with high real/bogus score"*
- *"Show me TDE candidates with ACAI_score > 0.8"*
- *"Find unclassified candidates saved to my group"*
- *"Search for nuclear transients: galaxies with recent detections"*

**Returns**: CSV table with obj_id, position, redshift, latest magnitude, classifications, ML scores, plus the filter configuration JSON for saving.

#### `generate_watchlist_filter`

Generate MongoDB aggregation pipeline JSON for a watchlist that monitors specific sky coordinates. This creates **alert-time filters** that run automatically on every incoming alert from the telescope.

**Important**: This is fundamentally different from `filter_candidates`:
- **`filter_candidates`**: Query-time tool that searches existing candidates (ad-hoc, runs via API)
- **`generate_watchlist_filter`**: Alert-time filter generator (permanent, runs on Kowalski backend)

**What this tool does:**
- Generates MongoDB pipeline JSON for monitoring specific coordinates
- Implements spherical distance calculation for accurate matching
- Annotates matching alerts with nearest target name and distance
- Ready to copy-paste into Fritz UI's filter creation page

**What this tool CANNOT do:**
- Create the filter directly via API (requires Fritz UI)
- MCP cannot automate filter creation — you must paste JSON manually

**Workflow:**
1. Call this tool with your target coordinates
2. Copy the generated MongoDB pipeline JSON
3. Go to Fritz UI → Filters page → Create Filter
4. Paste the JSON into the "Pipeline" field
5. Set Group and Stream for the filter
6. Save to activate monitoring

| Parameter | Type | Description |
|-----------|------|-------------|
| `targets` | `str` | JSON array of target objects. Each must have `"name"`, `"ra"` (decimal degrees), and `"dec"` (decimal degrees). Example: `'[{"name":"M31","ra":10.6847,"dec":41.2687},{"name":"Crab","ra":83.6333,"dec":22.0145}]'` |
| `max_distance_arcsec` | `float` | Maximum angular separation for a match (default: 2.0 arcsec, typical for known sources) |
| `filter_name` | `str` | Name for this watchlist filter (for documentation, default: "Watchlist") |

**Example prompts:**
- *"Create a watchlist filter for M31 and the Crab Nebula with 2 arcsec radius"*
- *"Generate a watchlist monitoring NGC1234 at RA=50.0, Dec=+10.0"*
- *"Make a filter to watch these three positions: [list coordinates]"*
- *"I want alerts whenever new detections appear near RA=123.456, Dec=-12.345"*

**Returns**: MongoDB aggregation pipeline JSON with instructions, ready to paste into Fritz filter UI. Includes human-readable summary of watched positions and annotations that will be added to matching alerts.

**Technical details**: The pipeline uses spherical trigonometry with `atan2` for accurate angular separation on the celestial sphere, converts to arcseconds, filters by distance threshold, and adds annotations for the closest watchlist target plus a list of all matching targets.

#### `search_sources_near_position`

Search for sources in SkyPortal near a sky position (cone search). Finds all sources within a specified radius. Useful for checking if a source already exists at a location, or finding nearby sources in your SkyPortal instance.

| Parameter | Type | Description |
|-----------|------|-------------|
| `ra` | `float` | Right ascension in decimal degrees (J2000). Not needed if `source_id` provided. |
| `dec` | `float` | Declination in decimal degrees (J2000). Not needed if `source_id` provided. |
| `source_id` | `str` | SkyPortal source ID (e.g., `ZTF21aaaaaaa`). RA/Dec resolved automatically. |
| `radius_arcsec` | `float` | Search radius in arcseconds (default: 10.0) |
| `num_per_page` | `int` | Maximum number of sources to return (default: 100) |

**Example prompts:**
- *"Are there any sources near RA=150.1, Dec=+2.2 within 5 arcsec?"*
- *"Show me all sources within 30 arcsec of ZTF21aaaaaaa"*
- *"Check if this position already has a source in SkyPortal"*

---

## For Developers

The server lives in `services/mcp_server/` and is built with [FastMCP](https://gofastmcp.com).

### Transport Modes

The MCP server supports two transport modes, selected via the `MCP_TRANSPORT` environment variable:

#### HTTP Mode (default, for production)

Multi-user authentication with bearer tokens. Clients send a SkyPortal API token as an `Authorization: Bearer <token>` header on every request. FastMCP's auth layer calls `SkyPortalOAuthProvider.load_access_token()`, which validates the token against SkyPortal's `/api/internal/profile` endpoint.

```
MCP Client                     MCP Server                      SkyPortal
    |                              |                               |
    |-- POST /mcp                  |                               |
    |   Authorization: Bearer ---> |-- GET /api/internal/profile ->|
    |   load_access_token() called |<- {username, id} -------------|
    |<- MCP response --------------|                               |
```

No browser-based OAuth flow is involved. The `OAuthProvider` subclass implements only the `load_access_token()` validation method; the remaining interface methods (client registration, authorize, token exchange) are stubs required by the base class.

#### stdio Mode (for local development)

Single-user mode where the server runs as a subprocess. Authentication uses the `SKYPORTAL_TOKEN` environment variable instead of per-request OAuth. Perfect for:
- Testing new tools locally
- Developing against a remote SkyPortal/Fritz instance
- Running custom forks without deploying

The token is passed via environment variables in the client config (Claude Desktop/Code JSON files).

### Deployment

The MCP server runs as a supervised process on port `ports.mcp` (default 8000) and is proxied through SkyPortal's existing nginx. This means:

- Users connect to `https://your-skyportal-host/mcp` — no separate port to expose
- HTTPS is handled by nginx, same as the rest of SkyPortal
- `MCP_BASE_URL` is derived automatically from `server.host`, `server.port`, and `server.ssl` in `config.yaml`

No extra configuration is needed for a standard deployment. If you need to override anything, the environment variables below take precedence over the config-derived defaults.

### Environment Variables

These override the values derived from SkyPortal's `config.yaml` at startup.

| Variable | Description | Default |
|----------|-------------|---------|
| `MCP_TRANSPORT` | Transport mode: `"http"` or `"stdio"` | `"http"` |
| `SKYPORTAL_URL` | Internal URL for SkyPortal's API | `http://127.0.0.1:{ports.app}` |
| `SKYPORTAL_TOKEN` | API token for stdio mode (not used in HTTP mode) | None |
| `MCP_HOST` | Bind host (HTTP mode only) | `127.0.0.1` |
| `MCP_PORT` | Listen port (HTTP mode only) | `ports.mcp` (default 8000) |
| `MCP_BASE_URL` | Public URL for OAuth metadata (HTTP mode only) | Derived from `server.host`, `server.port`, `server.ssl` |

### Adding New Tools

Decorate any async function with `@mcp.tool()`. Use `get_skyportal_token()` to retrieve the user's API token (works in both HTTP and stdio modes):

```python
from ..server import SKYPORTAL_URL, get_skyportal_token, mcp
import httpx

@mcp.tool()
async def my_new_tool(source_id: str) -> str:
    """Describe what this tool does."""
    token = get_skyportal_token()
    if not token:
        return "Not authenticated. Configure SKYPORTAL_TOKEN or send Bearer token."

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(
            f"{SKYPORTAL_URL}/api/sources/{source_id}",
            headers={"Authorization": f"token {token}"},
        )
    resp.raise_for_status()
    return str(resp.json())
```

The `get_skyportal_token()` helper automatically handles both transport modes:
- **HTTP mode**: Retrieves the per-request OAuth token from the Authorization header
- **stdio mode**: Returns the `SKYPORTAL_TOKEN` environment variable

### Running Locally for Development

#### Option 1: stdio mode (recommended for development)

Run the MCP server as a subprocess - no need to start SkyPortal. Perfect for testing new tools against Fritz or a remote instance.

**For Claude Code:**

```bash
claude mcp add --transport stdio skyportal-dev \
  -e MCP_TRANSPORT=stdio \
  -e SKYPORTAL_URL=https://fritz.science \
  -e SKYPORTAL_TOKEN=your-api-token \
  -- /path/to/skyportal/skyportal_env/bin/python -m services.mcp_server
```

**For Claude Desktop** - edit `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "skyportal-dev": {
      "command": "python",
      "args": ["-m", "services.mcp_server"],
      "cwd": "/path/to/skyportal",
      "env": {
        "MCP_TRANSPORT": "stdio",
        "SKYPORTAL_URL": "https://fritz.science",
        "SKYPORTAL_TOKEN": "your-api-token"
      }
    }
  }
}
```

#### Option 2: HTTP mode (testing full deployment)

Start SkyPortal normally — the MCP server starts automatically via supervisor on `http://localhost:8000/mcp`. Connect with Claude Code:

```bash
claude mcp add --transport http skyportal http://localhost:8000/mcp \
  --header "Authorization: Bearer your-api-token-here"
```

To run the MCP server standalone in HTTP mode (outside supervisor):

```bash
# Default: HTTP mode on localhost:8000
python -m services.mcp_server

# Custom port
MCP_PORT=9000 python -m services.mcp_server
```

The server reads `SKYPORTAL_URL`, `MCP_PORT`, and `MCP_BASE_URL` from SkyPortal's config automatically.
