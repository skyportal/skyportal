__all__ = ['ObservingRun']

from datetime import datetime, timezone

import sqlalchemy as sa
from sqlalchemy.orm import relationship

from astropy import time as ap_time
from astropy import units as u

import numpy as np

from baselayer.app.models import Base, accessible_by_owner


class ObservingRun(Base):
    """A classical observing run with a target list (of Objs)."""

    update = delete = accessible_by_owner

    instrument_id = sa.Column(
        sa.ForeignKey('instruments.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
        doc="ID of the Instrument used for this run.",
    )
    instrument = relationship(
        'Instrument',
        cascade='save-update, merge, refresh-expire, expunge',
        uselist=False,
        back_populates='observing_runs',
        doc="The Instrument for this run.",
    )

    # name of the PI
    pi = sa.Column(sa.String, doc="The name(s) of the PI(s) of this run.")
    observers = sa.Column(sa.String, doc="The name(s) of the observer(s) on this run.")

    sources = relationship(
        'Obj',
        secondary='join(ClassicalAssignment, Obj)',
        cascade='save-update, merge, refresh-expire, expunge',
        passive_deletes=True,
        doc="The targets [Objs] for this run.",
    )

    # let this be nullable to accommodate external groups' runs
    group = relationship(
        'Group',
        back_populates='observing_runs',
        doc='The Group associated with this Run.',
    )
    group_id = sa.Column(
        sa.ForeignKey('groups.id', ondelete='CASCADE'),
        nullable=True,
        index=True,
        doc='The ID of the Group associated with this run.',
    )

    # the person who uploaded the run
    owner = relationship(
        'User',
        back_populates='observing_runs',
        doc="The User who created this ObservingRun.",
        foreign_keys="ObservingRun.owner_id",
    )
    owner_id = sa.Column(
        sa.ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
        doc="The ID of the User who created this ObservingRun.",
    )

    assignments = relationship(
        'ClassicalAssignment',
        passive_deletes=True,
        doc="The Target Assignments for this Run.",
    )
    calendar_date = sa.Column(
        sa.Date, nullable=False, index=True, doc="The Local Calendar date of this Run."
    )

    @property
    def calendar_noon(self):
        observer = self.instrument.telescope.observer
        year = self.calendar_date.year
        month = self.calendar_date.month
        day = self.calendar_date.day
        hour = 12
        noon = datetime(
            year=year, month=month, day=day, hour=hour, tzinfo=observer.timezone
        )
        noon = noon.astimezone(timezone.utc).timestamp()
        noon = ap_time.Time(noon, format='unix')
        return noon

    def rise_time(self, target_or_targets, altitude=30 * u.degree):
        """The rise time of the specified targets as an astropy.time.Time."""
        observer = self.instrument.telescope.observer
        sunset = self.instrument.telescope.next_sunset(self.calendar_noon).reshape((1,))
        sunrise = self.instrument.telescope.next_sunrise(self.calendar_noon).reshape(
            (1,)
        )
        original_shape = np.asarray(target_or_targets).shape
        target_array = (
            [target_or_targets] if len(original_shape) == 0 else target_or_targets
        )

        next_rise = observer.target_rise_time(
            sunset, target_array, which='next', horizon=altitude
        ).reshape((len(target_array),))

        # if next rise time is after next sunrise, the target rises before
        # sunset. show the previous rise so that the target is shown to be
        # "already up" when the run begins (a beginning of night target).

        recalc = next_rise > sunrise
        if recalc.any():
            target_subarr = [t for t, b in zip(target_array, recalc) if b]
            next_rise[recalc] = observer.target_rise_time(
                sunset, target_subarr, which='previous', horizon=altitude
            ).reshape((len(target_subarr),))

        return next_rise.reshape(original_shape)

    def set_time(self, target_or_targets, altitude=30 * u.degree):
        """The set time of the specified targets as an astropy.time.Time."""
        observer = self.instrument.telescope.observer
        sunset = self.instrument.telescope.next_sunset(self.calendar_noon)
        original_shape = np.asarray(target_or_targets).shape
        return observer.target_set_time(
            sunset, target_or_targets, which='next', horizon=altitude
        ).reshape(original_shape)
