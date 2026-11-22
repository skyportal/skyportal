from unittest.mock import Mock

import pytest
import requests

from skyportal.utils.paper_corner import collect_papers, search_ads


def mock_ads(monkeypatch, docs):
    response = Mock()
    response.json.return_value = {"response": {"docs": docs}}
    get = Mock(return_value=response)
    monkeypatch.setattr(requests, "get", get)
    return get


def test_ads_checks_exact_designation_and_accepts_tns_name_spacing(monkeypatch):
    get = mock_ads(
        monkeypatch,
        [
            {"bibcode": "exact", "title": ["Light curves"], "abstract": "SN 2023ixf."},
            {"bibcode": "prefix", "title": ["SN 2023ixff"]},
            {"bibcode": "suffix", "title": ["XSN2023ixf"]},
        ],
    )

    results = search_ads("SN2023ixf", "token")

    assert [result["bibcode"] for result in results] == ["exact"]
    assert 'abs:"SN 2023ixf"' in get.call_args.kwargs["params"]["q"]
    assert results[0]["designation"] == "SN2023ixf"


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
    mock_ads(monkeypatch, [journal, preprint, recent])
    matches = [("a", match) for match in search_ads("AT2025abc", "token")] + [
        ("b", match) for match in search_ads("ZTF25aabcxyz", "token")
    ]

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
            {"id": "a", "designations": ["AT2025abc"]},
            {"id": "b", "designations": ["ZTF25aabcxyz"]},
        ],
    }
    assert collect_papers(matches, 1) == papers[:1]


def test_ads_errors_are_distinct_from_empty_results(monkeypatch):
    get = mock_ads(monkeypatch, [])
    assert search_ads("SN2023ixf", "token") == []
    get.return_value.raise_for_status.side_effect = requests.HTTPError
    with pytest.raises(requests.HTTPError):
        search_ads("SN2023ixf", "token")
