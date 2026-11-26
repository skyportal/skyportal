from unittest.mock import Mock

import pytest
import requests

from skyportal.utils.paper_corner import ADSClient, ADSRequestLimit, collect_papers


def ads_page(docs, total=None, status=200, headers=None):
    response = Mock(status_code=status, headers=headers or {})
    response.json.return_value = {
        "response": {"docs": docs, "numFound": len(docs) if total is None else total}
    }
    return response


def mock_ads(monkeypatch, *pages):
    get = Mock(side_effect=pages)
    monkeypatch.setattr(requests, "get", get)
    return get


def test_ads_checks_exact_designation_and_accepts_tns_name_spacing(monkeypatch):
    get = mock_ads(
        monkeypatch,
        ads_page(
            [
                {
                    "bibcode": "exact",
                    "title": ["Light curves"],
                    "abstract": "SN 2023ixf.",
                },
                {"bibcode": "prior", "title": ["AT 2023ixf: First impressions"]},
                {"bibcode": "prefix", "title": ["SN 2023ixff"]},
                {"bibcode": "suffix", "title": ["XSN2023ixf"]},
            ]
        ),
    )

    results = ADSClient("token", 1).search(["SN2023ixf"])["SN2023ixf"]

    assert [result["bibcode"] for result in results] == ["exact", "prior"]
    assert 'abs:"SN 2023ixf"' in get.call_args.kwargs["params"]["q"]
    assert [result["designations"] for result in results] == [
        ["SN 2023ixf"],
        ["AT 2023ixf"],
    ]


def test_deduplication_preserves_first_date_and_all_matches(monkeypatch):
    journal = {
        "bibcode": "2026ApJ...999..123E",
        "alternate_bibcode": ["2025arXiv250812345E"],
        "identifier": ["arXiv:2508.12345v2"],
        "title": ["A study of AT2025abc"],
        "abstract": "Observations of ZTF25aabcxyz and AT2025abc.",
        "first_author": "Example, A.",
        "pubdate": "2026-02-00",
    }
    preprint = {
        "bibcode": "2025arXiv250812345E",
        "identifier": ["arXiv:2508.12345"],
        "title": ["Preprint on ZTF25aabcxyz"],
        "pubdate": "2025-08-21",
    }
    recent = {
        "bibcode": "2026ApJ...999..456F",
        "title": ["New observations of AT2025abc"],
        "pubdate": "2026-01-00",
    }
    get = mock_ads(monkeypatch, ads_page([journal, preprint, recent]))
    results = ADSClient("token", 1).search(["AT2025abc", "ZTF25aabcxyz"])
    matches = [("a", match) for match in results["AT2025abc"]] + [
        ("b", match) for match in results["ZTF25aabcxyz"]
    ]
    get.assert_called_once()
    query = get.call_args.kwargs["params"]["q"]
    assert 'abs:"AT 2025abc"' in query
    assert 'abs:"ZTF25aabcxyz"' in query

    papers = collect_papers(matches, 5)

    assert [paper["bibcode"] for paper in papers] == [
        recent["bibcode"],
        journal["bibcode"],
    ]
    assert papers[1] == {
        "bibcode": journal["bibcode"],
        "first_author": "Example, A.",
        "arxiv_id": "2508.12345",
        "title": journal["title"][0],
        "date": "2025-08-21",
        "sources": [
            {"id": "a", "designations": ["AT 2025abc"]},
            {"id": "b", "designations": ["ZTF25aabcxyz"]},
        ],
    }
    assert collect_papers(matches, 1) == papers[:1]


def test_ads_paginates_and_keeps_matches_with_their_sources(monkeypatch):
    first = {"bibcode": "a", "title": ["SN 2023ixf"]}
    second = {"bibcode": "b", "title": ["A study of AT 2025abc"]}
    get = mock_ads(monkeypatch, ads_page([first], 2), ads_page([second], 2))
    ads = ADSClient("token", 2)

    results = ads.search(["SN2023ixf", "AT2025abc", "AT2025xyz"])

    assert [call.kwargs["params"]["start"] for call in get.call_args_list] == [0, 1]
    assert [record["bibcode"] for record in results["SN2023ixf"]] == ["a"]
    assert [record["bibcode"] for record in results["AT2025abc"]] == ["b"]
    assert results["AT2025xyz"] == []
    assert ads.remaining == 0


def test_ads_respects_refresh_budget_between_pages(monkeypatch):
    first = {"bibcode": "a", "title": ["SN 2023ixf"]}
    get = mock_ads(monkeypatch, ads_page([first], 2))

    with pytest.raises(ADSRequestLimit):
        ADSClient("token", 1).search(["SN2023ixf", "AT2025abc"])
    get.assert_called_once()


@pytest.mark.parametrize("status", [200, 429])
def test_ads_respects_provider_quota_and_reset(monkeypatch, status):
    get = mock_ads(
        monkeypatch,
        ads_page(
            [],
            status=status,
            headers={"X-RateLimit-Remaining": "0", "X-RateLimit-Reset": "1795392000"},
        ),
    )
    ads = ADSClient("token", 10)
    if status == 200:
        assert ads.search(["SN2023ixf"]) == {"SN2023ixf": []}
    with pytest.raises(ADSRequestLimit):
        ads.search(["AT2025abc"])
    assert ads.resume_at == 1795392000
    get.assert_called_once()


def test_ads_errors_are_distinct_from_empty_results(monkeypatch):
    response = ads_page([], status=503)
    response.raise_for_status.side_effect = requests.HTTPError
    mock_ads(monkeypatch, ads_page([]), response)
    ads = ADSClient("token", 2)

    assert ads.search(["SN2023ixf"]) == {"SN2023ixf": []}
    with pytest.raises(requests.HTTPError):
        ads.search(["SN2023ixf"])


def test_ads_read_timeout_consumes_one_request_without_retrying(monkeypatch):
    get = Mock(side_effect=requests.ReadTimeout)
    monkeypatch.setattr(requests, "get", get)
    ads = ADSClient("token", 2)

    with pytest.raises(requests.ReadTimeout):
        ads.search(["SN2023ixf", "AT2025abc"])

    get.assert_called_once()
    assert get.call_args.kwargs["timeout"] == (5, 60)
    assert get.call_args.kwargs["params"]["rows"] == 500
    assert ads.remaining == 1
