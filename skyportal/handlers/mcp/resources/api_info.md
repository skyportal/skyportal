# SkyPortal API Info Reference Sheet

> **Note:** For a quick reference of all available MCP tools (recommended high-level interface), see the `tools_reference` resource. This document covers the underlying API endpoints.

## Base URL

`http://localhost:5001` (for local development)

## Authentication

All requests require an API token in the header:

```
Authorization: token YOUR_TOKEN_HERE
```

---

## Core Endpoints

### **Sources** (`/api/sources`)

Astronomical objects that have been saved for follow-up

**Common Operations:**

- `GET /api/sources` - List all sources (with filters)
- `GET /api/sources/{obj_id}` - Get specific source details
- `POST /api/sources` - Create/save a new source
- `PATCH /api/sources/{obj_id}` - Update source metadata
- `DELETE /api/sources/{obj_id}` - Remove source

**Key Query Parameters:**

- `savedAfter`, `savedBefore` - Filter by save date
- `startDate`, `endDate` - Filter by observation date
- `group_ids` - Filter by group membership
- `classifications` - Filter by classification type
- `ra`, `dec`, `radius` - Spatial cone search

---

### **Candidates** (`/api/candidates`)

Potential sources from alert streams awaiting review

**Common Operations:**

- `GET /api/candidates` - List candidates for scanning
- `GET /api/candidates/{obj_id}` - Get candidate details
- `POST /api/candidates` - Save candidate as source
- `DELETE /api/candidates/{candidate_id}` - Remove candidate

**Key Query Parameters:**

- `savedAfter`, `savedBefore` - Date filters
- `classifications` - Filter by ML classifications
- `redshiftMinimum`, `redshiftMaximum` - Redshift range
- `numPerPage` - Pagination

---

### **Photometry** (`/api/photometry`)

Brightness measurements over time (light curves)

**Common Operations:**

- `GET /api/sources/{obj_id}/photometry` - Get photometry for source
- `POST /api/photometry` - Upload new photometry
- `PUT /api/photometry` - Bulk upload photometry
- `PATCH /api/photometry/{photometry_id}` - Update measurement
- `DELETE /api/photometry/{photometry_id}` - Delete measurement
- `GET /api/photometry/range` - Query by time/magnitude range

**Key Fields:**

- `obj_id` - Source identifier
- `mjd` - Modified Julian Date
- `mag` or `flux` - Brightness measurement
- `magerr` or `fluxerr` - Measurement error
- `filter` - Photometric filter used
- `instrument_id` - Instrument that made observation

---

### **Spectra** (`/api/spectrum`)

Spectroscopic observations

**Common Operations:**

- `GET /api/sources/{obj_id}/spectra` - Get all spectra for source
- `GET /api/spectrum/{spectrum_id}` - Get specific spectrum
- `POST /api/spectrum` - Upload new spectrum
- `POST /api/spectrum/ascii` - Upload from ASCII file
- `PUT /api/spectrum/{spectrum_id}` - Update spectrum
- `DELETE /api/spectrum/{spectrum_id}` - Delete spectrum

**Key Fields:**

- `obj_id` - Source identifier
- `observed_at` - Observation datetime
- `wavelengths` - Array of wavelength values
- `fluxes` - Array of flux values
- `instrument_id` - Instrument used

---

### **Classifications** (`/api/classification`)

Source type classifications (e.g., SN Ia, AGN, variable star)

**Common Operations:**

- `GET /api/sources/{obj_id}/classifications` - Get all classifications
- `GET /api/classification/{classification_id}` - Get specific classification
- `POST /api/classification` - Add new classification
- `PUT /api/classification/{classification_id}` - Update classification
- `DELETE /api/classification/{classification_id}` - Remove classification

**Key Fields:**

- `obj_id` - Source identifier
- `classification` - Type (must be in taxonomy)
- `taxonomy_id` - Which taxonomy to use
- `probability` - Confidence (0-1)
- `group_ids` - Groups that can see this classification

---

### **Comments** (`/api/comment`)

Collaborative notes on sources

**Common Operations:**

- `POST /api/comment` - Add comment to source
- `GET /api/comment/{comment_id}` - Get specific comment
- `PUT /api/comment/{comment_id}` - Edit comment
- `DELETE /api/comment/{comment_id}` - Delete comment

**Key Fields:**

- `obj_id` - Source to comment on
- `text` - Comment content

---

### **Annotations** (`/api/annotation`)

Structured metadata on sources

**Common Operations:**

- `POST /api/annotation` - Add annotation
- `GET /api/annotation/{annotation_id}` - Get annotation
- `PUT /api/annotation/{annotation_id}` - Update annotation
- `DELETE /api/annotation/{annotation_id}` - Delete annotation

**Key Fields:**

- `obj_id` - Source identifier
- `origin` - Data source/pipeline name
- `data` - JSON object with key-value pairs

---

### **Groups** (`/api/groups`)

Collaboration groups with access permissions

**Common Operations:**

- `GET /api/groups` - List all groups user can access
- `GET /api/groups/{group_id}` - Get group details
- `POST /api/groups` - Create new group
- `PUT /api/groups/{group_id}` - Update group
- `GET /api/sources/{obj_id}/groups` - Get groups that can access source

---

### **Telescopes** (`/api/telescope`)

Telescope facilities

**Common Operations:**

- `GET /api/telescope` - List all telescopes
- `GET /api/telescope/{telescope_id}` - Get telescope details
- `POST /api/telescope` - Add new telescope

---

### **Instruments** (`/api/instrument`)

Instruments attached to telescopes

**Common Operations:**

