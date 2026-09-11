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
