__all__ = [
    'Reminder',
    'ReminderOnSpectrum',
    'ReminderOnGCN',
    'ReminderOnEarthquake',
    'ReminderOnShift',
]

import sqlalchemy as sa
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import relationship

from baselayer.app.models import (
    Base,
    AccessibleIfRelatedRowsAreAccessible,
    AccessibleIfUserMatches,
)

from .group import accessible_by_groups_members


"""
NOTE ON ADDING NEW REMINDER TYPES:
To add a new reminder on <something> you need to
- Inherit from ReminderMixin (as well as Base).
- Add the name of the table to backref_name on ReminderMixin
- Add any additional columns, like references to a model the reminder is on.
- Add the reminder as a relationship with back_populates (etc.) on the model you are reminding on.
  (e.g., for ReminderOnSpectrum you need to add "reminders" to models/spectrum.py)
- Add a join to models/group_joins.py so reminders will have groups associated with them.
- Add a join to models/user_token.py so reminders will have a user associated with them.
- Update the API endpoints for reminders, and the reducers to listen for changes in the reminders.
- Update the app_server.py paths to accept the new type of reminder upon API calls.

"""


class ReminderMixin:
    text = sa.Column(sa.String, nullable=False, doc="Reminder body.")

    origin = sa.Column(sa.String, nullable=True, doc='Reminder origin.')

    bot = sa.Column(
        sa.Boolean(),
        nullable=False,
        server_default="false",
        doc="Boolean indicating whether reminder was posted via a bot (token-based request).",
    )

    next_reminder = sa.Column(
        sa.DateTime, nullable=False, index=True, doc="Next reminder."
    )

    reminder_delay = sa.Column(
        sa.Float, nullable=False, doc="Delay until next reminder in days."
    )

    number_of_reminders = sa.Column(
        sa.Integer, nullable=False, index=True, doc="Number of remaining requests."
    )

    @classmethod
    def backref_name(cls):
        if cls.__name__ == 'Reminder':
            return "reminders"
        if cls.__name__ == 'ReminderOnSpectrum':
            return 'reminders_on_spectra'
        if cls.__name__ == 'ReminderOnGCN':
            return 'reminders_on_gcns'
        if cls.__name__ == 'ReminderOnShift':
            return 'reminders_on_shifts'
        if cls.__name__ == 'ReminderOnEarthquake':
            return 'reminders_on_earthquakes'

    @declared_attr
    def user(cls):
        return relationship(
            "User",
            back_populates=cls.backref_name(),
            doc="Reminder's user.",
            passive_deletes=True,
            uselist=False,
            foreign_keys=f"{cls.__name__}.user_id",
        )

    @declared_attr
    def user_id(cls):
        return sa.Column(
            sa.ForeignKey('users.id', ondelete='CASCADE'),
            nullable=False,
            index=True,
            doc="ID of the Reminder User instance.",
        )

    @declared_attr
    def groups(cls):
        return relationship(
            "Group",
            secondary="group_" + cls.backref_name(),
            cascade="save-update, merge, refresh-expire, expunge",
            passive_deletes=True,
            doc="Groups that can see the reminder.",
        )


class Reminder(Base, ReminderMixin):
    """A reminder made by a User or a Robot (via the API) on a Source."""

    create = AccessibleIfRelatedRowsAreAccessible(obj='read')

    read = accessible_by_groups_members & AccessibleIfRelatedRowsAreAccessible(
        obj='read'
    )

    update = delete = AccessibleIfUserMatches('user')

    obj_id = sa.Column(
        sa.ForeignKey('objs.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
        doc="ID of the Reminder's Obj.",
    )

    obj = relationship(
        'Obj',
        back_populates='reminders',
        doc="The Reminder's Obj.",
    )


class ReminderOnSpectrum(Base, ReminderMixin):
    __tablename__ = 'reminders_on_spectra'

    create = AccessibleIfRelatedRowsAreAccessible(obj='read', spectrum='read')

    read = accessible_by_groups_members & AccessibleIfRelatedRowsAreAccessible(
        obj='read',
        spectrum='read',
    )

    update = delete = AccessibleIfUserMatches('user')

    obj_id = sa.Column(
        sa.ForeignKey('objs.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
        doc="ID of the Reminder's Obj.",
    )

    obj = relationship(
        'Obj',
        back_populates='reminders_on_spectra',
        doc="The Reminder's Obj.",
    )

    spectrum_id = sa.Column(
        sa.ForeignKey('spectra.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
        doc="ID of the Reminder's Spectrum.",
    )
    spectrum = relationship(
        'Spectrum',
        back_populates='reminders',
        doc="The Spectrum referred to by this reminder.",
    )


class ReminderOnGCN(Base, ReminderMixin):
    __tablename__ = 'reminders_on_gcns'

    create = AccessibleIfRelatedRowsAreAccessible(gcn='read')

    read = accessible_by_groups_members & AccessibleIfRelatedRowsAreAccessible(
        gcn='read',
    )

    update = delete = AccessibleIfUserMatches('user')

    gcn_id = sa.Column(
        sa.ForeignKey('gcnevents.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
        doc="ID of the Reminder's GCN.",
    )
    gcn = relationship(
        'GcnEvent',
        back_populates='reminders',
        doc="The GcnEvent referred to by this reminder.",
    )


class ReminderOnEarthquake(Base, ReminderMixin):
    __tablename__ = 'reminders_on_earthquakes'

    create = AccessibleIfRelatedRowsAreAccessible(earthquake='read')

    read = accessible_by_groups_members & AccessibleIfRelatedRowsAreAccessible(
        earthquake='read',
    )

    update = delete = AccessibleIfUserMatches('user')

    earthquake_id = sa.Column(
        sa.ForeignKey('earthquakeevents.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
        doc="ID of the Reminder's Earthquake.",
    )
    earthquake = relationship(
        'EarthquakeEvent',
        back_populates='reminders',
        doc="The Earthquake referred to by this reminder.",
    )


class ReminderOnShift(Base, ReminderMixin):
    __tablename__ = 'reminders_on_shifts'

    create = AccessibleIfRelatedRowsAreAccessible(shift='read')

    read = accessible_by_groups_members & AccessibleIfRelatedRowsAreAccessible(
        shift='read',
    )

    update = delete = AccessibleIfUserMatches('user')

    shift_id = sa.Column(
        sa.ForeignKey('shifts.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
        doc="ID of the Reminder's Shift.",
    )
    shift = relationship(
        'Shift',
        back_populates='reminders',
        doc="The Shift referred to by this reminder.",
    )
