# Candidate & Source Filter Reference

## Two Types of Filtering in Fritz/SkyPortal

### 1. Alert-Time Filters (MongoDB Pipelines) 🚫 Not Available via MCP

**What they do:** Run on Kowalski backend when new alerts arrive from the telescope. These filters determine which alerts become candidates visible on the scanning page.

**How they work:**

- Written as MongoDB aggregation pipelines
- Access enhanced alert packets with cross-matches, ML scores, photometric history
- Can iterate through `prv_candidates` array, compute light curve properties, etc.
- Created and managed in the **Fritz UI** (Filters page)
- Permanent, automatically process every incoming alert

**⚠️ If you want to create/modify alert-time filters:**

1. Go to the Fritz UI → Filters page
2. Follow the tutorial: https://github.com/fritz-marshal/fritz/blob/main/doc/filter_tutorial.md
3. Use MongoDB Compass to test filters: https://docs.fritz.science/user_guide.html#alert-filters-in-fritz

**MCP cannot create these filters** because they require MongoDB pipeline syntax and direct backend access.

---

### 2. Query-Time Filters (API Parameters) ✅ Available via MCP

**What they do:** Search existing candidates that are already on the scanning page. Ad-hoc searches to find candidates matching specific criteria.

**How they work:**

- Use `/api/candidates` API query parameters
- Filter by classifications, redshift, ML scores, dates, saved status
- Run on-demand when you query (not permanent)
- Results returned as JSON/CSV

**✅ Use the `filter_candidates` MCP tool to:**

- Search the scanning page for candidates
- Filter by any criteria documented below
- Get results as CSV table
- Save filter configurations for reuse

**This reference covers query-time filtering only.**

---

### Watchlists (Alert-Time Position Monitoring) ✅ MCP Can Generate

**What they are:** Alert-time filters that monitor specific sky coordinates. When new detections fall within a specified angular distance from watched positions, alerts are flagged and annotated.

**How they work:**

- MongoDB aggregation pipeline with spherical distance calculation
- Runs automatically on every incoming alert
- Annotations added: nearest target name, distance in arcseconds, list of all matches
- Permanent monitoring (unlike ad-hoc query-time searches)

**✅ Use the `generate_watchlist_filter` MCP tool to:**

- Generate the MongoDB pipeline JSON for watchlist filters
- Specify target coordinates and search radius
- Get ready-to-paste JSON for Fritz filter UI
- Monitor multiple positions with a single filter

**Important:** MCP cannot create the filter directly. The workflow is:

1. Generate JSON with `generate_watchlist_filter` tool
2. Copy the generated MongoDB pipeline
3. Paste into Fritz UI → Filters page
4. Set Group/Stream and save

**Use cases:**

- Monitor known sources for new activity (e.g., M31, Crab)
- Track specific sky positions of interest
- Get alerted when detections appear near target coordinates
- Watch multiple objects with a single filter (max distance typically 2 arcsec)

---

## Querying Candidates: GET /api/candidates

### Date & Time Filters

- `startDate` / `endDate` — when the candidate passed the filter (ISO format)
- `firstDetectionAfter` — only sources first detected after this date
- `lastDetectionBefore` — only sources last detected before this date
- `numberDetections` — minimum number of detections required
- `requireDetections` — boolean (default true)
- `excludeForcedPhotometry` — boolean, exclude forced photometry from detection counts

### Group & Filter Selection

- `groupIDs` — comma-separated group IDs to search within
- `filterIDs` — comma-separated filter IDs (alternative to groupIDs)

### Saved Status

- `savedStatus` — one of:
  - `all` (default), `savedToAllSelected`, `savedToAnySelected`,
    `savedToAnyAccessible`, `notSavedToAnyAccessible`,
    `notSavedToAnySelected`, `notSavedToAllSelected`

### Classification Filters

- `classifications` — comma-separated classification names to include
  (e.g., "SN Ia,SN Ib/c,SN II")
- `classificationsReject` — exclude candidates with these classifications

### Redshift Filters

- `minRedshift` / `maxRedshift` — redshift range

### User Lists

- `listName` — only show candidates on this user list (e.g., "favorites")
- `listNameReject` — exclude candidates on this user list (e.g., "rejected_candidates")

