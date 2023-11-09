__all__ = ['ObservingRun']

import sqlalchemy as sa
from sqlalchemy.orm import relationship

from astropy import time as ap_time
from astropy import units as u
from dateutil.tz import tzutc

import numpy as np

from baselayer.app.models import Base, accessible_by_owner

TZINFO = tzutc()


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
        overlaps='assignments, obj, run',
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
        overlaps='sources',
    )
    calendar_date = sa.Column(
        sa.Date, nullable=False, index=True, doc="The Local Calendar date of this Run."
    )

    run_end_utc = sa.Column(
        sa.DateTime,
        nullable=True,
        doc="The UTC end time of this Run.",
    )

    @property
    def calendar_noon(self):
        """The Local Calendar noon of this Run."""
        year = self.calendar_date.year
        month = self.calendar_date.month
        day = self.calendar_date.day
        hour = 12
        noon_str = f'{year}-{month}-{day}T{hour}:00:00.000'
        return ap_time.Time(noon_str, format='isot', scale='utc')

    def calculate_run_end_utc(self):
        observer = self.instrument.telescope.observer
        if observer is None:
            return None
        try:
            end = self.instrument.telescope.next_sunrise(self.calendar_noon).isot
        except Exception:
            end = None
        self.run_end_utc = end

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

        masked = next_rise.mask
        if masked.any():
            target_subarr = [t for t, b in zip(target_array, masked) if b]
            altitudes = observer.altaz(sunset, target_subarr).alt
            always_up = np.where(altitudes > altitude)[0]
            idx = np.where(masked)[0][always_up]
            next_rise[idx] = sunset

        return next_rise.reshape(original_shape)

    def set_time(self, target_or_targets, altitude=30 * u.degree):
        """The set time of the specified targets as an astropy.time.Time."""
        observer = self.instrument.telescope.observer
        sunset = self.instrument.telescope.next_sunset(self.calendar_noon).reshape((1,))
        sunrise = self.instrument.telescope.next_sunrise(self.calendar_noon).reshape(
            (1,)
        )
        original_shape = np.asarray(target_or_targets).shape
        target_array = (
            [target_or_targets] if len(original_shape) == 0 else target_or_targets
        )
        next_set = observer.target_set_time(
            sunset, target_array, which='next', horizon=altitude
        ).reshape((len(target_array),))

        masked = next_set.mask
        if masked.any():
            target_subarr = [t for t, b in zip(target_array, masked) if b]
            altitudes = observer.altaz(sunset, target_subarr).alt
            always_up = np.where(altitudes > altitude)[0]
            idx = np.where(masked)[0][always_up]
            next_set[idx] = sunrise

        return next_set.reshape(original_shape)
