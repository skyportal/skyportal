from skyportal.utils import gitlog

log = """
[2020-10-06T19:38:32-07:00 f3542fa8 someone@berkeley.edu] Pass git log to frontend as parsed components
[2020-10-05T14:06:20+03:00 a4052098f noreply@github.com] Bump emoji-dictionary from 1.0.10 to 1.0.11 (#1040)
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
