import glob
import itertools
import json

from skyportal.utils.gitlog import get_gitlog, parse_gitlog

from ..base import BaseHandler

# This file is generated with `utils.get_gitlog`.
#
# We query for more than the number desired (1000 instead of 100), because
# we filter out all commits by noreply@github.com and hope to end up
# with 100 commits still.

gitlog_files = "data/gitlog*.json"
max_log_lines = 100


class SysInfoHandler(BaseHandler):
    def get(self):
        """
        ---
        summary: Retrieve system/deployment info
        description: Retrieve system/deployment info
        tags:
          - system info
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
                            gitlog:
                                type: array
                                description: Recent git commit lines

        """
        # if another build system has written a gitlog file, use it
        gitlogs = []
        for gitlog in glob.glob(gitlog_files):
            with open(gitlog) as f:
                gitlogs.append(json.load(f))
        if not gitlogs:
            gitlogs = [get_gitlog()]

        parsed_logs = [parse_gitlog(gitlog) for gitlog in gitlogs]
        parsed_log = list(itertools.chain(*parsed_logs))
        parsed_log = sorted(parsed_log, key=lambda x: x["time"], reverse=True)
        parsed_log = parsed_log[:max_log_lines]
        parsed_log = [
            entry
            for entry in parsed_log
            if not (entry["description"].lower().startswith(("bump", "pin")))
        ]

        return self.success(
            data={
                "gitlog": parsed_log,
            }
        )
