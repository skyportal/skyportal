from baselayer.app.access import auth_or_token
from ..base import BaseHandler
from ...models import DBSession, Source, Localization, SourcesInGCN

from .source import get_sources, MAX_SOURCES_PER_PAGE


class SourcesInGcnHandler(BaseHandler):
    @auth_or_token
    def post(self, dateobs, localization_name):

        data = self.get_json()
        print(data)
        if 'sourceId' not in data:
            return self.error("Missing source_id")
        if 'confirmed' not in data and 'rejected' not in data:
            return self.error("Missing confirmed or rejected")

        source_id = data.get('sourceId')
        confirmed = data.get('confirmed', False)
        rejected = data.get('rejected', False)
        start_date = data.get('startDate')
        end_date = data.get('endDate')

        if not isinstance(source_id, str):
            return self.error("source_id must be an integer")
        if not isinstance(confirmed, bool):
            return self.error("confirmed must be a boolean")
        if not isinstance(rejected, bool):
            return self.error("rejected must be a boolean")

        if start_date is None:
                return self.error(message="Missing start_date")
        if end_date is None:
            return self.error(message="Missing end_date")
        if confirmed is False and rejected is False:
            return self.error("Source must be either confirmed or rejected")
        if confirmed is True and rejected is True:
            return self.error("Source must be either confirmed or rejected, not both")

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

        source_in_gcn = SourcesInGCN(obj_id=source_id, localization_id=localization.id, confirmed=confirmed, rejected=rejected)
        DBSession.add(source_in_gcn)
        DBSession.commit()
        return self.success(data={'id': source_in_gcn.id})

    @auth_or_token
    def get(self, dateobs, localization_name):
        start_date = self.get_query_argument('startDate')
        end_date = self.get_query_argument('endDate')
        # get all sources that have been confirmed or rejected in this localization
        localization = Localization.query.filter(Localization.localization_name == localization_name, Localization.dateobs == dateobs).first()
        if not localization:
            return self.error("Localization not found")

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
            )
            sources = sources['sources']
        
        sources_ids = [source['id'] for source in sources]
        print(sources_ids)
        sources_in_gcn = SourcesInGCN.query.filter(SourcesInGCN.localization_id == Localization.id).filter(Localization.localization_name == localization_name, Localization.dateobs == dateobs).filter(SourcesInGCN.obj_id.in_(sources_ids)).all()
        return self.success(data=sources_in_gcn)

    @auth_or_token
    def put(self, dateobs, localization_name, source_id):
        data = self.get_json()
        confirmed = data.get('confirmed', False)
        rejected = data.get('rejected', False)

        if not isinstance(source_id, str):
            return self.error("source_id must be an integer")
        if not isinstance(confirmed, bool):
            return self.error("confirmed must be a boolean")
        if not isinstance(rejected, bool):
            return self.error("rejected must be a boolean")

        if confirmed is False and rejected is False:
            return self.error("Source must be either confirmed or rejected")

        if confirmed is True and rejected is True:
            return self.error("Source must be either confirmed or rejected, not both")

        localization = Localization.query.filter(Localization.localization_name == localization_name, Localization.dateobs == dateobs).first()
        if not localization:
            return self.error("Localization not found")

        source_in_gcn = SourcesInGCN.query.filter(SourcesInGCN.obj_id == source_id, SourcesInGCN.localization_id == localization.id).first()
        if not source_in_gcn:
            return self.error("This source is not confirmed or rejected in this localization yet")
        print(source_in_gcn)
        if confirmed is True:
            source_in_gcn.confirm()
        if rejected is True:
            source_in_gcn.reject()

        DBSession.commit()
        return self.success(data={'id': source_in_gcn.id})

    @auth_or_token
    def delete(self, dateobs, localization_name, source_id):
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
