import os
import subprocess
import re

from baselayer.app.env import load_env
from baselayer.app.access import auth_or_token
from ..base import BaseHandler
from skyportal.models import cosmo


_, cfg = load_env()
default_log_lines = 25
gitlog_file = "data/gitlog.txt"
pr_url_base = "https://github.com/skyportal/skyportal/pull"
commit_url_base = "https://github.com/skyportal/skyportal/commit"


class SysInfoHandler(BaseHandler):
    @auth_or_token
    def get(self):
        """
        ---
        description: Retrieve system/deployment info
        responses:
          200:
            content:
              application/json:
                schema:
                  allOf:
                    - $ref: '#/components/schemas/Success'
                    - type: object
                      properties:
                        data:
                          type: object
                        properties:
                          invitationsEnabled:
                            type: boolean
                            description: |
                              Boolean indicating whether new user invitation pipeline
                              is enabled in current deployment.
                          gitlog:
                              type: array
                              description: Recent git commit lines
                          cosmology:
                              type: string
                              description: Details of the cosmology used here
                          cosmoref:
                              type: string
                              description: Reference for the cosmology used.
        """
        # if another build system has written a gitlog file, use it
        loginfo = ""
        if os.path.exists(gitlog_file):
            with open(gitlog_file, "r") as spgl:
                loginfo = spgl.read()
        if loginfo == "":
            p = subprocess.run(
                [
                    "git",
                    "--git-dir=.git",
                    "log",
                    "--no-merges",
                    "--first-parent",
                    "--pretty=format:[%ci %h] %s",
                    f"-{default_log_lines}",
                ],
                capture_output=True,
                universal_newlines=True,
            )
            loginfo = p.stdout

        raw_gitlog = loginfo.splitlines()

        timestamp_re = '(?P<time>[0-9\\-:].*)'
        sha_re = '(?P<sha>[0-9a-f]{8})'
        pr_desc_re = '(?P<pr_desc>.*?)'
        pr_nr_re = '( \\(\\#(?P<pr_nr>[0-9]*)\\))?'
        log_re = f'\\[{timestamp_re} {sha_re}\\] {pr_desc_re}{pr_nr_re}$'

        gitlog = []
        for line in raw_gitlog:
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

        return self.success(
            data={
                "invitationsEnabled": cfg["invitations.enabled"],
                "cosmology": str(cosmo),
                "cosmoref": cosmo.__doc__,
                "gitlog": gitlog,
            }
        )
