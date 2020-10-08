import os
import subprocess

from baselayer.app.env import load_env
from baselayer.app.access import auth_or_token
from ..base import BaseHandler

from skyportal.models import cosmo
from skyportal.utils import gitlog


_, cfg = load_env()

# This file is generated with
#
#   git log --no-merges --first-parent \
#           --pretty='format:[%cI %h %cE] %s' -1000
#
# We query for more than the number desired (1000 instead of 100), because
# we filter out all commits by noreply@github.com and hope to end up
# with 100 commits still.


gitlog_file = "data/gitlog.txt"
max_log_lines = 100


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
                    "--pretty=format:[%cI %h %cE] %s",
                    f"-{max_log_lines * 10}",
                ],
                capture_output=True,
                universal_newlines=True,
            )
            loginfo = p.stdout

        parsed_log = gitlog.parse_gitlog(loginfo.splitlines())
        parsed_log = [
            entry
            for entry in parsed_log
            if not (entry['description'].lower().startswith(('bump', 'pin')))
        ]
        parsed_log = parsed_log[:max_log_lines]

        return self.success(
            data={
                "invitationsEnabled": cfg["invitations.enabled"],
                "cosmology": str(cosmo),
                "cosmoref": cosmo.__doc__,
                "gitlog": parsed_log,
            }
        )
