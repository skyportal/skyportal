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
pr_url = "https://github.com/skyportal/skyportal/pull/"


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
                    "--pretty=format:'[%ci %h] %s'",
                    f"-{default_log_lines}",
                ],
                capture_output=True,
                universal_newlines=True,
            )
            loginfo = p.stdout

        raw_gitlog = loginfo.splitlines()
        gitlog = []

        pr_re = r'\(#[0-9]+\)$'

        for commit in raw_gitlog:
            # remove leading and trailing quote
            result = commit[1:-1]
            pr_number = re.search(pr_re, result)
            if pr_number:
                pr_str = result[pr_number.start() :]  # noqa: E203
                pr_nr = pr_str[2:-1]
                pr_link = f"""
                (<a
                  target='_blank'
                  rel='noopener noreferrer'
                  href={pr_url + pr_nr}>#{pr_nr}</a>)
                """
                result = result[: pr_number.start()] + pr_link  # noqa: E203
            gitlog.append(result)

        return self.success(
            data={
                "invitationsEnabled": cfg["invitations.enabled"],
                "cosmology": str(cosmo),
                "cosmoref": cosmo.__doc__,
                "gitlog": gitlog,
            }
        )
