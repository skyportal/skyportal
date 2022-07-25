from baselayer.app.access import auth_or_token, permissions
from skyportal.models.gcn import GcnEvent
from ..base import BaseHandler
from ...models import DBSession, Localization, SourcesInGCN

from .source import get_sources, MAX_SOURCES_PER_PAGE


class SourcesInGcnHandler(BaseHandler):
    @permissions(['Manage GCNs'])
    def post(self, dateobs):
        data = self.get_json()
        print(data)
        if 'localizationName' not in data:
            return self.error("Missing required parameter: localization_name")
        if 'localizationCumprob' not in data:
            return self.error("Missing required parameter: localization_cumprob")
        if 'sourceId' not in data:
            return self.error("Missing source_id")
        if 'confirmedOrRejected' not in data:
            return self.error("Missing confirmed or rejected")

        localization_name = data['localizationName']
        localization_cumprob = data['localizationCumprob']
        source_id = data.get('sourceId')
        confirmed_or_rejected = data.get('confirmedOrRejected', False)
        start_date = data.get('startDate')
        end_date = data.get('endDate')

        if localization_cumprob is not None:
            localization_cumprob = float(localization_cumprob)

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
                localization_cumprob=localization_cumprob,
                page_number=1,
                num_per_page=MAX_SOURCES_PER_PAGE,
                sourceID=source_id,
            )

            sources = sources['sources']

        if len(sources) == 0:
            return self.error("No sources found")

        localization = Localization.query.filter(
            Localization.localization_name == localization_name,
            Localization.dateobs == dateobs,
        ).first()
        if not localization:
            return self.error("Localization not found")

        source_in_gcn = SourcesInGCN.query.filter(
            SourcesInGCN.obj_id == source_id,
            SourcesInGCN.dateobs == dateobs,
        ).first()
        if source_in_gcn:
            return self.error(
                "Source is already confirmed or rejected in this localization"
            )

        source_in_gcn = SourcesInGCN(
            obj_id=source_id,
            dateobs=dateobs,
            confirmed_or_rejected=confirmed_or_rejected,
        )
        DBSession.add(source_in_gcn)
        DBSession.commit()
        return self.success(data={'id': source_in_gcn.id})

    @auth_or_token
    def get(self, dateobs):
        sources_id_list = self.get_query_argument('sourcesIdList', '')

        if not isinstance(sources_id_list, str):
            return self.error("sourcesIdList must be a comma separated string")

        sources_id_list = sources_id_list.split(',')

        gcn_event = GcnEvent.query.filter(GcnEvent.dateobs == dateobs).first()
        if not gcn_event:
            return self.error(f"GCN event not found for dateobs: {dateobs}")

        if len(sources_id_list) == 0:
            sources_in_gcn = SourcesInGCN.query.filter(
                Localization.dateobs == dateobs
            ).all()
            return self.success(data=sources_in_gcn)
        else:
            sources_in_gcn = (
                SourcesInGCN.query.filter(
                    Localization.dateobs == dateobs,
                )
                .filter(SourcesInGCN.obj_id.in_(sources_id_list))
                .all()
            )
            return self.success(data=sources_in_gcn)

    @permissions(['Manage GCNs'])
    def put(self, dateobs, source_id):
        data = self.get_json()
        confirmed_or_rejected = data.get('confirmedOrRejected', False)
        if not isinstance(source_id, str):
            return self.error("sourceId must be an integer")
        if not isinstance(confirmed_or_rejected, bool):
            return self.error("confirmed_or_rejected must be a boolean")

        gcn_event = GcnEvent.query.filter(GcnEvent.dateobs == dateobs).first()
        if not gcn_event:
            return self.error(f"GCN event not found for dateobs: {dateobs}")

        source_in_gcn = SourcesInGCN.query.filter(
            SourcesInGCN.obj_id == source_id,
            SourcesInGCN.dateobs == dateobs,
        ).first()
        if not source_in_gcn:
            return self.error(
                "This source is not confirmed or rejected in this localization yet"
            )
        source_in_gcn.confirmed_or_rejected = confirmed_or_rejected

        DBSession.commit()
        return self.success(data={'id': source_in_gcn.id})

    @permissions(['Manage GCNs'])
    def delete(self, dateobs, source_id):
        if not isinstance(source_id, str):
            return self.error("source_id must be a string")

        gcn_event = GcnEvent.query.filter(GcnEvent.dateobs == dateobs).first()
        if not gcn_event:
            return self.error(f"GCN event not found for dateobs: {dateobs}")

        source_in_gcn = SourcesInGCN.query.filter(
            SourcesInGCN.obj_id == source_id,
            SourcesInGCN.dateobs == dateobs,
        ).first()
        if not source_in_gcn:
            return self.error(
                "This source is not confirmed or rejected in this localization yet"
            )

        DBSession.delete(source_in_gcn)
        DBSession.commit()
        return self.success(data={'id': source_in_gcn.id})


class SourceInGcnsHandler(BaseHandler):
    @auth_or_token
    def get(self, source_id):
        source_in_gcn = (
            SourcesInGCN.query.filter(SourcesInGCN.obj_id == source_id)
            .filter(SourcesInGCN.confirmed_or_rejected.is_(True))
            .all()
        )

        # transform it in a list of gcn events (list of dateobs)
        gcn_events = []
        for source in source_in_gcn:
            gcn_events.append(source.dateobs)
        return self.success(data={"gcns": gcn_events})
