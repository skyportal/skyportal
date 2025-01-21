import subprocess

from baselayer.app.access import auth_or_token

from ....models import DBSession, Source
from ...base import BaseHandler


class DBInfoHandler(BaseHandler):
    @auth_or_token
    def get(self):
        """
        ---
        description: Determine whether sources table is empty.
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
                            source_table_empty:
                              type: boolean
                              description: Boolean indicating whether source table is empty
                            postgres_version:
                              type: string
                              description: Installed Postgres version
        """
        p = subprocess.Popen(["psql", "--version"], stdout=subprocess.PIPE)
        out, err = p.communicate()
        postgres_version = out.decode("utf-8").split()[2]
        info = {
            "source_table_empty": DBSession.query(Source).first() is None,
            "postgres_version": postgres_version,
        }
        return self.success(data=info)
