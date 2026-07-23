"""Tests for candidate filtering and watchlist filter generation."""

import json

import httpx
import pytest

from .conftest import call_tool_text

pytestmark = pytest.mark.asyncio

TARGETS = json.dumps(
    [
        {"name": "M31", "ra": 10.6847, "dec": 41.2687},
        {"name": "Crab", "ra": 83.6333, "dec": 22.0145},
    ]
)


# ─── generate_watchlist_filter ──────────────────────────────────────────────


async def test_watchlist_filter_pipeline_structure(mcp_client):
    text = await call_tool_text(
        mcp_client,
        "generate_watchlist_filter",
        {"targets": TARGETS, "max_distance_arcsec": 3.0, "filter_name": "TNS watch"},
    )
    assert "TNS watch" in text
    assert "M31" in text and "Crab" in text

    pipeline = json.loads(text.split("## MongoDB Pipeline JSON:")[1])
    assert isinstance(pipeline, list) and len(pipeline) == 4
    # Targets are embedded in the distance-computation stage
    map_input = pipeline[0]["$addFields"]["watchlist_distances"]["$map"]["input"]
    assert [t["name"] for t in map_input] == ["M31", "Crab"]
    # The match-radius stage uses the requested distance
    cond = pipeline[1]["$addFields"]["watchlist_matches"]["$filter"]["cond"]
    assert cond["$lte"][1] == 3.0
    # Non-matching alerts are dropped
    assert pipeline[2] == {"$match": {"watchlist_matches": {"$ne": []}}}


@pytest.mark.parametrize(
    "targets,expected_error",
    [
        ("not json", "Error parsing targets JSON"),
        ('{"name": "M31"}', "must be a JSON array"),
        ("[]", "cannot be empty"),
        ('[{"name": "M31", "ra": 10.0}]', "missing required fields"),
        ('[{"name": "M31", "ra": 400.0, "dec": 0.0}]', "RA must be in range"),
        ('[{"name": "M31", "ra": 10.0, "dec": -100.0}]', "Dec must be in range"),
        ('[{"name": "M31", "ra": "abc", "dec": 0.0}]', "must be numeric"),
    ],
)
async def test_watchlist_filter_input_validation(mcp_client, targets, expected_error):
    text = await call_tool_text(
        mcp_client, "generate_watchlist_filter", {"targets": targets}
    )
    assert expected_error in text


# ─── filter_candidates ──────────────────────────────────────────────────────

CANDIDATE = {
    "id": "ZTF24xyz",
    "ra": 150.0,
    "dec": 2.0,
    "redshift": 0.05,
    "saved_at": "2024-05-01T12:00:00",
    "photometry": [
        {"mjd": 60000.0, "mag": 19.0, "filter": "ztfg"},
        {"mjd": 60010.0, "mag": 18.5, "filter": "ztfr"},
    ],
    "classifications": [{"classification": "SN Ia"}],
    "annotations": [{"origin": "braai", "data": {"braai": 0.95}}],
}


async def test_filter_candidates_csv_output(mcp_client, skyportal_api):
    skyportal_api.add(
        "GET",
        "/api/candidates",
        json={
            "status": "success",
            "data": {"candidates": [CANDIDATE], "totalMatches": 1},
        },
    )
    text = await call_tool_text(
        mcp_client,
        "filter_candidates",
        {
            "classifications": "SN Ia",
            "annotation_filters": '[{"origin":"braai","key":"braai","min":0.8}]',
        },
    )
    assert "Found 1 candidates" in text
    # CSV header gains a column per annotation filter
    assert (
        "obj_id,ra,dec,redshift,latest_mag,latest_filter,saved_at,"
        "classifications,braai_braai" in text
    )
    # Latest photometry point (by MJD) is used; values are rounded
    assert (
        "ZTF24xyz,150.000000,+2.000000,0.0500,18.50,ztfr,2024-05-01,SN Ia,0.950"
        in text
    )
    assert "Filter Configuration" in text

    params = httpx.QueryParams(skyportal_api.requests[0].url.query)
    assert params["classifications"] == "SN Ia"
    assert json.loads(params["annotationFilterList"]) == {
        "origin": "braai",
        "key": "braai",
        "min": 0.8,
    }


async def test_filter_candidates_caps_page_size(mcp_client, skyportal_api):
    skyportal_api.add(
        "GET",
        "/api/candidates",
        json={"status": "success", "data": {"candidates": [], "totalMatches": 0}},
    )
    await call_tool_text(mcp_client, "filter_candidates", {"num_per_page": 5000})
    params = httpx.QueryParams(skyportal_api.requests[0].url.query)
    assert params["numPerPage"] == "500"


async def test_filter_candidates_no_matches(mcp_client, skyportal_api):
    skyportal_api.add(
        "GET",
        "/api/candidates",
        json={"status": "success", "data": {"candidates": [], "totalMatches": 0}},
    )
    text = await call_tool_text(
        mcp_client, "filter_candidates", {"min_redshift": 0.1}
    )
    assert "No candidates found" in text
    assert "z>=0.1" in text


async def test_filter_candidates_rejects_bad_annotation_json(mcp_client):
    text = await call_tool_text(
        mcp_client, "filter_candidates", {"annotation_filters": "{broken"}
    )
    assert "Error parsing annotation_filters JSON" in text


async def test_filter_candidates_requires_auth(mcp_client, no_auth):
    text = await call_tool_text(mcp_client, "filter_candidates", {})
    assert "Not authenticated" in text
