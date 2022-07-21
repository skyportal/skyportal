from numpy import isin
from baselayer.app.access import auth_or_token
from ..base import BaseHandler
from ...models import DBSession, Source, Localization, SourcesInGCN

from .source import get_sources, MAX_SOURCES_PER_PAGE


class SourcesInGcnHandler(BaseHandler):
    @auth_or_token
    def post(self, dateobs):

        data = self.get_json()
        print(data)
        if 'localizationName' not in data:
            return self.error("Missing required parameter: localization_name")
        if 'sourceId' not in data:
            return self.error("Missing source_id")
        if 'confirmedOrRejected' not in data:
            return self.error("Missing confirmed or rejected")

        localization_name = data['localizationName']
        source_id = data.get('sourceId')
        confirmed_or_rejected = data.get('confirmedOrRejected', False)
        start_date = data.get('startDate')
        end_date = data.get('endDate')

        if not isinstance(localization_name, str):
            return self.error("localizationName must be a string")
        if not isinstance(source_id, str):
            return self.error("sourceId must be an integer")
        if not isinstance(confirmed_or_rejected, bool):
            return self.error("confirmed_or_rejected must be a boolean")

        if start_date is None:
                return self.error(message="Missing startDate")
        if end_date is None:
            return self.error(message="Missing endDate")

        with self.Session() as session:
            sources = get_sources(
                user_id=self.associated_user_object.id,
                session=session,
                first_detected_date=start_date,
                last_detected_date=end_date,
                localization_dateobs=dateobs,
                localization_name=localization_name,
                localization_cumprob=0.95,
                page_number=1,
                num_per_page=MAX_SOURCES_PER_PAGE,
                sourceID=source_id,
            )

            sources = sources['sources']

        if len(sources) == 0:
            return self.error("No sources found")

        localization = Localization.query.filter(Localization.localization_name == localization_name, Localization.dateobs == dateobs).first()
        if not localization:
            return self.error("Localization not found")

        source_in_gcn = SourcesInGCN.query.filter(SourcesInGCN.obj_id == source_id, SourcesInGCN.localization_id == localization.id).first()
        if source_in_gcn:
            return self.error("Source is already confirmed or rejected in this localization")

        source_in_gcn = SourcesInGCN(obj_id=source_id, localization_id=localization.id, confirmed_or_rejected=confirmed_or_rejected)
        DBSession.add(source_in_gcn)
        DBSession.commit()
        return self.success(data={'id': source_in_gcn.id})

    @auth_or_token
    def get(self, dateobs):
        localization_name = self.get_query_argument('localizationName')
        if not isinstance(localization_name, str):
            return self.error("localizationName must be a string")
        # get all sources that have been confirmed or rejected in this localization
        localization = Localization.query.filter(Localization.localization_name == localization_name, Localization.dateobs == dateobs).first()
        if not localization:
            return self.error("Localization not found")
        sources_in_gcn = SourcesInGCN.query.filter(SourcesInGCN.localization_id == Localization.id).filter(Localization.localization_name == localization_name, Localization.dateobs == dateobs).all()
        return self.success(data=sources_in_gcn)

    @auth_or_token
    def put(self, dateobs, source_id):
        data = self.get_json()
        localization_name = data.get('localizationName')
        confirmed_or_rejected = data.get('confirmedOrRejected', False)
        if not isinstance(localization_name, str):
            return self.error("localizationName must be a string")
        if not isinstance(source_id, str):
            return self.error("sourceId must be an integer")
        if not isinstance(confirmed_or_rejected, bool):
            return self.error("confirmed_or_rejected must be a boolean")

        localization = Localization.query.filter(Localization.localization_name == localization_name, Localization.dateobs == dateobs).first()
        if not localization:
            return self.error("Localization not found")

        source_in_gcn = SourcesInGCN.query.filter(SourcesInGCN.obj_id == source_id, SourcesInGCN.localization_id == localization.id).first()
        if not source_in_gcn:
            return self.error("This source is not confirmed or rejected in this localization yet")
        source_in_gcn.confirmed_or_rejected = confirmed_or_rejected

        DBSession.commit()
        return self.success(data={'id': source_in_gcn.id})

    @auth_or_token
    def delete(self, dateobs, source_id):
        localization_name = self.get_query_argument('localizationName')
        if not isinstance(localization_name, str):
            return self.error("localizationName must be a string")
        if not isinstance(source_id, int):
            return self.error("source_id must be an integer")

        localization = Localization.query.filter(Localization.localization_name == localization_name, Localization.dateobs == dateobs).first()
        if not localization:
            return self.error("Localization not found")

        source_in_gcn = SourcesInGCN.query.filter(SourcesInGCN.source_id == source_id, SourcesInGCN.localization_id == localization.id).first()
        if not source_in_gcn:
            return self.error("This source is not confirmed or rejected in this localization yet")

        DBSession.delete(source_in_gcn)
        DBSession.commit()
        return self.success(data={'id': source_in_gcn.id})
