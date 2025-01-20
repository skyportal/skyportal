import re
import subprocess

from baselayer.log import make_log

log = make_log("gitlog")


def get_gitlog(
    cwd=".",
    name=None,
    pr_url_base="https://github.com/skyportal/skyportal/pull",
    commit_url_base="https://github.com/skyportal/skyportal/commit",
    N=1000,
):
    """Return git log for a given directory.

    Parameters
    ----------
    cwd : str
        Where to gather logs.
    N : int
        Number of log entries to return.
    name : str
        Name of these logs. Value is propagated into the output dictionary.

    Returns
    -------
    dict
        The output dictionary has the following keys:

        - pr_url_base: URL at which pull requests live
        - commit_url_base: URL at which commits live
        - name: Name of this set of logs
        - log: list of lines that come from::

          git log --no-merges --first-parent \
                  --pretty='format:[%cI %h %cE] %s' -1000

          (assuming N=1000)

    """
    p = subprocess.run(
        [
            "git",
            "--git-dir=.git",
            "log",
            "--no-merges",
            "--pretty=format:[%cI %h %cE] %s",
            "-1000",
        ],
        capture_output=True,
        text=True,
        cwd=cwd,
    )
    gitlog = {
        "name": name,
        "pr_url_base": pr_url_base,
        "commit_url_base": commit_url_base,
        "log": p.stdout.splitlines(),
    }
    return gitlog


def parse_gitlog(gitlog):
    """Parse git log.

    Parameters
    ----------
    gitlog : dict
        The log should be passed in as a dictionary that conforms to the
        output of `get_gitlog`.

    Returns
    -------
    parsed_log : list of dict
        Each entry has keys `time` (commit time), `sha` (commit hash),
        `email` (committer email), `commit_url`, `pr_desc` (commit description),
        `pr_nr`, `pr_url`.

    """
    pr_url_base = gitlog["pr_url_base"]
    commit_url_base = gitlog["commit_url_base"]
    name = gitlog.get("name", None)

    timechars = "[0-9\\-:\\+]"
    timestamp_re = f"(?P<time>{timechars}+T{timechars}+)"
    sha_re = "(?P<sha>[0-9a-f]{7,12})"
    email_re = "(?P<email>\\S*@\\S*?)"
    pr_desc_re = "(?P<description>.*?)"
    pr_nr_re = "( \\(\\#(?P<pr_nr>[0-9]*)\\))?"
    log_re = f"\\[{timestamp_re} {sha_re} {email_re}\\] {pr_desc_re}{pr_nr_re}$"

    parsed_log = []
    for line in gitlog["log"]:
        if not line:
            continue

        m = re.match(log_re, line)
        if m is None:
            log(f"sysinfo: could not parse gitlog line: `{line}`")
            continue

        log_fields = m.groupdict()
        pr_nr = log_fields["pr_nr"]
        sha = log_fields["sha"]
        log_fields["pr_url"] = f"{pr_url_base}/{pr_nr}" if pr_nr else ""
        log_fields["commit_url"] = f"{commit_url_base}/{sha}"
        log_fields["name"] = name

        parsed_log.append(log_fields)

    return parsed_log
