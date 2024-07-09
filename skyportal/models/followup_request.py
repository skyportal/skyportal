__all__ = [
    'DefaultFollowupRequest',
    'FollowupRequest',
    'FollowupRequestTargetGroup',
    'FollowupRequestUser',
]

from astropy import coordinates as ap_coord
from astropy import time as ap_time
from astropy import units as u
import operator  # noqa: F401

import sqlalchemy as sa
from sqlalchemy import event, inspect, func
from sqlalchemy.orm import relationship
from sqlalchemy.dialects import postgresql as psql
from sqlalchemy.sql.expression import cast

from baselayer.app.models import (
    Base,
    DBSession,
    join_model,
    User,
    public,
    AccessibleIfRelatedRowsAreAccessible,
    AccessibleIfUserMatches,
    CustomUserAccessControl,
)

from .group import Group
from .instrument import Instrument
from .allocation import Allocation
from .classification import Classification
from .source import Source

from baselayer.app.env import load_env
from baselayer.log import make_log

_, cfg = load_env()

log = make_log('model/followup_request')

EQ_OP = getattr(operator, 'eq')


def updatable_by_token_with_listener_acl(cls, user_or_token):
    if user_or_token.is_admin:
        return public.query_accessible_rows(cls, user_or_token)

    instruments_with_apis = (
        Instrument.query_records_accessible_by(user_or_token)
        .filter(Instrument.listener_classname.isnot(None))
        .all()
    )

    api_map = {
        instrument.id: instrument.listener_class.get_acl_id()
        for instrument in instruments_with_apis
    }

    accessible_instrument_ids = [
        instrument_id
        for instrument_id, acl_id in api_map.items()
        if acl_id in user_or_token.permissions
    ]

    return (
        DBSession()
        .query(cls)
        .join(Allocation)
        .join(Instrument)
        .filter(Instrument.id.in_(accessible_instrument_ids))
    )


class DefaultFollowupRequest(Base):
    """A default request for a FollowupRequest."""

    # TODO: Make read-accessible via target groups
    create = read = AccessibleIfRelatedRowsAreAccessible(allocation="read")
    update = delete = (
        (
            AccessibleIfUserMatches('allocation.group.users')
            | AccessibleIfUserMatches('requester')
        )
        & read
    ) | CustomUserAccessControl(updatable_by_token_with_listener_acl)

    requester_id = sa.Column(
        sa.ForeignKey('users.id', ondelete='SET NULL'),
        nullable=True,
        index=True,
        doc="ID of the User who requested the default follow-up.",
    )

    requester = relationship(
        User,
        back_populates='default_followup_requests',
        doc="The User who requested the default follow-up.",
        foreign_keys=[requester_id],
    )

    payload = sa.Column(
        psql.JSONB,
        nullable=False,
        doc="Content of the default follow-up request.",
    )

    allocation_id = sa.Column(
        sa.ForeignKey('allocations.id', ondelete='CASCADE'), nullable=False, index=True
    )
    allocation = relationship('Allocation', back_populates='default_requests')

    target_groups = relationship(
        'Group',
        secondary='default_followup_groups',
        passive_deletes=True,
        doc='Groups to share the resulting data from this default followup request with.',
        overlaps='groups',
    )

    default_followup_name = sa.Column(
        sa.String, unique=True, nullable=False, doc='Default followup name'
    )

    source_filter = sa.Column(
        psql.JSONB,
        nullable=False,
        doc="Source filter for default follow-up request.",
    )


DefaultFollowupRequestTargetGroup = join_model(
    'default_followup_groups',
    DefaultFollowupRequest,
    Group,
    new_name='DefaultFollowupRequestTargetGroup',
    overlaps='target_groups',
)
DefaultFollowupRequestTargetGroup.create = (
    DefaultFollowupRequestTargetGroup.update
) = DefaultFollowupRequestTargetGroup.delete = (
    AccessibleIfUserMatches('defaultfollowuprequest.requester')
    & DefaultFollowupRequestTargetGroup.read
)


