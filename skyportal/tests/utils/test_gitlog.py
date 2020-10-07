from skyportal.utils import gitlog


log = '''
[2020-10-06 19:38:32 -0700 f3542fa8] Pass git log to frontend as parsed components
[2020-10-05 14:06:20 -0700 a4052098] Bump emoji-dictionary from 1.0.10 to 1.0.11 (#1040)
'''.split(
    '\n'
)


def test_gitlog_parse():
    entries = gitlog.parse_gitlog(log)
    e0 = entries[0]
    e1 = entries[1]

    assert e0['time'] == '2020-10-06 19:38:32 -0700'
    assert e0['sha'] == 'f3542fa8'
    assert e0['pr_desc'] == 'Pass git log to frontend as parsed components'
    assert e0['pr_nr'] is None
    assert e0['pr_url'] == ''
    assert e0['commit_url'] == (
        f"https://github.com/skyportal/skyportal/commit/f3542fa8"
    )

    assert e1['time'] == '2020-10-05 14:06:20 -0700'
    assert e1['sha'] == 'a4052098'
    assert e1['pr_desc'] == 'Bump emoji-dictionary from 1.0.10 to 1.0.11'
    assert e1['pr_nr'] == '1040'
    assert e1['pr_url'] == 'https://github.com/skyportal/skyportal/pull/1040'
    assert e1['commit_url'] == (
        f"https://github.com/skyportal/skyportal/commit/a4052098"
    )
