import tornado.web
from sqlalchemy.orm import joinedload
from baselayer.app.access import permissions
from baselayer.app.handlers.base import BaseHandler
from ..models import DBSession, Photometry, Comment


class PhotometryHandler(BaseHandler):
    @permissions(['Upload data'])
    def post(self):
        data = self.get_json()

        # TODO where do we get the instrument info?
        # TODO should filters be a table/plaintext/limited set of strings?
        p = Photometry(source_id=data['sourceID'], observed_at=data['obsTime'], 
                       instrument_id=data['instrumentID'], mag=data['mag'],
                       e_mag=data['e_mag'], lim_mag=data['lim_mag'],
                       filter=data['filter'])
        DBSession().add(p)
        DBSession().commit()

        return self.success({"id": s.id}, 'cesium/FETCH_SOURCES')

    """TODO any need for get/put/delete?
    @tornado.web.authenticated
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
