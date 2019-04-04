import tornado.web
from sqlalchemy.orm import joinedload
from baselayer.app.access import permissions, auth_or_token
from baselayer.app.handlers import BaseHandler
from ..models import (DBSession, Comment, Instrument, Photometry, Source,
                      Thumbnail, Token, User)

from functools import reduce


class SourceHandler(BaseHandler):
    @auth_or_token
    def get(self, source_id=None):
        """
        ---
        single:
          description: Retrieve a source
          parameters:
            - in: path
              name: source_id
              required: false
              schema:
                type: integer
          responses:
            200:
              content:
                application/json:
                  schema: SingleSource
            400:
              content:
                application/json:
                  schema: Error
        multiple:
          description: Retrieve all sources
          responses:
            200:
              content:
                application/json:
                  schema:
                    oneOf:
                      - ArrayOfSources
                      - Error
        """
        if source_id is not None:
            source = Source.get_if_owned_by(source_id, self.current_user,
                                            options=[joinedload(Source.comments)
                                                     .joinedload(Comment.user),
                                                     joinedload(Source.thumbnails)
                                                     .joinedload(Thumbnail.photometry)
                                                     .joinedload(Photometry.instrument)
                                                     .joinedload(Instrument.telescope)])
            return self.success(source)
        else:
            if isinstance(self.current_user, Token):
                token = self.current_user
                sources = reduce(set.union,
                                 (set(group.sources) for group in token.groups))
            else:
                sources = self.current_user.sources

        if sources is not None:
            return self.success(list(sources))
        else:
            return self.error(f"Could not load source {source_id}",
                              {"source_id": source_id})

    @permissions(['Manage sources'])
    def post(self):
        """
        ---
        description: Upload a source
        parameters:
          - in: path
            name: source
            schema: Source
        responses:
          200:
            content:
              application/json:
                schema:
                  allOf:
                    - Success
                    - type: object
                      properties:
                        id:
                          type: integer
                          description: New source ID
        """
        data = self.get_json()

        s = Source(ra=data['sourceRA'], dec=data['sourceDec'],
                   red_shift=data.get('sourceRedShift'))
        DBSession().add(s)
        DBSession().commit()

        return self.success({"id": s.id}, 'cesium/FETCH_SOURCES')

    @permissions(['Manage sources'])
    def put(self, source_id):
        """
        ---
        description: Update a source
        parameters:
          - in: path
            name: source
            schema: Source
        responses:
          200:
            content:
              application/json:
                schema: Success
        """
        data = self.get_json()

        s = Source.query.get(source_id)
        s.ra = data['sourceRA']
        s.dec = data['sourceDec']
        s.red_shift = data.get('sourceRedShift')
        DBSession().commit()

        return self.success(action='cesium/FETCH_SOURCES')

    @permissions(['Manage sources'])
    def delete(self, source_id):
        """
        ---
        description: Delete a source
        parameters:
          - in: path
            name: source
            schema:
              Source
        responses:
          200:
            content:
              application/json:
                schema: Success
        """
        s = Source.query.get(source_id)
        DBSession().delete(s)
        DBSession().commit()

        return self.success(action='cesium/FETCH_SOURCES')
