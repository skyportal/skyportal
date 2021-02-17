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
                          numCandidates:
                            type: integer
                            description: Number of rows in candidates table
                          numObjs:
                            type: integer
                            description: Number of rows in objs table
                          numSources:
                            type: integer
                            description: Number of rows in sources table
                          numPhotometry:
                            type: integer
                            description: Number of rows in photometry table
                          numSpectra:
                            type: integer
                            description: Number of rows in spectra table
                          numGroups:
                            type: integer
                            description: Number of rows in groups table
                          numUsers:
                            type: integer
                            description: Number of rows in users table
                          numTokens:
                            type: integer
                            description: Number of rows in tokens table
                          oldestCandidateCreatedAt:
                            type: string
                            description: |
                              Datetime string corresponding to created_at column of
                              the oldest row in the candidates table.
                          newestCandidateCreatedAt:
                            type: string
                            description: |
                              Datetime string corresponding to created_at column of
                              the newest row in the candidates table.
        """
        data = {}
        data["numCandidates"] = Candidate.query.count()
        data["numSources"] = Source.query.count()
        data["numObjs"] = Obj.query.count()
        data["numPhotometry"] = Photometry.query.count()
        data["numSpectra"] = Spectrum.query.count()
        data["numGroups"] = Group.query.count()
        data["numUsers"] = User.query.count()
        data["numTokens"] = Token.query.count()
        cand = Candidate.query.order_by(Candidate.created_at).first()
        data["oldestCandidateCreatedAt"] = cand.created_at if cand is not None else None
        cand = Candidate.query.order_by(Candidate.created_at.desc()).first()
        data["newestCandidateCreatedAt"] = cand.created_at if cand is not None else None
        return self.success(data=data)
