"""Tests for the typed sources endpoint functions."""

from __future__ import annotations

import json

import httpx
import respx

from skyportal_py import SkyPortal, sources

BASE_URL = "https://skyportal.example.com"


@respx.mock
def test_fetch_source(client: SkyPortal) -> None:
    """A source response validates into a Source model."""
    respx.get(f"{BASE_URL}/api/sources/ZTF20abcdef").mock(
        return_value=httpx.Response(
            200,
            json={
                "status": "success",
                "data": {
                    "id": "ZTF20abcdef",
                    "ra": 10.5,
                    "dec": -20.25,
                    "redshift": 0.1,
                    "groups": [{"id": 1, "name": "Program A", "nickname": "progA"}],
                },
            },
        )
    )
    source = sources.fetch_source(client, "ZTF20abcdef")
    assert source.id == "ZTF20abcdef"
    assert source.ra == 10.5
    assert source.groups[0].name == "Program A"
    assert source.redshift == 0.1

    # the same endpoint function is also bound as a method on the client
    assert client.fetch_source("ZTF20abcdef") == source


@respx.mock
def test_fetch_sources_pagination_and_filters(client: httpx.Client) -> None:
    """Query kwargs map to the endpoint's camelCase query parameters."""
    route = respx.get(f"{BASE_URL}/api/sources").mock(
        return_value=httpx.Response(
            200,
            json={
                "status": "success",
                "data": {
                    "sources": [{"id": "ZTF20abcdef"}],
                    "totalMatches": 42,
                    "pageNumber": 2,
                    "numPerPage": 1,
                },
            },
        )
    )
    page = sources.fetch_sources(
        client, page_number=2, num_per_page=1, ra=10.5, dec=-20.25, radius=0.5
    )
    assert page.total_matches == 42
    assert page.page_number == 2
    assert page.sources[0].id == "ZTF20abcdef"
    params = route.calls[0].request.url.params
    assert params["pageNumber"] == "2"
    assert params["numPerPage"] == "1"
    assert params["ra"] == "10.5"


@respx.mock
def test_post_source(client: httpx.Client) -> None:
    """The payload model is sent with unset fields omitted."""
    route = respx.post(f"{BASE_URL}/api/sources").mock(
        return_value=httpx.Response(
            200,
            json={
                "status": "success",
                "data": {"id": "ZTF20abcdef", "saved_to_groups": [1, 2]},
            },
        )
    )
    result = sources.post_source(
        client,
        sources.SourcePost(id="ZTF20abcdef", ra=10.5, dec=-20.25),
    )
    assert result.id == "ZTF20abcdef"
    assert result.saved_to_groups == [1, 2]
    assert result.warnings == []
    body = json.loads(route.calls[0].request.content)
    assert body == {"id": "ZTF20abcdef", "ra": 10.5, "dec": -20.25}
