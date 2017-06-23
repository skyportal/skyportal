import os
import pandas as pd

import sqlalchemy as sa
from sqlalchemy.orm import relationship

from baselayer.app.models import init_db, Base, DBSession, User


class Comment(Base):
    user_id = sa.Column(sa.ForeignKey('users.id', ondelete='CASCADE'),
                        nullable=False, index=True)
    user = relationship('User', backref='comments')
    text = sa.Column(sa.String(), nullable=False)
    source_id = sa.Column(sa.ForeignKey('sources.id', ondelete='CASCADE'),
                          nullable=False, index=True)
    source = relationship('Source', backref='comments')


class Photometry(Base):
    __tablename__ = 'photometry'
    source_id = sa.Column(sa.ForeignKey('sources.id', ondelete='CASCADE'),
                          nullable=False, index=True)
    source = relationship('Source', backref='photometry')
    obs_time = sa.Column(sa.DateTime())
    mag = sa.Column(sa.Float())
    e_mag = sa.Column(sa.Float())
    lim_mag = sa.Column(sa.Float())
    filter = sa.Column(sa.String())


class Source(Base):
    ra = sa.Column(sa.Float())
    dec = sa.Column(sa.Float())
    red_shift = sa.Column(sa.Float(), nullable=True)
    name = sa.Column(sa.String())
