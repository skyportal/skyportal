import re


pr_url_base = "https://github.com/skyportal/skyportal/pull"
commit_url_base = "https://github.com/skyportal/skyportal/commit"


def parse_gitlog(log):
    """Parse git log.

    Parameters
    ----------
    log : list
        The log should be passed in as a list of lines, obtained using::

          git log --no-merges --first-parent \
                  --pretty='format:[%ci %h] %s' -25

    Returns
    -------
    parsed_log : list of dict
        Each entry has keys `time` (commit time), `sha` (commit hash),
        `commit_url`, `pr_desc` (commit description), `pr_nr`, `pr_url`.

    """
    timestamp_re = '(?P<time>[0-9\\-:].*)'
    sha_re = '(?P<sha>[0-9a-f]{8})'
    pr_desc_re = '(?P<pr_desc>.*?)'
    pr_nr_re = '( \\(\\#(?P<pr_nr>[0-9]*)\\))?'
    log_re = f'\\[{timestamp_re} {sha_re}\\] {pr_desc_re}{pr_nr_re}$'

    gitlog = []
    for line in log:
        if not line:
            continue

        m = re.match(log_re, line)
        if m is None:
            print(f'sysinfo: could not parse gitlog line: [{line}]')
            continue

        log_fields = m.groupdict()
        pr_nr = log_fields['pr_nr']
        sha = log_fields['sha']
        log_fields['pr_url'] = f'{pr_url_base}/{pr_nr}' if pr_nr else ''
        log_fields['commit_url'] = f'{commit_url_base}/{sha}'

        gitlog.append(log_fields)

    return gitlog
