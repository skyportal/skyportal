__all__ = ['FollowupRequest', 'FollowupRequestTargetGroup']

from astropy import coordinates as ap_coord
from astropy import time as ap_time
from astropy import units as u

import sqlalchemy as sa
from sqlalchemy.orm import relationship

from sqlalchemy.dialects import postgresql as psql

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
