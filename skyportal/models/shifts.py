__all__ = ['Shifts']

from datetime import datetime, timezone

import sqlalchemy as sa
from sqlalchemy.orm import relationship

from astropy import time as ap_time
from astropy import units as u

import numpy as np

from baselayer.app.models import Base, accessible_by_owner, public


class Shifts(Base):
    """A classical observing run with a target list (of Objs)."""

    update = delete = public

    user_id = sa.Column(
        sa.ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
        doc="ID of the User for this shift.",
    )
    user = relationship(
        'User',
        cascade='save-update, merge, refresh-expire, expunge',
        uselist=False,
        back_populates='shifts',
        doc="The User for this shift.",
    )

    calendar_date = sa.Column(
        sa.Date, nullable=False, index=True, doc="The Local Calendar date of this User."
    )

    @property
    def calendar_noon(self):
        observer = self.user
        year = self.calendar_date.year
        month = self.calendar_date.month
        day = self.calendar_date.day
        hour = 12
        #Need to associate a user to its timezone
        noon = datetime(
            year=year, month=month, day=day, hour=hour, tzinfo=observer.timezone
        )
        noon = noon.astimezone(timezone.utc).timestamp()
        noon = ap_time.Time(noon, format='unix')
        return noon