from astropy.time import Time
from marshmallow.exceptions import ValidationError
from baselayer.app.access import permissions, auth_or_token
from ..base import BaseHandler
from .thumbnail import create_thumbnail
from ...models import (
    DBSession, Candidate, Photometry, Instrument, Source
)


class PhotometryHandler(BaseHandler):
    @permissions(['Upload data'])
    def post(self):
        """
        ---
        description: Upload photometry
        requestBody:
          content:
            application/json:
              schema: PhotometryNoID
        responses:
          200:
            content:
              application/json:
                schema:
                  allOf:
                    - Success
                    - type: object
                      properties:
                        ids:
                          type: array
                          description: List of new photometry IDs
        """
        data = self.get_json()

        # TODO should filters be a table/plaintext/limited set of strings?
        if 'time_format' not in data or 'time_scale' not in data:
            return self.error('Time scale (\'time_scale\') and time format '
                              '(\'time_format\') are required parameters.')
        if not isinstance(data['mag'], (list, tuple)):
            data['observed_at'] = [data['observed_at']]
            data['mag'] = [data['mag']]
            data['e_mag'] = [data['e_mag']]
            data['lim_mag'] = [data['lim_mag']]
            data['filter'] = [data['filter']]
        ids = []
        instrument = Instrument.query.get(data['instrument_id'])
        if not instrument:
            return self.error('Invalid instrument ID')
        source_id = data.get("source_id", None)
        candidate_id = data.get('candidate_id', None)
        if candidate_id is not None:
            candidate = Candidate.get_if_owned_by(candidate_id, self.current_user)
            if candidate is None:
                return self.error("Invalid candidate ID")
        else:
            # We want candidates to stay up to date with associated sources
            candidate = Candidate.get_if_owned_by(source_id, self.current_user)
        if source_id is not None:
            source = Source.get_if_owned_by(source_id, self.current_user)
            if source is None:
                return self.error("Invalid source ID")
        else:
            # We want sources to stay up to date with associated candidates
            source = Source.get_if_owned_by(candidate_id, self.current_user)
        if not (source or candidate):
            return self.error('Invalid source/candidate ID')
        converted_times = []
        for i in range(len(data['mag'])):
            t = Time(data['observed_at'][i],
                     format=data['time_format'],
                     scale=data['time_scale'])
            observed_at = t.tcb.iso
            converted_times.append(observed_at)
            p = Photometry(source=source,
                           candidate=candidate,
                           observed_at=observed_at,
                           mag=data['mag'][i],
                           e_mag=data['e_mag'][i],
                           time_scale='tcb',
                           time_format='iso',
                           instrument=instrument,
                           lim_mag=data['lim_mag'][i],
                           filter=data['filter'][i])
            DBSession().add(p)
            DBSession().flush()
            ids.append(p.id)
        if 'thumbnails' in data:
            p = Photometry.query.get(ids[0])
            for thumb in data['thumbnails']:
                create_thumbnail(thumb['data'], thumb['ttype'], source.id, p)
        if source is not None:
            source.last_detected = max(converted_times
                                       + [source.last_detected if
                                          source.last_detected is not None else '0'])
        if candidate is not None:
            candidate.last_detected = max(converted_times
                                          + [candidate.last_detected if
                                             candidate.last_detected is not None else '0'])
        DBSession().commit()

        return self.success(data={"ids": ids})

    @auth_or_token
    def get(self, photometry_id):
        """
        ---
        description: Retrieve photometry
        parameters:
          - in: path
            name: photometry_id
            required: true
            schema:
              type: integer
        responses:
          200:
            content:
              application/json:
                schema: SinglePhotometry
          400:
            content:
              application/json:
                schema: Error
        """
        p = Photometry.query.get(photometry_id)
        if p is None:
            return self.error('Invalid photometry ID')
        # Ensure user/token has access to parent source/candidate
        try:
            _ = Source.get_if_owned_by(p.source_id, self.current_user)
        except (ValueError, AttributeError, TypeError):
            _ = Candidate.get_if_owned_by(p.candidate_id, self.current_user)

        return self.success(data={"photometry": p})

    @permissions(['Manage sources'])
    def put(self, photometry_id):
        """
        ---
        description: Update photometry
        parameters:
          - in: path
            name: photometry_id
            required: true
            schema:
              type: integer
        requestBody:
          content:
            application/json:
              schema: PhotometryNoID
        responses:
          200:
            content:
              application/json:
                schema: Success
          400:
            content:
              application/json:
                schema: Error
        """
        # Ensure user/token has access to parent source/candidate
        try:
            _ = Source.get_if_owned_by(Photometry.query.get(photometry_id).source_id,
                                       self.current_user)
        except (ValueError, AttributeError, TypeError):
            _ = Candidate.get_if_owned_by(Photometry.query.get(photometry_id).candidate_id,
                                          self.current_user)

        data = self.get_json()
        data['id'] = photometry_id

        schema = Photometry.__schema__()
        try:
            schema.load(data)
        except ValidationError as e:
            return self.error('Invalid/missing parameters: '
                              f'{e.normalized_messages()}')
        DBSession().commit()

        return self.success()

    @permissions(['Manage sources'])
    def delete(self, photometry_id):
        """
        ---
        description: Delete photometry
        parameters:
          - in: path
            name: photometry_id
            required: true
            schema:
              type: integer
        responses:
          200:
            content:
              application/json:
                schema: Success
          400:
            content:
              application/json:
                schema: Error
        """
        # Ensure user/token has access to parent source/candidate
        try:
            _ = Source.get_if_owned_by(Photometry.query.get(photometry_id).source_id,
                                       self.current_user)
        except (ValueError, AttributeError, TypeError):
            _ = Candidate.get_if_owned_by(Photometry.query.get(photometry_id).candidate_id,
                                          self.current_user)

        DBSession.query(Photometry).filter(Photometry.id == int(photometry_id)).delete()
        DBSession().commit()

        return self.success()
