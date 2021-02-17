from baselayer.app.access import auth_or_token
from ..base import BaseHandler
from ...models import (
    Obj,
    Source,
    Candidate,
    User,
    Token,
    Group,
    Photometry,
    Spectrum,
)


class StatsHandler(BaseHandler):
    @auth_or_token
    def get(self):
        """
        ---
        description: Retrieve basic DB statistics
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
                            Number of candidates:
                              type: integer
                              description: Number of rows in candidates table
                            Number of objs:
                              type: integer
                              description: Number of rows in objs table
                            Number of sources:
                              type: integer
                              description: Number of rows in sources table
                            Number of photometry:
                              type: integer
                              description: Number of rows in photometry table
                            Number of spectra:
                              type: integer
                              description: Number of rows in spectra table
                            Number of groups:
                              type: integer
                              description: Number of rows in groups table
                            Number of users:
                              type: integer
                              description: Number of rows in users table
                            Number of tokens:
                              type: integer
                              description: Number of rows in tokens table
                            Oldest candidate creation datetime:
                              type: string
                              description: |
                                Datetime string corresponding to created_at column of
                                the oldest row in the candidates table.
                            Newest candidate creation datetime:
                              type: string
                              description: |
                                Datetime string corresponding to created_at column of
                                the newest row in the candidates table.
        """
        data = {}
        data["Number of candidates"] = Candidate.query.count()
        data["Number of sources"] = Source.query.count()
        data["Number of objs"] = Obj.query.count()
        data["Number of photometry"] = Photometry.query.count()
        data["Number of spectra"] = Spectrum.query.count()
        data["Number of groups"] = Group.query.count()
        data["Number of users"] = User.query.count()
        data["Number of tokens"] = Token.query.count()
        cand = Candidate.query.order_by(Candidate.created_at).first()
        data["Oldest candidate creation datetime"] = (
            cand.created_at if cand is not None else None
        )
        cand = Candidate.query.order_by(Candidate.created_at.desc()).first()
        data["Newest candidate creation datetime"] = (
            cand.created_at if cand is not None else None
        )
        return self.success(data=data)
