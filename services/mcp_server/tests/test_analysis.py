"""Tests for light-curve analysis with synthetic photometry."""

import json
from pathlib import Path

import pytest

from .conftest import call_tool_text

pytestmark = pytest.mark.asyncio


def make_photometry(points, filter_name="ztfg"):
    return [
        {"mjd": mjd, "mag": mag, "magerr": 0.1, "filter": filter_name}
        for mjd, mag in points
    ]


def add_source_with_photometry(fake, photometry, obj_id="ZTF21abc"):
    fake.add(
        "GET",
        f"/api/sources/{obj_id}",
        json={"status": "success", "data": {"id": obj_id, "ra": 150.0, "dec": 2.0}},
    )
    fake.add(
        "GET",
        f"/api/sources/{obj_id}/photometry",
        json={"status": "success", "data": photometry},
    )


# Rise 10 days (19.0 → 17.5), fade past the 0.3-mag baseline after 5 days
COMPLETE_LC = [
    (60000.0, 19.0),
    (60005.0, 18.0),
    (60010.0, 17.5),
    (60015.0, 18.0),
    (60020.0, 19.0),
]


async def test_complete_light_curve_metrics(mcp_client, skyportal_api):
    add_source_with_photometry(skyportal_api, make_photometry(COMPLETE_LC))
    text = await call_tool_text(
        mcp_client,
        "analyze_light_curve",
        {
            "source_name": "ZTF21abc",
            "filter_names": "ztfg",
            "output_format": "text",
        },
    )
    assert "LIGHT CURVE ANALYSIS: ZTF21abc" in text
    assert "Status:        Complete light curve" in text
    assert "Peak mag:      17.50" in text
    assert "Peak time:     MJD 60010.00" in text
    assert "Rise time:     10.0 days" in text
    # Baseline (>0.3 mag below peak) is first reached at MJD 60015
    assert "Fade time:     5.0 days" in text
    assert "Total duration: 15.0 days" in text


async def test_still_rising_light_curve(mcp_client, skyportal_api):
    rising = [(60000.0, 19.0), (60005.0, 18.5), (60010.0, 18.0)]
    add_source_with_photometry(skyportal_api, make_photometry(rising))
    text = await call_tool_text(
        mcp_client,
        "analyze_light_curve",
        {
            "source_name": "ZTF21abc",
            "filter_names": "ztfg",
            "output_format": "text",
        },
    )
    assert "Status:        Still rising" in text
    assert "N/A (still rising)" in text


async def test_missing_filters_are_skipped(mcp_client, skyportal_api):
    # Only ztfg data exists; requesting ztfg+ztfr should analyze ztfg only
    add_source_with_photometry(skyportal_api, make_photometry(COMPLETE_LC))
    text = await call_tool_text(
        mcp_client,
        "analyze_light_curve",
        {
            "source_name": "ZTF21abc",
            "filter_names": "ztfg,ztfr",
            "output_format": "text",
        },
    )
    assert "## ZTFG BAND" in text
    assert "## ZTFR BAND" not in text


async def test_no_usable_photometry(mcp_client, skyportal_api):
    add_source_with_photometry(skyportal_api, make_photometry(COMPLETE_LC, "ztfg"))
    text = await call_tool_text(
        mcp_client,
        "analyze_light_curve",
        {
            "source_name": "ZTF21abc",
            "filter_names": "sdssu",
            "output_format": "text",
        },
    )
    assert "No sufficient photometry" in text


async def test_notebook_output_writes_files(
    mcp_client, skyportal_api, tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    add_source_with_photometry(skyportal_api, make_photometry(COMPLETE_LC))
    text = await call_tool_text(
        mcp_client,
        "analyze_light_curve",
        {
            "source_name": "ZTF21abc",
            "filter_names": "ztfg",
            "output_format": "notebook",
        },
    )
    output_dir = Path("ZTF21abc_lightcurve_analysis")
    assert output_dir.is_dir()
    csv_files = list(output_dir.glob("*.csv"))
    notebooks = list(output_dir.glob("*.ipynb"))
    assert csv_files and notebooks
    notebook = json.loads(notebooks[0].read_text())
    assert notebook["nbformat"] == 4
    assert str(output_dir) in text


async def test_requires_auth(mcp_client, no_auth):
    text = await call_tool_text(
        mcp_client, "analyze_light_curve", {"source_name": "ZTF21abc"}
    )
    assert "Not authenticated" in text
