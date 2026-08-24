__all__ = ["GcnAssociationRule"]

import sqlalchemy as sa
from sqlalchemy.orm import relationship

from baselayer.app.models import AccessibleIfUserMatches, Base

from ..enum_types import mma_detector_types


class GcnAssociationRule(Base):
    """How close two events must be, for one pair of messengers, to be related.

    A neutrino arrives within seconds of a gravitational wave, a GRB within
    minutes, an X-ray counterpart over days, and groups disagree about where to
    draw each line. The overlap integral is objective and computed once; these
    are the cuts a user applies to it, so they are owned by a user rather than
    set site-wide.

    The messenger pair is stored in sorted order, so a rule is one row however
    it was entered.
    """

    read = create = update = delete = AccessibleIfUserMatches("user")

    user_id = sa.Column(
        sa.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="ID of the User whose rule this is.",
    )

    user = relationship(
        "User",
        foreign_keys="GcnAssociationRule.user_id",
        doc="The User whose rule this is.",
    )

    detector_type_1 = sa.Column(
        mma_detector_types,
        nullable=False,
        doc="First messenger of the pair, sorted.",
    )

    detector_type_2 = sa.Column(
        mma_detector_types,
        nullable=False,
        doc="Second messenger of the pair, sorted.",
    )

    tags_1 = sa.Column(
        sa.ARRAY(sa.String),
        nullable=False,
        server_default="{}",
        doc="Tags the detector_type_1 event must carry at least one of, e.g. "
        "BNS or NSBH so only those GW events pair with GRBs. Empty means no "
        "restriction. Same 'any of' rule as a crossmatch filter's gcn_tags.",
    )

    tags_2 = sa.Column(
        sa.ARRAY(sa.String),
        nullable=False,
        server_default="{}",
        doc="Tags the detector_type_2 event must carry at least one of. Empty "
        "means no restriction.",
    )

    days = sa.Column(
        sa.Float,
        nullable=False,
        doc="Widest separation in days for this pair to count as coincident.",
    )

    min_consistency = sa.Column(
        sa.Float,
        nullable=False,
        server_default="0.5",
        doc="Smallest sky-map consistency for this pair: how well the two "
        "localizations must agree, as a fraction of the most they could. The "
        "cut is on consistency rather than the raw overlap because the "
        "overlap's ceiling depends on the localization areas, so one threshold "
        "would mean different things for a cone and a wide skymap.",
    )

    __table_args__ = (
        sa.UniqueConstraint(
            "user_id",
            "detector_type_1",
            "detector_type_2",
            name="gcnassociationrules_user_pair_key",
        ),
    )