class FollowupRequest(Base):
    """A request for follow-up data (spectroscopy, photometry, or both) using a
    robotic instrument."""

    # TODO: Make read-accessible via target groups
    create = read = AccessibleIfRelatedRowsAreAccessible(obj="read", allocation="read")
    update = delete = (
        (
            AccessibleIfUserMatches('allocation.group.users')
            | AccessibleIfUserMatches('requester')
        )
        & read
    ) | CustomUserAccessControl(updatable_by_token_with_listener_acl)

    requester_id = sa.Column(
        sa.ForeignKey('users.id', ondelete='SET NULL'),
        nullable=True,
        index=True,
        doc="ID of the User who requested the follow-up.",
    )

    requester = relationship(
        User,
        back_populates='followup_requests',
        doc="The User who requested the follow-up.",
        foreign_keys=[requester_id],
    )

    last_modified_by_id = sa.Column(
        sa.ForeignKey('users.id', ondelete='SET NULL'),
        nullable=True,
        doc="The ID of the User who last modified the request.",
    )

    last_modified_by = relationship(
        User,
        doc="The user who last modified the request.",
        foreign_keys=[last_modified_by_id],
    )

    obj = relationship('Obj', back_populates='followup_requests', doc="The target Obj.")
    obj_id = sa.Column(
        sa.ForeignKey('objs.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
        doc="ID of the target Obj.",
    )

    payload = sa.Column(
        psql.JSONB, nullable=False, doc="Content of the followup request."
    )

    status = sa.Column(
        sa.String(),
        nullable=False,
        default="pending submission",
        index=True,
        doc="The status of the request.",
    )

    allocation_id = sa.Column(
        sa.ForeignKey('allocations.id', ondelete='CASCADE'), nullable=False, index=True
    )

    comment = sa.Column(
        sa.String(),
        nullable=True,
        doc="Comment on the follow-up request.",
    )

    allocation = relationship('Allocation', back_populates='requests')

    transactions = relationship(
        'FacilityTransaction',
        back_populates='followup_request',
        passive_deletes=True,
        order_by="FacilityTransaction.created_at.desc()",
    )

    transaction_requests = relationship(
        'FacilityTransactionRequest',
        back_populates='followup_request',
        passive_deletes=True,
        order_by="FacilityTransactionRequest.created_at.desc()",
    )

    target_groups = relationship(
        'Group',
        secondary='request_groups',
        passive_deletes=True,
        doc='Groups to share the resulting data from this request with.',
        overlaps='groups',
    )

    photometry = relationship('Photometry', back_populates='followup_request')
    photometric_series = relationship(
        'PhotometricSeries', back_populates='followup_request'
    )
    spectra = relationship('Spectrum', back_populates='followup_request')

    watchers = relationship(
        'FollowupRequestUser',
        back_populates='followuprequest',
        cascade='save-update, merge, refresh-expire, expunge',
        passive_deletes=True,
        doc='Elements of a join table mapping Users to FollowupRequestss.',
        overlaps='followup_requests, users',
    )

    @property
    def instrument(self):
        return self.allocation.instrument

    def rise_time(self, altitude=30 * u.degree):
        """The rise time of the target as an astropy.time.Time."""
        observer = self.allocation.instrument.telescope.observer
        if observer is None:
            return None

        sunset = self.allocation.instrument.telescope.next_sunset(
            ap_time.Time.now()
        ).reshape((1,))
        sunrise = self.allocation.instrument.telescope.next_sunrise(
            ap_time.Time.now()
        ).reshape((1,))

        coord = ap_coord.SkyCoord(self.obj.ra, self.obj.dec, unit='deg')

        next_rise = observer.target_rise_time(
            sunset, coord, which='next', horizon=altitude
        )

        # if next rise time is after next sunrise, the target rises before
        # sunset. show the previous rise so that the target is shown to be
        # "already up" when the run begins (a beginning of night target).

        recalc = next_rise > sunrise
        if recalc.any():
            next_rise = observer.target_rise_time(
                sunset, coord, which='previous', horizon=altitude
            )

        return next_rise

    def set_time(self, altitude=30 * u.degree):
        """The set time of the target as an astropy.time.Time."""
        observer = self.allocation.instrument.telescope.observer
        if observer is None:
            return None

        sunset = self.allocation.instrument.telescope.next_sunset(ap_time.Time.now())
        coord = ap_coord.SkyCoord(self.obj.ra, self.obj.dec, unit='deg')
        return observer.target_set_time(sunset, coord, which='next', horizon=altitude)


FollowupRequestTargetGroup = join_model(
    'request_groups', FollowupRequest, Group, overlaps='target_groups'
)
FollowupRequestTargetGroup.create = (
    FollowupRequestTargetGroup.update
) = FollowupRequestTargetGroup.delete = (
    AccessibleIfUserMatches('followuprequest.requester')
    & FollowupRequestTargetGroup.read
)


FollowupRequestUser = join_model('followup_request_users', FollowupRequest, User)
FollowupRequestUser.__doc__ = "Join table mapping `FollowupRequest`s to `User`s."
FollowupRequestUser.create = FollowupRequestUser.read
FollowupRequestUser.update = FollowupRequestUser.delete = AccessibleIfUserMatches(
    'user'
)


@event.listens_for(Source, 'after_insert')
@event.listens_for(Classification, 'after_insert')
def add_followup(mapper, connection, target):
    # Add front-end user notifications
    @event.listens_for(inspect(target).session, "after_flush", once=True)
    def receive_after_flush(session, context):
        if target is None:
            return

        user_id = None
        target_class_name = target.__class__.__name__
        target_data = target.to_dict()

        requests_query = sa.select(DefaultFollowupRequest)

        default_followup_requests = session.scalars(requests_query).all()

        # GroupObj is the classname for the Source table,
        # since it's a join table between Obj and Group
        if target_class_name == 'GroupObj':
            # match by obj id/name
            # match by group id of the source
            requests_query = requests_query.where(
                DefaultFollowupRequest.source_filter['name'].astext.isnot(None),
                func.regexp_match(
                    target_data['obj_id'],
                    DefaultFollowupRequest.source_filter['name'].astext,
                ).isnot(None),
                EQ_OP(
                    DefaultFollowupRequest.source_filter['group_id'],
                    cast(target_data['group_id'], psql.JSONB),
                ),
            )
            user_id = target_data.get('saved_by_id', None)
        if target_class_name == 'Classification':
            # match by classification
            requests_query = requests_query.where(
                EQ_OP(
                    DefaultFollowupRequest.source_filter['classification'],
                    cast(target_data['classification'], psql.JSONB),
                )
            )
            user_id = target_data.get('author_id', None)
        elif target_class_name not in ['Source', 'GroupObj']:
            print(f"Unknown target class name: {target_class_name}")
            return

        default_followup_requests = session.scalars(requests_query).all()

        if len(default_followup_requests) == 0:
            return

        from skyportal.utils.asynchronous import run_async
        from skyportal.handlers.api.followup_request import (
            post_default_followup_requests,
        )

        run_async(
            post_default_followup_requests,
            target_data['obj_id'],
            default_followup_requests,
            user_id,
        )