- `GET /api/instrument` - List all instruments
- `GET /api/instrument/{instrument_id}` - Get instrument details
- `POST /api/instrument` - Add new instrument

---

### **Follow-up Requests** (`/api/followup_request`)

Observation requests for sources

**Common Operations:**

- `GET /api/followup_request` - List follow-up requests
- `GET /api/followup_request/{request_id}` - Get request details
- `POST /api/followup_request` - Submit new request
- `PUT /api/followup_request/{request_id}` - Update request
- `DELETE /api/followup_request/{request_id}` - Cancel request

**Key Fields:**

- `obj_id` - Target source
- `allocation_id` - Time allocation to use
- `payload` - Request-specific parameters (JSON)

---

### **Observing Runs** (`/api/observing_run`)

Scheduled observing sessions

**Common Operations:**

- `GET /api/observing_run` - List observing runs
- `GET /api/observing_run/{run_id}` - Get run details with assignments
- `POST /api/observing_run` - Create new run
- `PUT /api/observing_run/{run_id}` - Update run

---

### **Taxonomies** (`/api/taxonomy`)

Classification hierarchies

**Common Operations:**

- `GET /api/taxonomy` - List available taxonomies
- `GET /api/taxonomy/{taxonomy_id}` - Get taxonomy hierarchy
- `POST /api/taxonomy` - Upload new taxonomy

---

### **System Info** (`/api/sysinfo`)

System information and git version

**Common Operations:**

- `GET /api/sysinfo` - Get version and recent commits

---

## Common Use Cases

### 1. **Find Recent Supernovae**

```
GET /api/sources?classifications=SN Ia,SN II&savedAfter=2024-01-01
```

### 2. **Search Sources by Position**

```
GET /api/sources?ra=150.0&dec=2.5&radius=0.1
```

(Search within 0.1 degrees of RA=150°, Dec=2.5°)

### 3. **Get Complete Source Information**

```
GET /api/sources/{obj_id}
```

Returns source with photometry, spectra, classifications, comments

### 4. **Find Sources in Redshift Range**

```
GET /api/sources?minRedshift=0.0&maxRedshift=0.1
```

### 5. **Get Light Curve Data**

```
GET /api/sources/{obj_id}/photometry
```

### 6. **Find Candidates from Last Week**

```
GET /api/candidates?savedAfter=2024-01-25&numPerPage=100
```

### 7. **Search by Classification and Date**

```
GET /api/sources?classifications=AGN&startDate=2024-01-01&endDate=2024-12-31
```

### 8. **Get Sources for a Specific Group**

```
GET /api/sources?group_ids=5
```

### 9. **Find Transients with Recent Detections**

```
GET /api/sources?savedAfter=2024-01-01&hasSpectrum=true
```

### 10. **Query Photometry by Date Range**

```
GET /api/photometry/range?startDate=2024-01-01&endDate=2024-12-31&minMag=15&maxMag=20
```

---

## Response Format

All responses follow this structure:

```json
{
  "status": "success" | "error",
  "data": { ... },
  "message": "Error message if status is error",
  "version": "1.4.0"
}
```

---

## Pagination

Many endpoints support pagination:

- `numPerPage` - Number of results per page (default: 100)
- `pageNumber` - Page to retrieve (default: 1)

---

## Use MCP Tools Instead of These Endpoints

> **💡 TIP:** For a complete reference of all MCP tools with usage guidelines and workflows, see the `tools_reference` resource.

Some API endpoints return images or PDFs that cannot be parsed. Use the
dedicated MCP tools instead:

| Instead of                                          | Use MCP tool                                                       |
| --------------------------------------------------- | ------------------------------------------------------------------ |
| **Multiple API calls for TNS report**               | **`get_tns_summary` (ONE call for complete TNS/AstroNote report)** |
| `GET /api/sources/{id}/observability` (returns PDF) | `get_source_observability` (returns text with exact time windows)  |
| `GET /api/sources/{id}/photometry`                  | `get_source_photometry` (returns CSV, easier to analyze)           |
| Manual time conversion                              | `convert_time` (MJD/JD/ISO/Unix)                                   |
| Looking up survey URLs by hand                      | `get_survey_urls` (returns links for 15+ surveys)                  |
| Searching IRSA for ZTF images                       | `get_ztf_cutout_urls` (returns FITS download URLs)                 |
| Reading candidate filter docs                       | `get_candidate_filter_reference` (returns filter parameter guide)  |

### ⭐ TNS/AstroNote Reports

**When user asks to create TNS report, AstroNote, or source summary:**

- Use `get_tns_summary(source_name)` - single tool that combines ALL data
- DO NOT call `get_source_photometry`, `get_source_spectra`, `get_source_classifications` separately
- Tool returns formatted report with: coordinates, discovery, photometry, classification, spectra, host
- After generating summary, ask user what additional context they need (e.g., spectroscopic follow-up plans, comparison to similar events, references)

---

## Tips

1. **Start broad, then filter**: Use `/api/sources` with query parameters rather than trying to get individual sources
2. **Use date ranges**: Most astronomical queries care about when observations were made
3. **Spatial searches**: RA/Dec/radius is powerful for finding nearby sources
4. **Check group access**: Sources are tied to groups for permissions
5. **Redshift is key**: Many queries filter by redshift range
6. **Classification filtering**: Use standard taxonomy names (SN Ia, AGN, etc.)
7. **Prefer MCP tools**: For observability, photometry, and time conversion, use the dedicated MCP tools above rather than raw API calls

---

## Full Documentation

For complete API documentation with all parameters and response schemas:

- Auto-generated docs: https://github.com/skyportal/skyportal_client/tree/master/docs
- Main SkyPortal docs: https://skyportal.io/docs/api.html
