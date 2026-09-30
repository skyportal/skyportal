from skyportal.utils.gitlog import load_gitlog

from ..base import BaseHandler

# We query for more than the number desired (1000 instead of 100), because
# we filter out all commits by noreply@github.com and hope to end up
# with 100 commits still.

max_log_lines = 100


class SysInfoHandler(BaseHandler):
    async def get(self):
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
                                items:
                                  type: string
                                description: Recent git commit lines

        """
        parsed_log = load_gitlog()[:max_log_lines]
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
