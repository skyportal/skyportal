import json

from skyportal.utils import gitlog

log = """
[2020-10-06T19:38:32-07:00 f3542fa8 someone@berkeley.edu] Pass git log to frontend as parsed components
[2020-10-05T14:06:20+03:00 a4052098f noreply@github.com] Bump emoji-dictionary from 1.0.10 to 1.0.11 (#1040)
[2026-08-23T00:31:04Z d487cce7d someone@berkeley.edu] Add a public profile page
""".split("\n")


def test_gitlog_parse():
    entries = gitlog.parse_gitlog(
        {
            "pr_url_base": "https://github.com/skyportal/skyportal/pull",
            "commit_url_base": "https://github.com/skyportal/skyportal/commit",
            "name": "SP",
            "log": log,
        }
    )
    e0 = entries[0]
    e1 = entries[1]
    e2 = entries[2]

    assert e0["name"] == "SP"
    assert e0["time"] == "2020-10-06T19:38:32-07:00"
    assert e0["sha"] == "f3542fa8"
    assert e0["email"] == "someone@berkeley.edu"
    assert e0["description"] == "Pass git log to frontend as parsed components"
    assert e0["pr_nr"] is None
    assert e0["pr_url"] == ""
    assert e0["commit_url"] == "https://github.com/skyportal/skyportal/commit/f3542fa8"

    assert e1["name"] == "SP"
    assert e1["time"] == "2020-10-05T14:06:20+03:00"
    assert e1["sha"] == "a4052098f"
    assert e1["email"] == "noreply@github.com"
    assert e1["description"] == "Bump emoji-dictionary from 1.0.10 to 1.0.11"
    assert e1["pr_nr"] == "1040"
    assert e1["pr_url"] == "https://github.com/skyportal/skyportal/pull/1040"
    assert e1["commit_url"] == "https://github.com/skyportal/skyportal/commit/a4052098f"

    assert e2["name"] == "SP"
    assert e2["time"] == "2026-08-23T00:31:04Z"
    assert e2["sha"] == "d487cce7d"
    assert e2["email"] == "someone@berkeley.edu"
    assert e2["description"] == "Add a public profile page"
    assert e2["pr_nr"] is None
    assert e2["pr_url"] == ""
    assert e2["commit_url"] == "https://github.com/skyportal/skyportal/commit/d487cce7d"


def test_load_gitlog_sorts_by_time_not_by_string(tmp_path):
    # 10:00+02:00 is 08:00 UTC, older than 08:19-05:00 (13:19 UTC)
    (tmp_path / "gitlog-test.json").write_text(
        json.dumps(
            {
                "pr_url_base": "",
                "commit_url_base": "",
                "log": [
                    "[2026-09-29T10:00:00+02:00 aaaaaaa a@b.c] Older",
                    "[2026-09-29T08:19:35-05:00 bbbbbbb a@b.c] Newer",
                ],
            }
        )
    )
    entries = gitlog.load_gitlog(str(tmp_path / "gitlog*.json"))
    assert [e["sha"] for e in entries] == ["bbbbbbb", "aaaaaaa"]


def test_normalize_pr_url():
    canonical = "https://github.com/skyportal/skyportal/pull/1234"
    for url in [
        canonical,
        "http://github.com/SkyPortal/skyportal/pull/1234",
        "github.com/skyportal/skyportal/pull/01234/files",
        " https://www.github.com/skyportal/skyportal/pull/1234#discussion_r1 ",
        "https://github.com/skyportal/skyportal/pull/1234?w=1",
    ]:
        assert gitlog.normalize_pr_url(url) == canonical
    for url in [
        "https://github.com/skyportal/skyportal/issues/1234",
        "https://gitlab.com/skyportal/skyportal/pull/1234",
        "https://github.com/skyportal/skyportal/pull/1234x",
        "1234",
    ]:
        assert gitlog.normalize_pr_url(url) is None


def test_deployed_pr_urls_and_tracked_bases():
    entries = gitlog.parse_gitlog(
        {
            "pr_url_base": "https://github.com/Fritz-Marshal/fritz/pull",
            "commit_url_base": "https://github.com/Fritz-Marshal/fritz/commit",
            "log": log,
        }
    )
    assert gitlog.deployed_pr_urls(entries) == {
        "https://github.com/fritz-marshal/fritz/pull/1040"
    }
    assert gitlog.tracked_pr_url_bases(gitlog.deployed_pr_urls(entries)) == {
        "https://github.com/fritz-marshal/fritz/pull/"
    }
