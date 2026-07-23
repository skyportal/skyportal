"""Tests for bulk-analysis code generation tools."""

import json
from pathlib import Path

import pytest

from .conftest import call_tool_text

pytestmark = pytest.mark.asyncio


@pytest.fixture(autouse=True)
def run_in_tmpdir(tmp_path, monkeypatch):
    # Codegen tools write notebooks relative to the current directory
    monkeypatch.chdir(tmp_path)


async def test_bulk_lightcurve_notebook_written(mcp_client):
    text = await call_tool_text(
        mcp_client,
        "generate_bulk_lightcurve_code",
        {"sources": "ZTF21aaaaaaa,ZTF21aaaaaab", "filters": "ztfg,ztfr"},
    )
    notebook_path = Path("ztf_lightcurves/bulk_lightcurve_download.ipynb")
    assert str(notebook_path) in text
    notebook = json.loads(notebook_path.read_text())
    assert notebook["nbformat"] == 4
    all_source = "".join(
        "".join(cell["source"]) for cell in notebook["cells"]
    )
    assert "ZTF21aaaaaaa" in all_source
    assert "ZTF21aaaaaab" in all_source
    assert "ztfquery" in all_source


async def test_bulk_lightcurve_accepts_json_array(mcp_client):
    await call_tool_text(
        mcp_client,
        "generate_bulk_lightcurve_code",
        {"sources": '["ZTF21aaaaaaa", "ZTF21aaaaaab"]'},
    )
    assert Path("ztf_lightcurves/bulk_lightcurve_download.ipynb").exists()


async def test_bulk_lightcurve_rejects_empty_sources(mcp_client):
    text = await call_tool_text(
        mcp_client, "generate_bulk_lightcurve_code", {"sources": " "}
    )
    assert "Error: No sources provided" in text


async def test_cone_search_code_contains_coordinates(mcp_client):
    text = await call_tool_text(
        mcp_client,
        "generate_cone_search_code",
        {"coordinates": "150.0,2.5,151.2,3.1", "radius_arcsec": 5.0},
    )
    assert "150.0" in text and "151.2" in text
    assert "ztfquery" in text


async def test_cone_search_rejects_odd_coordinate_count(mcp_client):
    text = await call_tool_text(
        mcp_client, "generate_cone_search_code", {"coordinates": "150.0,2.5,151.2"}
    )
    assert "Coordinates must be pairs" in text


async def test_fritz_bulk_query_code(mcp_client):
    text = await call_tool_text(
        mcp_client,
        "generate_fritz_bulk_query_code",
        {"sources": "ZTF21aaaaaaa", "include_spectra": True},
    )
    assert "ZTF21aaaaaaa" in text
    assert "fritz" in text


async def test_alert_download_code(mcp_client):
    text = await call_tool_text(
        mcp_client,
        "generate_alert_download_code",
        {"sources": "ZTF21aaaaaaa", "with_cutouts": True},
    )
    assert "ZTF21aaaaaaa" in text
    assert "alert" in text.lower()


async def test_field_visualization_code(mcp_client):
    text = await call_tool_text(
        mcp_client,
        "generate_field_visualization_code",
        {"field_id": 300, "ccd_id": 8},
    )
    assert "300" in text
