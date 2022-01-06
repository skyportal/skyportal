__all__ = ['Logbook', 'LogbookOnSpectrum']

import sqlalchemy as sa
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import relationship

from baselayer.app.models import (
    Base,
    AccessibleIfRelatedRowsAreAccessible,
    AccessibleIfUserMatches,
)

from .group import accessible_by_groups_members


class LogbookMixin:
    text = sa.Column(sa.String, nullable=False, doc="Logbook body.")

    attachment_name = sa.Column(
        sa.String, nullable=True, doc="Filename of the attachment."
    )

    attachment_bytes = sa.Column(
        sa.types.LargeBinary,
        nullable=True,
        doc="Binary representation of the attachment.",
    )

    origin = sa.Column(sa.String, nullable=True, doc='Logbook origin.')

    bot = sa.Column(
        sa.Boolean(),
        nullable=False,
        server_default="false",
        doc="Boolean indicating whether logbook was posted via a bot (token-based request).",
    )

    @classmethod
    def backref_name(cls):
        if cls.__name__ == 'Logbook':
            return "logbooks"
        if cls.__name__ == 'logbookOnSpectrum':
            return 'logbooks_on_spectra'

    @declared_attr
    def author(cls):
        return relationship(
            "User",
            back_populates=cls.backref_name(),
            doc="Logbook's author.",
            uselist=False,
            foreign_keys=f"{cls.__name__}.author_id",
        )

    @declared_attr
    def author_id(cls):
        return sa.Column(
            sa.ForeignKey('users.id', ondelete='CASCADE'),
            nullable=False,
            index=True,
            doc="ID of the Logbook author's User instance.",
        )

    @declared_attr
    def obj_id(cls):
        return sa.Column(
            sa.ForeignKey('objs.id', ondelete='CASCADE'),
            nullable=False,
            index=True,
            doc="ID of the Logbook's Obj.",
        )

    @declared_attr
    def obj(cls):
        return relationship(
            'Obj',
            back_populates=cls.backref_name(),
            doc="The Logbook's Obj.",
        )

    @declared_attr
    def groups(cls):
        return relationship(
            "Group",
            secondary="group_" + cls.backref_name(),
            cascade="save-update, merge, refresh-expire, expunge",
            passive_deletes=True,
            doc="Groups that can see the logbook.",
        )

    def construct_author_info_dict(self):
        return {
            field: getattr(self.author, field)
            for field in ('username', 'first_name', 'last_name', 'gravatar_url')
        }


class Logbook(Base, LogbookMixin):
    """A logbook made by a User or a Robot (via the API) on a Source."""

    create = AccessibleIfRelatedRowsAreAccessible(obj='read')

    read = accessible_by_groups_members & AccessibleIfRelatedRowsAreAccessible(
        obj='read'
    )

    update = delete = AccessibleIfUserMatches('author')


class LogbookOnSpectrum(Base, LogbookMixin):

    __tablename__ = 'logbooks_on_spectra'

    create = AccessibleIfRelatedRowsAreAccessible(obj='read', spectrum='read')

    read = accessible_by_groups_members & AccessibleIfRelatedRowsAreAccessible(
        obj='read',
        spectrum='read',
    )

    update = delete = AccessibleIfUserMatches('author')

    spectrum_id = sa.Column(
        sa.ForeignKey('spectra.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
        doc="ID of the Logbook's Spectrum.",
    )
    spectrum = relationship(
        'Spectrum',
        back_populates='logbooks',
        doc="The Spectrum referred to by this logbook.",
    )
