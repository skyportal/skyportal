__all__ = ['Annotation', 'AnnotationOnSpectrum', 'AnnotationOnPhotometry']

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import relationship
from sqlalchemy.schema import UniqueConstraint

from baselayer.app.models import (
    Base,
    AccessibleIfRelatedRowsAreAccessible,
    AccessibleIfUserMatches,
)

from .group import accessible_by_groups_members


class AnnotationMixin:
    data = sa.Column(
        JSONB, default=None, nullable=False, doc="Searchable data in JSON format"
    )

    origin = sa.Column(
        sa.String,
        index=True,
        nullable=False,
        doc=(
            'What generated the annotation. This should generally map to a '
            'filter/group name. But since an annotation can be made accessible to multiple '
            'groups, the origin name does not necessarily have to map to a single group name.'
            ' The important thing is to make the origin distinct and descriptive such '
            'that annotations from the same origin generally have the same metrics. One '
            'annotation with multiple fields from each origin is allowed.'
        ),
    )

    @classmethod
    def backref_name(cls):
        if cls.__name__ == 'Annotation':
            return "annotations"
        if cls.__name__ == 'AnnotationOnSpectrum':
            return 'annotations_on_spectra'
        if cls.__name__ == 'AnnotationOnPhotometry':
            return 'annotations_on_photometry'

    @declared_attr
    def author(cls):
        return relationship(
            "User",
            back_populates=cls.backref_name(),
            doc="Annotation's author.",
            uselist=False,
            foreign_keys=f"{cls.__name__}.author_id",
        )

    @declared_attr
    def author_id(cls):
        return sa.Column(
            sa.ForeignKey('users.id', ondelete='CASCADE'),
            nullable=False,
            index=True,
            doc="ID of the Annotation author's User instance.",
        )

    @declared_attr
    def obj_id(cls):
        return sa.Column(
            sa.ForeignKey('objs.id', ondelete='CASCADE'),
            nullable=False,
            index=True,
            doc="ID of the Annotation's Obj.",
        )

    @declared_attr
    def obj(cls):
        return relationship(
            'Obj',
            back_populates=cls.backref_name(),
            doc="The Annotation's Obj.",
        )

    @declared_attr
    def groups(cls):
        return relationship(
            "Group",
            secondary="group_" + cls.backref_name(),
            cascade="save-update, merge, refresh-expire, expunge",
            passive_deletes=True,
            doc="Groups that can see the annotation.",
        )

    def construct_author_info_dict(self):
        return {
            field: getattr(self.author, field)
            for field in (
                'username',
                'first_name',
                'last_name',
                'gravatar_url',
                'is_bot',
            )
        }


class Annotation(Base, AnnotationMixin):
    """A sortable/searchable Annotation on a source, made by a filter or other robot,
    with a set of data as JSON"""

    create = AccessibleIfRelatedRowsAreAccessible(obj='read')
    read = accessible_by_groups_members & AccessibleIfRelatedRowsAreAccessible(
        obj='read'
    )
    update = delete = AccessibleIfUserMatches('author')

    __table_args__ = (UniqueConstraint('obj_id', 'origin'),)


class AnnotationOnSpectrum(Base, AnnotationMixin):
    __tablename__ = 'annotations_on_spectra'

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
        doc="ID of the Annotation's Spectrum.",
    )
    spectrum = relationship(
        'Spectrum',
        back_populates='annotations',
        doc="The Spectrum referred to by this annotation.",
    )

    __table_args__ = (UniqueConstraint('spectrum_id', 'origin'),)


class AnnotationOnPhotometry(Base, AnnotationMixin):
    __tablename__ = 'annotations_on_photometry'

    create = AccessibleIfRelatedRowsAreAccessible(obj='read', photometry='read')

    read = accessible_by_groups_members & AccessibleIfRelatedRowsAreAccessible(
        obj='read',
        photometry='read',
    )

    update = delete = AccessibleIfUserMatches('author')

    photometry_id = sa.Column(
        sa.ForeignKey('photometry.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
        doc="ID of the Annotation's Photometry.",
    )
    photometry = relationship(
        'Photometry',
        back_populates='annotations',
        doc="The Photometry referred to by this annotation.",
    )

    __table_args__ = (UniqueConstraint('photometry_id', 'origin'),)
