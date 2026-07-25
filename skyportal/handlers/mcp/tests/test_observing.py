"""Tests for observability computation (pure astropy, no network)."""

import pytest

from .conftest import call_tool_text

pytestmark = pytest.mark.asyncio


async def test_observable_target_reports_windows(mcp_client):
    # RA 17.5h transits near local midnight in mid-June; well placed for Keck
    text = await call_tool_text(
        mcp_client,
        "get_source_observability",
        {"ra": 262.5, "dec": 20.0, "telescopes": "Keck", "date": "2024-06-15"},
    )
    assert "RA=262.50000, Dec=+20.00000" in text
    assert "Date: 2024-06-15" in text
    assert "Keck" in text
    assert "Observable:" in text
    assert "Transit:" in text


async def test_never_rising_target(mcp_client):
    # Dec -75 never rises above the horizon from Mauna Kea (lat +19.8)
    text = await call_tool_text(
        mcp_client,
        "get_source_observability",
        {"ra": 100.0, "dec": -75.0, "telescopes": "Keck", "date": "2024-06-15"},
    )
    assert "NOT OBSERVABLE" in text
    assert "never rises above horizon" in text


async def test_multiple_telescopes(mcp_client):
    text = await call_tool_text(
        mcp_client,
        "get_source_observability",
        {
            "ra": 262.5,
            "dec": -30.0,
            "telescopes": "VLT,Gemini-S",
            "date": "2024-06-15",
        },
    )
    assert "Vlt" in text
    assert "Gemini-S" in text


async def test_unknown_telescope(mcp_client):
    text = await call_tool_text(
        mcp_client,
        "get_source_observability",
        {"ra": 100.0, "dec": 0.0, "telescopes": "Hubble", "date": "2024-06-15"},
    )
    assert "Unknown telescope 'hubble'" in text


async def test_requires_position(mcp_client):
    text = await call_tool_text(mcp_client, "get_source_observability", {})
    assert "Provide either source_id or both ra and dec" in text
