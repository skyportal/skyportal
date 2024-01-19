import arrow
from ligo.gracedb.rest import GraceDb
import sqlalchemy as sa
from sqlalchemy.orm import sessionmaker, scoped_session
import tempfile
from tornado.ioloop import IOLoop

from baselayer.app.access import permissions
from baselayer.app.flow import Flow
from baselayer.app.env import load_env
from baselayer.log import make_log

from ..base import BaseHandler
from ...models import DBSession, CommentOnGCN, GcnEvent, Group, User

Session = scoped_session(sessionmaker())

log = make_log('api/gcn_gracedb')

_, cfg = load_env()
GRACEDB_URL = cfg['app.gracedb_endpoint']
GRACEDB_CREDENTIAL = cfg.get('app.gracedb_credential')

if GRACEDB_CREDENTIAL is not None:
    client = GraceDb(service_url=GRACEDB_URL, cred=GRACEDB_CREDENTIAL)
else:
    client = GraceDb(service_url=GRACEDB_URL)


def post_gracedb_data(dateobs, gracedb_id, user_id):
    if Session.registry.has():
        session = Session()
    else:
        session = Session(bind=DBSession.session_factory.kw["bind"])

    try:
        flow = Flow()
        user = session.scalars(sa.select(User).where(User.id == user_id)).first()
        stmt = GcnEvent.select(user, mode="update").where(GcnEvent.dateobs == dateobs)
        gcn_event = session.scalars(stmt).first()
        if gcn_event is None:
            return

        # fetch superevent
        superevent_dict = client.superevent(gracedb_id).json()
        superevent_dict_log = client.logs(gracedb_id).json()
        superevent_dict_labels = client.labels(gracedb_id).json()

        gcn_event.gracedb_log = superevent_dict_log
        gcn_event.gracedb_labels = superevent_dict_labels

        gracedb_link = superevent_dict['links']['self']

        group_ids = [g.id for g in user.accessible_groups]
        groups = (
            session.scalars(Group.select(user).where(Group.id.in_(group_ids)))
            .unique()
            .all()
        )

        comment = CommentOnGCN(
            text=f'GraceDB link: {gracedb_link}',
            gcn_id=gcn_event.id,
            author=user,
            groups=groups,
            bot=True,
        )
        session.add(comment)

        # get list of superevent files
        event_files = client.files(gracedb_id).json()

        for filename in event_files:
            if not filename.endswith("png"):
                continue

            # get the file content
            file = client.files(gracedb_id, filename)
            output_format = filename.split(".")[-1]
            with tempfile.NamedTemporaryFile(
                mode='wb', delete=False, suffix='.' + output_format
            ) as f:
                f.write(file.read())
                f.flush()

                with open(f.name, mode='rb') as g:
                    data_to_disk = g.read()

                comment = CommentOnGCN(
                    text=f'GraceDB file: {filename}',
                    gcn_id=gcn_event.id,
                    attachment_name=filename,
                    author=user,
                    groups=groups,
                    bot=True,
                )
                session.add(comment)
                if data_to_disk is not None:
                    comment.save_data(filename, data_to_disk)
        session.commit()

        flow.push(
            user_id='*',
            action_type='skyportal/REFRESH_GCN_EVENT',
            payload={'gcnEvent_dateobs': dateobs},
        )
        log(f'Posted GraceDB data for {dateobs}')
    except Exception as e:
        log(f'Failed to post GraceDB data for {dateobs}: {str(e)}')
    finally:
        session.close()
        Session.remove()


class GcnGraceDBHandler(BaseHandler):
    @permissions(["Manage GCNs"])
    def post(self, dateobs):
        """
        ---
        description: Scrape data of a GCN Event from GraceDB
        tags:
          - gcn_event
        parameters:
          - in: path
            name: dateobs
            required: true
            schema:
              type: string
            description: The dateobs of the event, as an arrow parseable string
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
                            id:
                              type: int
                              description: The id of the GcnEvent
          400:
            content:
              application/json:
                schema: Error
        """
        try:
            arrow.get(dateobs).datetime
        except Exception:
            return self.error(f'Invalid dateobs: {dateobs}')
        try:
            with self.Session() as session:
                stmt = GcnEvent.select(session.user_or_token).where(
                    GcnEvent.dateobs == dateobs
                )
                gcn_event = session.scalars(stmt).first()
                if gcn_event is None:
                    return self.error(f'No GCN event found for {dateobs}')

                gracedb_id = None
                aliases = gcn_event.aliases
                for alias in aliases:
                    if "LVC" in alias:
                        gracedb_id = alias.split("#")[-1]
                        break

                if gracedb_id is None:
                    return self.error(
                        f'Event {dateobs} does not have GraceDB ID, cannot retrieve data.'
                    )
                gcn_event_id = gcn_event.id

                IOLoop.current().run_in_executor(
                    None,
                    lambda: post_gracedb_data(
                        dateobs, gracedb_id, self.associated_user_object.id
                    ),
                )

                return self.success(data={'id': gcn_event_id})

        except Exception as e:
            return self.error(f'Error scraping GraceDB: {e}')
