import tornado.web
from astropy.time import Time
from sqlalchemy.orm import joinedload
from baselayer.app.access import permissions, auth_or_token
from .base import BaseHandler
from ..models import DBSession, Photometry, Comment


class PhotometryHandler(BaseHandler):
    @permissions(['Upload data'])
    def post(self):
        """
        ---
        description: Upload photometry
        parameters:
          - in: path
            name: photometry
            schema: Photometry
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

        # TODO where do we get the instrument info?
        # TODO should filters be a table/plaintext/limited set of strings?
        if 'timeFormat' not in data or 'timeScale' not in data:
            return self.error('Time scale (\'timeScale\') and time format '
                              '(\'timeFormat\') are required parameters.')
        if not isinstance(data['mag'], (list, tuple)):
            data['obsTime'] = [data['obsTime']]
            data['mag'] = [data['mag']]
            data['e_mag'] = [data['e_mag']]
        ids = []
        for i in range(len(data['mag'])):
            if not (data['timeScale'] == 'tcb' and data['timeFormat'] == 'iso'):
                t = Time(data['obsTime'][i],
                         format=data['timeFormat'],
                         scale=data['timeScale'])
                obs_time = t.tcb.iso
            else:
                obs_time = data['obsTime'][i]
            p = Photometry(source_id=data['sourceID'],
                           observed_at=obs_time,
                           mag=data['mag'][i],
                           e_mag=data['e_mag'][i],
                           time_scale='tcb',
                           time_format='iso',
                           instrument_id=data['instrumentID'],
                           lim_mag=data['lim_mag'],
                           filter=data['filter'])
            ids.append(p.id)
            DBSession().add(p)
        DBSession().commit()

        return self.success(data={"ids": ids})

    """TODO any need for get/put/delete?
    @auth_or_token
    def get(self, source_id=None):
        if source_id is not None:
            info = Photometry.get_if_owned_by(source_id, self.current_user,
                                          options=joinedload(Photometry.comments)
                                                  .joinedload(Comment.user))
        else:
            info = list(self.current_user.sources)

        if info is not None:
            return self.success(info)
        else:
            return self.error(f"Could not load source {source_id}",
                              {"source_id": source_id})

    def put(self, source_id):
        data = self.get_json()

        return self.success(action='cesium/FETCH_SOURCES')

    def delete(self, source_id):
        s = Photometry.query.get(source_id)
        DBSession().delete(s)
        DBSession().commit()

    return self.success(action='cesium/FETCH_SOURCES')
    """