---

## Annotation Filters (key for ML scores)

The `annotationFilterList` parameter accepts a JSON-encoded list of filter objects.
Each object specifies an annotation origin, key, and either a value match or a min/max range.

### Format

**Range filter (for numerical scores):**

```json
{"origin": "<source>", "key": "<field>", "min": <float>, "max": <float>}
```

**Exact match filter:**

```json
{ "origin": "<source>", "key": "<field>", "value": "<value>" }
```

**Boolean filter:**

```json
{ "origin": "<source>", "key": "<field>", "value": true }
```

Multiple filters can be combined (comma-separated in the query string):

```
annotationFilterList={"origin":"braai","key":"braai","min":0.8,"max":1.0},{"origin":"kowalski","key":"sgScore","min":0.0,"max":0.5}
```

### Common Annotation Origins and Keys

**Base SkyPortal / ZTF Public:**
| Origin | Key | Range | Description |
|--------|-----|-------|-------------|
| `braai` | `braai` | 0–1 | Real/bogus score (higher = more likely real) |
| `kowalski` | `drb` | 0–1 | Deep real/bogus score |
| `kowalski` | `sgScore` | 0–1 | Star/galaxy score (0=galaxy, 1=star) |
| `Kowalski` | `ACAI_score` | 0–1 | ACAI spectral classifier score |

**Fritz-specific (may not be in base SkyPortal):**

- TDE scores, SN Ia scores, and other classifier outputs
- Period scores, variability metrics
- Cross-match results from catalogs

**Note:** Available annotation origins and keys depend on your instance's alert
processing pipeline. To discover what annotations exist, fetch a source with
`GET /api/sources/{obj_id}` and inspect the `annotations` field.

### Annotation Sorting

- `sortByAnnotationOrigin` — origin to sort by
- `sortByAnnotationKey` — key within that annotation
- `sortByAnnotationOrder` — "asc" or "desc"

---

## Photometry Annotation Filters

These filter on per-detection (per-photometry-point) annotations rather than
source-level annotations:

- `photometryAnnotationsFilter` — annotation key/value filter
- `photometryAnnotationsFilterOrigin` — which annotation origin
- `photometryAnnotationsFilterAfter` / `Before` — date range for detections
- `photometryAnnotationsFilterMinCount` — minimum number of matching detections (default 1)

---

## Localization (GW/GRB Event) Filters

- `localizationDateobs` — filter by GW/GRB event date
- `localizationName` — filter by localization name
- `localizationCumprob` — cumulative probability contour (default 0.95)
- Requires `firstDetectionAfter` and `lastDetectionBefore` to also be set

---

## Querying Sources: GET /api/sources

Similar to candidates, plus:

- `ra`, `dec`, `radius` — cone search (degrees)
- `savedAfter` / `savedBefore` — when saved to group
- `hasSpectrum` — boolean
- `hasFollowupRequest` — boolean
- `hasTNSname` — boolean

---

## Managing Filters: /api/filters

Filters determine which alerts from a stream become candidates for a group:

- `POST /api/filters` with `{"name": "...", "stream_id": N, "group_id": N}`
- `GET /api/filters` — list all accessible filters
- `PATCH /api/filters/{id}` — update filter name
- `DELETE /api/filters/{id}` — delete filter

**Important distinction:** Fritz filters operate on the alert stream and determine
which alerts become candidates. They are NOT the same as query-time parameters
on `/api/candidates`. To search existing candidates with specific criteria, use
the query parameters documented above.

---

## What CAN vs CANNOT Be Filtered via API

**Filterable via API parameters (fast, server-side):**

- Classification type, redshift range, date ranges
- Real/bogus score, star/galaxy score (via annotation filters)
- Saved status, group membership, user lists
- Cone search (RA/Dec/radius)
- Photometry annotation properties
- Number of detections, first/last detection dates

**Requires fetching data + computation (use dedicated MCP tools):**

- Color cuts (g-r, g-i thresholds) — need photometry per source
- Rise time or light curve shape — need photometry time series analysis
- Proximity to galaxy centers — need catalog cross-matching
- Pre-peak detections — need to identify peak from light curve
- Combined computed criteria — need multi-step analysis pipeline
