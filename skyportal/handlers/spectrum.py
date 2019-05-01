import tornado.web
from sqlalchemy.orm import joinedload
from baselayer.app.access import permissions, auth_or_token
from .base import BaseHandler
from ..models import DBSession, Spectrum, Comment


class SpectrumHandler(BaseHandler):
    @permissions(['Upload data'])
    def post(self):
        data = self.get_json()

        # TODO where do we get the instrument info?
        p = Spectrum(source_id=data['sourceID'],
                     observed_at=data['observed_at'],
                     instrument_id=data['instrumentID'],
                     wavelengths=data['wavlengths'],
                     fluxes=data['fluxes'],
                     errors=data.get('errors', []))
        DBSession().add(p)
        DBSession().commit()

        return self.success(data={"id": s.id}, action='cesium/FETCH_SOURCES')

    """TODO any need for get/put/delete?
    @auth_or_token
    def get(self, source_id=None):
        if source_id is not None:
            info = Spectrum.get_if_owned_by(source_id, self.current_user,
                                          options=joinedload(Spectrum.comments)
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
        s = Spectrum.query.get(source_id)
        DBSession().delete(s)
        DBSession().commit()

    return self.success(action='cesium/FETCH_SOURCES')
    """
