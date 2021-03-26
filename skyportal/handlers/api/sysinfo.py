import glob
import json
import itertools

from baselayer.app.env import load_env
from baselayer.app.access import auth_or_token
from ..base import BaseHandler

from skyportal.models import cosmo
from skyportal.utils.gitlog import get_gitlog, parse_gitlog


_, cfg = load_env()

# This file is generated with `utils.get_gitlog`.
#
# We query for more than the number desired (1000 instead of 100), because
# we filter out all commits by noreply@github.com and hope to end up
# with 100 commits still.

gitlog_files = "data/gitlog*.json"
max_log_lines = 100


class SysInfoHandler(BaseHandler):
    @auth_or_token
    def get(self):
        """
        ---
        description: Retrieve system/deployment info
        tags:
          - system_info
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
        gitlogs = []
        for gitlog in glob.glob(gitlog_files):
            with open(gitlog, "r") as f:
                gitlogs.append(json.load(f))
        if not gitlogs:
            gitlogs = [get_gitlog()]

        parsed_logs = [parse_gitlog(gitlog) for gitlog in gitlogs]
        parsed_log = list(itertools.chain(*parsed_logs))
        parsed_log = list(sorted(parsed_log, key=lambda x: x['time'], reverse=True))
        parsed_log = parsed_log[:max_log_lines]
        parsed_log = [
            entry
            for entry in parsed_log
            if not (entry['description'].lower().startswith(('bump', 'pin')))
        ]

        return self.success(
            data={
                "invitationsEnabled": cfg["invitations.enabled"],
                "cosmology": str(cosmo),
                "cosmoref": cosmo.__doc__,
                "gitlog": parsed_log,
            }
        )
