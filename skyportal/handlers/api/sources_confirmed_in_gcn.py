from baselayer.app.access import auth_or_token, permissions
from ..base import BaseHandler
from .source import get_sources, MAX_SOURCES_PER_PAGE
from ...models import GcnEvent, Localization, SourcesConfirmedInGCN
from ...utils.UTCTZnaiveDateTime import UTCTZnaiveDateTime

import arrow
from marshmallow import Schema
from marshmallow.exceptions import ValidationError


class SourcesConfirmedInGCNHandler(BaseHandler):
    @auth_or_token
    def get(self, dateobs, source_id=None):

        # try except parsing the dateobs with arrow
        try:
            arrow.get(dateobs).datetime
        except Exception:
            return self.error(f'Invalid dateobs: {dateobs}')
        sources_id_list = self.get_query_argument('sourcesIDList', '')
        if not isinstance(sources_id_list, str):
            return self.error("sourcesIDList must be a comma separated string")
        if sources_id_list != '':
            try:
                sources_id_list = [
                    source_id.strip() for source_id in sources_id_list.split(',')
                ]
            except ValueError:
                return self.error(
                    "some of the sourceIDs in the sourcesIDList are not valid strings"
                )

        if source_id is not None:
            # if a source_id is passed as a parameter, we only want to return the source_id, we ignore the query argument sourcesIDList
            sources_id_list = [source_id]

        with self.Session() as session:
            try:
                stmt = GcnEvent.select(session.user_or_token).where(
                    GcnEvent.dateobs == dateobs
                )
                gcn_event = session.scalars(stmt).first()
                if not gcn_event:
                    return self.error(f"GCN event not found for dateobs: {dateobs}")

                if len(sources_id_list) == 0:
                    stmt = SourcesConfirmedInGCN.select(session.user_or_token).where(
                        Localization.dateobs == dateobs
                    )
                else:
                    stmt = SourcesConfirmedInGCN.select(session.user_or_token).where(
                        Localization.dateobs == dateobs,
                        SourcesConfirmedInGCN.obj_id.in_(sources_id_list),
                    )
                sources_in_gcn = session.scalars(stmt).all()
            except Exception as e:
                return self.error(str(e))

        return self.success(data=sources_in_gcn)

    @permissions(['Manage GCNs'])
    def post(self, dateobs):
        data = self.get_json()
        try:
            arrow.get(dateobs).datetime
        except Exception:
            return self.error(f'Invalid dateobs: {dateobs}')
        if 'localization_name' not in data:
            return self.error("Missing required parameter: localization_name")
        if 'localization_cumprob' not in data:
            return self.error("Missing required parameter: localization_cumprob")
        if 'source_id' not in data:
            return self.error("Missing source_id")
        if 'confirmed_or_rejected' not in data:
            return self.error("Missing confirmed_or_rejected")
        if 'start_date' not in data:
            return self.error("Missing start_date")
        if 'end_date' not in data:
            return self.error("Missing end_date")

        localization_name = data['localization_name']
        localization_cumprob = data['localization_cumprob']
        source_id = data.get('source_id')
        confirmed_or_rejected = data.get('confirmed_or_rejected')
        start_date = data.get('start_date')
        end_date = data.get('end_date')

        if start_date is None:
            return self.error(message="Missing startDate")
        if end_date is None:
            return self.error(message="Missing endDate")

        class Validator(Schema):
            start_date = UTCTZnaiveDateTime(required=False, missing=None)
            end_date = UTCTZnaiveDateTime(required=False, missing=None)

        validator_instance = Validator()
        params_to_be_validated = {}
        params_to_be_validated['start_date'] = start_date
        params_to_be_validated['end_date'] = end_date
        try:
            validated = validator_instance.load(params_to_be_validated)
        except ValidationError as e:
            return self.error(f'Error parsing query params: {e.args[0]}.')
        start_date = validated['start_date']
        end_date = validated['end_date']

        if localization_cumprob is None:
            return self.error("Missing required parameter: localization_cumprob")
        try:
            localization_cumprob = float(localization_cumprob)
        except ValueError:
            return self.error("localization_cumprob must be a float")
        if not isinstance(localization_name, str):
            return self.error("localizationName must be a string")
        if not isinstance(source_id, str):
            return self.error("sourceID must be an integer")

        if confirmed_or_rejected is None:
            return self.error("Missing required parameter: confirmed_or_rejected")
        try:
            confirmed_or_rejected = bool(confirmed_or_rejected)
        except ValueError:
            return self.error("confirmed_or_rejected must be a boolean")

        with self.Session() as session:
            try:
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

                stmt = Localization.select(session.user_or_token).where(
                    Localization.localization_name == localization_name,
                    Localization.dateobs == dateobs,
                )
                localization = session.scalars(stmt).first()
                if not localization:
                    return self.error("Localization not found")

                stmt = SourcesConfirmedInGCN.select(session.user_or_token).where(
                    SourcesConfirmedInGCN.dateobs == dateobs,
                    SourcesConfirmedInGCN.obj_id == source_id,
                )
                source_in_gcn = session.scalars(stmt).first()
                if source_in_gcn:
                    return self.error(
                        "Source is already confirmed or rejected in this localization"
                    )

                source_in_gcn = SourcesConfirmedInGCN(
                    obj_id=source_id,
                    dateobs=dateobs,
                    confirmed=confirmed_or_rejected,
                )
                session.add(source_in_gcn)
                session.commit()
                source_in_gcn_id = source_in_gcn.id
            except Exception as e:
                session.rollback()
                return self.error(str(e))

        return self.success(data={'id': source_in_gcn_id})

    @permissions(['Manage GCNs'])
    def put(self, dateobs, source_id):
        data = self.get_json()
        confirmed_or_rejected = data.get('confirmed_or_rejected', False)
        try:
            arrow.get(dateobs).datetime
        except Exception:
            return self.error(f'Invalid dateobs: {dateobs}')
        if not isinstance(source_id, str):
            return self.error("source_id must be a string")
        if not isinstance(confirmed_or_rejected, bool):
            return self.error("confirmed_or_rejected must be a boolean")

        source_id = source_id.strip()

        with self.Session() as session:
            try:
                stmt = GcnEvent.select(session.user_or_token).where(
                    GcnEvent.dateobs == dateobs
                )
                gcn_event = session.scalars(stmt).first()
                if not gcn_event:
                    return self.error(f"GCN event not found for dateobs: {dateobs}")

                stmt = SourcesConfirmedInGCN.select(session.user_or_token).where(
                    SourcesConfirmedInGCN.dateobs == dateobs,
                    SourcesConfirmedInGCN.obj_id == source_id,
                )
                source_in_gcn = session.scalars(stmt).first()
                if not source_in_gcn:
                    return self.error(
                        "Source is not confirmed or rejected in this GCN event"
                    )
                source_in_gcn.confirmed = confirmed_or_rejected
                session.commit()
                source_in_gcn_id = source_in_gcn.id
            except Exception as e:
                session.rollback()
                return self.error(str(e))

        return self.success(data={'id': source_in_gcn_id})

    @permissions(['Manage GCNs'])
    def delete(self, dateobs, source_id):
        try:
            arrow.get(dateobs).datetime
        except Exception:
            return self.error(f'Invalid dateobs: {dateobs}')
        if not isinstance(source_id, str):
            return self.error("source_id must be a string")

        source_id = source_id.strip()

        with self.Session() as session:
            try:
                stmt = GcnEvent.select(session.user_or_token).where(
                    GcnEvent.dateobs == dateobs
                )
                gcn_event = session.scalars(stmt).first()
                if not gcn_event:
                    return self.error(f"GCN event not found for dateobs: {dateobs}")
                stmt = SourcesConfirmedInGCN.select(session.user_or_token).where(
                    SourcesConfirmedInGCN.obj_id == source_id,
                    SourcesConfirmedInGCN.dateobs == dateobs,
                )
                source_in_gcn = session.scalars(stmt).first()
                if not source_in_gcn:
                    return self.error(
                        "Source is not confirmed or rejected in this GCN event"
                    )
                session.delete(source_in_gcn)
                session.commit()
            except Exception as e:
                session.rollback()
                return self.error(str(e))
        return self.success(data={'id': source_in_gcn.id})


class GCNsAssociatedToSourceHandler(BaseHandler):
    @auth_or_token
    def get(self, source_id):
        if not isinstance(source_id, str):
            return self.error("source_id must be a string")

        source_id = source_id.strip()

        with self.Session() as session:
            try:
                stmt = SourcesConfirmedInGCN.select(session.user_or_token).where(
                    SourcesConfirmedInGCN.obj_id == source_id,
                    SourcesConfirmedInGCN.confirmed.is_(True),
                )
                source_confirmed_in_gcns = session.scalars(stmt.distinct()).all()
                gcns = [
                    source_confirmed_in_gcn.dateobs
                    for source_confirmed_in_gcn in source_confirmed_in_gcns
                ]
                gcns = list(set(gcns))

            except Exception as e:
                return self.error(str(e))
        return self.success(data={"gcns": gcns})
