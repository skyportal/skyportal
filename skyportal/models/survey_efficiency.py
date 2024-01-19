__all__ = [
    'DefaultSurveyEfficiencyRequest',
    'SurveyEfficiencyForObservations',
    'SurveyEfficiencyForObservationPlan',
]

import json
import sqlalchemy as sa
from sqlalchemy.orm import relationship
from sqlalchemy.dialects import postgresql as psql
from sqlalchemy.ext.declarative import declared_attr
import numpy as np

from baselayer.app.models import (
    Base,
    AccessibleIfRelatedRowsAreAccessible,
)

from .group import accessible_by_groups_members


class DefaultSurveyEfficiencyRequest(Base):
    """A default request for a Survey Efficiency analysis."""

    # TODO: Make read-accessible via target groups
    create = read = AccessibleIfRelatedRowsAreAccessible(
        default_observationplan_request="read"
    )
    update = AccessibleIfRelatedRowsAreAccessible(
        default_observationplan_request="update"
    )
    delete = AccessibleIfRelatedRowsAreAccessible(
        default_observationplan_request="delete"
    )

    default_observationplan_request_id = sa.Column(
        sa.ForeignKey('defaultobservationplanrequests.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    default_observationplan_request = relationship(
        'DefaultObservationPlanRequest', back_populates='default_survey_efficiencies'
    )

    payload = sa.Column(
        psql.JSONB,
        nullable=False,
        doc="Content of the survey efficiency assessment request.",
    )


class SurveyEfficiencyAnalysisMixin:
    payload = sa.Column(
        psql.JSONB,
        nullable=False,
        doc="Content of the survey efficiency assessment request.",
    )

    status = sa.Column(
        sa.String(),
        nullable=False,
        default="pending submission",
        index=True,
        doc="The status of the request.",
    )

    lightcurves = sa.Column(psql.JSONB, doc='Simulated light curve dictionary')

    @property
    def number_of_transients(self):
        """Number of simulated transients."""
        if self.lightcurves:
            lcs = json.loads(self.lightcurves)
            all_transients = []
            if lcs['meta_notobserved'] is not None:
                all_transients.append(len(lcs['meta_notobserved']['z']))
            if lcs['meta'] is not None:
                all_transients.append(len(lcs['meta']['z']))
            if lcs['meta_rejected'] is not None:
                all_transients.append(len(lcs['meta_rejected']['z']))
            ntransient = np.sum(all_transients)
            return int(ntransient)
        else:
            return None

    @property
    def number_in_covered(self):
        """Number of simulated transients in covered area."""
        if self.lightcurves:
            lcs = json.loads(self.lightcurves)

            n_in_covered = 0
            if lcs['meta'] is not None:
                n_in_covered = n_in_covered + len(lcs['meta']['z'])
            if lcs['meta_rejected'] is not None:
                n_in_covered = n_in_covered + len(lcs['meta_rejected']['z'])

            return int(n_in_covered)

        else:
            return None

    @property
    def number_detected(self):
        """Number of detected transients."""
        if self.lightcurves:
            lcs = json.loads(self.lightcurves)

            if lcs['lcs'] is not None:
                n_detected = len(lcs['lcs'])
            else:
                n_detected = 0

            return int(n_detected)

        else:
            return None

    @property
    def efficiency(self):
        """Efficiency of transient detection."""
        if self.number_of_transients and self.number_detected:
            return self.number_detected / self.number_of_transients
        else:
            return None

    @declared_attr
    def requester(cls):
        return relationship(
            "User",
            back_populates=cls.backref_name(),
            doc="SurveyEfficiencyAnalysis's requester.",
            uselist=False,
            foreign_keys=f"{cls.__name__}.requester_id",
        )

    @declared_attr
    def requester_id(cls):
        return sa.Column(
            sa.ForeignKey('users.id', ondelete='CASCADE'),
            nullable=False,
            index=True,
            doc="ID of the SurveyEfficiencyAnalysis requester's User instance.",
        )

    @declared_attr
    def groups(cls):
        return relationship(
            "Group",
            secondary="group_" + cls.backref_name(),
            cascade="save-update, merge, refresh-expire, expunge",
            passive_deletes=True,
            doc="Groups that can see the SurveyEfficiencyAnalysis.",
        )

    @classmethod
    def backref_name(cls):
        if cls.__name__ == 'SurveyEfficiencyForObservations':
            return 'survey_efficiency_for_observations'
        if cls.__name__ == 'SurveyEfficiencyForObservationPlan':
            return 'survey_efficiency_for_observation_plan'


class SurveyEfficiencyForObservations(Base, SurveyEfficiencyAnalysisMixin):
    """A request for an SurveyEfficiencyAnalysis from a set of observations."""

    __tablename__ = 'survey_efficiency_for_observations'

    create = AccessibleIfRelatedRowsAreAccessible(gcnevent='read')

    read = accessible_by_groups_members & AccessibleIfRelatedRowsAreAccessible(
        gcnevent='read'
    )

    gcnevent = relationship(
        'GcnEvent',
        back_populates='survey_efficiency_analyses',
        doc="The target GcnEvent.",
    )
    gcnevent_id = sa.Column(
        sa.ForeignKey('gcnevents.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
        doc="ID of the target GcnEvent.",
    )

    localization = relationship(
        'Localization',
        back_populates='survey_efficiency_analyses',
        doc="The target Localization.",
    )
    localization_id = sa.Column(
        sa.ForeignKey('localizations.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
        doc="ID of the target Localization.",
    )

    instrument_id = sa.Column(
        sa.ForeignKey('instruments.id', ondelete="CASCADE"),
        nullable=False,
        doc='Instrument ID',
    )

    instrument = relationship(
        "Instrument",
        foreign_keys=instrument_id,
        doc="The Instrument that this efficiency analysis belongs to",
    )


class SurveyEfficiencyForObservationPlan(Base, SurveyEfficiencyAnalysisMixin):
    """A request for an SurveyEfficiencyAnalysis from an observation plan."""

    __tablename__ = 'survey_efficiency_for_observation_plans'

    create = AccessibleIfRelatedRowsAreAccessible(observation_plan='read')

    read = accessible_by_groups_members & AccessibleIfRelatedRowsAreAccessible(
        observation_plan='read'
    )

    observation_plan_id = sa.Column(
        sa.ForeignKey('eventobservationplans.id', ondelete="CASCADE"),
        nullable=False,
        doc='Event observation plan ID',
    )

    observation_plan = relationship(
        "EventObservationPlan",
        foreign_keys=observation_plan_id,
        doc="The EventObservationPlan that this survey efficiency analysis belongs to",
    )
