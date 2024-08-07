__all__ = [
    'GroupTaxonomy',
    'GroupComment',
    'GroupAnnotation',
    'GroupClassification',
    'GroupMMADetectorSpectrum',
    'GroupMMADetectorTimeInterval',
    'GroupPhotometry',
    'GroupPhotometricSeries',
    'GroupSpectrum',
    'GroupCommentOnSpectrum',
    'GroupCommentOnGCN',
    'GroupCommentOnEarthquake',
    'GroupCommentOnShift',
    'GroupReminder',
    'GroupReminderOnSpectrum',
    'GroupReminderOnGCN',
    'GroupReminderOnEarthquake',
    'GroupReminderOnShift',
    'GroupAnnotationOnPhotometry',
    'GroupAnnotationOnSpectrum',
    'GroupInvitation',
    'GroupSourceNotification',
    'GroupStream',
    'GroupAnalysisService',
    'GroupObjAnalysis',
    'GroupDefaultAnalysis',
    'GroupPublicRelease',
]

import sqlalchemy as sa

from baselayer.app.models import join_model, User, AccessibleIfUserMatches

from baselayer.app.models import DBSession, restricted, CustomUserAccessControl
from .photometry import Photometry
from .photometric_series import PhotometricSeries
from .taxonomy import Taxonomy
from .comment import (
    Comment,
    CommentOnSpectrum,
    CommentOnGCN,
    CommentOnShift,
    CommentOnEarthquake,
)
from .annotation import Annotation
from .classification import Classification
from .mmadetector import MMADetectorSpectrum, MMADetectorTimeInterval
from .spectrum import Spectrum
from .annotation import AnnotationOnSpectrum, AnnotationOnPhotometry
from .reminder import (
    Reminder,
    ReminderOnGCN,
    ReminderOnSpectrum,
    ReminderOnShift,
    ReminderOnEarthquake,
)
from .invitation import Invitation
from .source_notification import SourceNotification
from .filter import Filter
from .stream import Stream, StreamUser
from .survey_efficiency import (
    SurveyEfficiencyForObservations,
    SurveyEfficiencyForObservationPlan,
)
from .group import Group, accessible_by_group_admins, accessible_by_group_members
from .analysis import AnalysisService, ObjAnalysis, DefaultAnalysis
from .public_pages.public_release import PublicRelease

GroupObjAnalysis = join_model("group_obj_analyses", Group, ObjAnalysis)
GroupObjAnalysis.__doc__ = "Join table mapping Groups to ObjAnalysis."
GroupObjAnalysis.delete = GroupObjAnalysis.update = (
    accessible_by_group_admins & GroupObjAnalysis.read
)

GroupAnalysisService = join_model("group_analysisservices", Group, AnalysisService)
GroupAnalysisService.__doc__ = "Join table mapping Groups to Analysis Services."
GroupAnalysisService.delete = GroupAnalysisService.update = (
    accessible_by_group_admins & GroupAnalysisService.read
)

GroupDefaultAnalysis = join_model("group_default_analyses", Group, DefaultAnalysis)
GroupDefaultAnalysis.__doc__ = "Join table mapping Groups to Default Analyses."
GroupDefaultAnalysis.delete = GroupDefaultAnalysis.update = (
    accessible_by_group_admins & GroupDefaultAnalysis.read
)

GroupTaxonomy = join_model("group_taxonomy", Group, Taxonomy)
GroupTaxonomy.__doc__ = "Join table mapping Groups to Taxonomies."
GroupTaxonomy.delete = GroupTaxonomy.update = (
    accessible_by_group_admins & GroupTaxonomy.read
)

GroupComment = join_model("group_comments", Group, Comment)
GroupComment.__doc__ = "Join table mapping Groups to Comments."
GroupComment.delete = GroupComment.update = (
    accessible_by_group_admins & GroupComment.read
)

GroupReminder = join_model("group_reminders", Group, Reminder)
GroupReminder.__doc__ = "Join table mapping Groups to Reminders."
GroupReminder.delete = GroupReminder.update = (
    accessible_by_group_admins & GroupReminder.read
)
GroupSurveyEfficiencyForObservationPlan = join_model(
    "group_survey_efficiency_for_observation_plan",
    Group,
    SurveyEfficiencyForObservationPlan,
)
GroupSurveyEfficiencyForObservationPlan.__doc__ = (
    "Join table mapping Groups to SurveyEfficiencyForObservationPlans."
)
GroupSurveyEfficiencyForObservationPlan.delete = (
    GroupSurveyEfficiencyForObservationPlan.update
) = (accessible_by_group_admins & GroupSurveyEfficiencyForObservationPlan.read)

GroupSurveyEfficiencyForObservations = join_model(
    "group_survey_efficiency_for_observations", Group, SurveyEfficiencyForObservations
)
GroupSurveyEfficiencyForObservations.__doc__ = (
    "Join table mapping Groups to SurveyEfficiencyForObservations."
)
GroupSurveyEfficiencyForObservations.delete = (
    GroupSurveyEfficiencyForObservations.update
) = (accessible_by_group_admins & GroupSurveyEfficiencyForObservations.read)

GroupAnnotation = join_model("group_annotations", Group, Annotation)
GroupAnnotation.__doc__ = "Join table mapping Groups to Annotation."
GroupAnnotation.delete = GroupAnnotation.update = (
    accessible_by_group_admins & GroupAnnotation.read
)

GroupClassification = join_model("group_classifications", Group, Classification)
GroupClassification.__doc__ = "Join table mapping Groups to Classifications."
GroupClassification.delete = GroupClassification.update = (
    accessible_by_group_admins & GroupClassification.read
)

GroupPhotometry = join_model("group_photometry", Group, Photometry)
GroupPhotometry.__doc__ = "Join table mapping Groups to Photometry."
GroupPhotometry.delete = GroupPhotometry.update = (
    accessible_by_group_admins & GroupPhotometry.read
)

GroupPhotometricSeries = join_model(
    "group_photometric_series", Group, PhotometricSeries
)
GroupPhotometricSeries.__doc__ = "Join table mapping Groups to PhotometricSeries."
GroupPhotometricSeries.delete = GroupPhotometricSeries.update = (
    accessible_by_group_admins & GroupPhotometricSeries.read
)

GroupMMADetectorSpectrum = join_model(
    "group_mmadetector_spectra",
    Group,
    MMADetectorSpectrum,
    overlaps='mmadetector_spectra',
)
GroupMMADetectorSpectrum.__doc__ = 'Join table mapping Groups to MMADetectorSpectra.'
GroupMMADetectorSpectrum.update = GroupMMADetectorSpectrum.delete = (
    accessible_by_group_admins & GroupMMADetectorSpectrum.read
)

GroupMMADetectorTimeInterval = join_model(
    "group_mmadetector_time_intervals",
    Group,
    MMADetectorTimeInterval,
    overlaps='mmadetector_time_intervals',
)
GroupMMADetectorTimeInterval.__doc__ = (
    'Join table mapping Groups to MMADetectorTimeInterval.'
)
GroupMMADetectorTimeInterval.update = GroupMMADetectorTimeInterval.delete = (
    accessible_by_group_admins & GroupMMADetectorTimeInterval.read
)

GroupSpectrum = join_model("group_spectra", Group, Spectrum)
GroupSpectrum.__doc__ = 'Join table mapping Groups to Spectra.'
GroupSpectrum.update = GroupSpectrum.delete = (
    accessible_by_group_admins & GroupSpectrum.read
)

GroupCommentOnSpectrum = join_model(
    "group_comments_on_spectra", Group, CommentOnSpectrum
)
GroupCommentOnSpectrum.__doc__ = "Join table mapping Groups to CommentOnSpectrum."
GroupCommentOnSpectrum.delete = GroupCommentOnSpectrum.update = (
    accessible_by_group_admins & GroupCommentOnSpectrum.read
)

GroupReminderOnSpectrum = join_model(
    "group_reminders_on_spectra", Group, ReminderOnSpectrum
)
GroupReminderOnSpectrum.__doc__ = "Join table mapping Groups to ReminderOnSpectrum."
GroupReminderOnSpectrum.delete = GroupReminderOnSpectrum.update = (
    accessible_by_group_admins & GroupReminderOnSpectrum.read
)

GroupAnnotationOnSpectrum = join_model(
    "group_annotations_on_spectra", Group, AnnotationOnSpectrum
)
GroupAnnotationOnSpectrum.__doc__ = "Join table mapping Groups to AnnotationOnSpectrum."
GroupAnnotationOnSpectrum.delete = GroupAnnotationOnSpectrum.update = (
    accessible_by_group_admins & GroupAnnotationOnSpectrum.read
)

GroupAnnotationOnPhotometry = join_model(
    "group_annotations_on_photometry", Group, AnnotationOnPhotometry
)
GroupAnnotationOnPhotometry.__doc__ = (
    "Join table mapping Groups to AnnotationOnPhotometry."
)
GroupAnnotationOnPhotometry.delete = GroupAnnotationOnPhotometry.update = (
    accessible_by_group_admins & GroupAnnotationOnPhotometry.read
)

GroupCommentOnGCN = join_model("group_comments_on_gcns", Group, CommentOnGCN)
GroupCommentOnGCN.__doc__ = "Join table mapping Groups to CommentOnGCN."
GroupCommentOnGCN.delete = GroupCommentOnGCN.update = (
    accessible_by_group_admins & GroupCommentOnGCN.read
)

GroupReminderOnGCN = join_model("group_reminders_on_gcns", Group, ReminderOnGCN)
GroupReminderOnGCN.__doc__ = "Join table mapping Groups to ReminderOnGCN."
GroupReminderOnGCN.delete = GroupReminderOnGCN.update = (
    accessible_by_group_admins & GroupReminderOnGCN.read
)

GroupCommentOnShift = join_model("group_comments_on_shifts", Group, CommentOnShift)
GroupCommentOnShift.__doc__ = "Join table mapping Groups to CommentOnShift."
GroupCommentOnShift.delete = GroupCommentOnShift.update = (
    accessible_by_group_admins & GroupCommentOnShift.read
)

GroupReminderOnShift = join_model("group_reminders_on_shifts", Group, ReminderOnShift)
GroupReminderOnShift.__doc__ = "Join table mapping Groups to ReminderOnShift."
GroupReminderOnShift.delete = GroupReminderOnShift.update = (
    accessible_by_group_admins & GroupReminderOnShift.read
)

GroupCommentOnEarthquake = join_model(
    "group_comments_on_earthquakes", Group, CommentOnEarthquake
)
GroupCommentOnEarthquake.__doc__ = "Join table mapping Groups to CommentOnEarthquake."
GroupCommentOnEarthquake.delete = GroupCommentOnEarthquake.update = (
    accessible_by_group_admins & GroupCommentOnEarthquake.read
)

GroupReminderOnEarthquake = join_model(
    "group_reminders_on_earthquakes", Group, ReminderOnEarthquake
)
GroupReminderOnEarthquake.__doc__ = "Join table mapping Groups to ReminderOnEarthquake."
GroupReminderOnEarthquake.delete = GroupReminderOnEarthquake.update = (
    accessible_by_group_admins & GroupReminderOnEarthquake.read
)

GroupInvitation = join_model('group_invitations', Group, Invitation)

GroupSourceNotification = join_model('group_notifications', Group, SourceNotification)
GroupSourceNotification.create = (
    GroupSourceNotification.read
) = accessible_by_group_members
GroupSourceNotification.update = (
    GroupSourceNotification.delete
) = accessible_by_group_admins | AccessibleIfUserMatches('sourcenotification.sent_by')

GroupStream = join_model('group_streams', Group, Stream)
GroupStream.__doc__ = "Join table mapping Groups to Streams."
GroupStream.update = restricted
GroupStream.delete = (
    # only admins can delete streams from groups
    accessible_by_group_admins
    & GroupStream.read
) & CustomUserAccessControl(
    # Can only delete a stream from the group if none of the group's filters
    # are operating on the stream.
    lambda cls, user_or_token: DBSession()
    .query(cls)
    .outerjoin(Stream)
    .outerjoin(
        Filter,
        sa.and_(Filter.stream_id == Stream.id, Filter.group_id == cls.group_id),
    )
    .group_by(cls.id)
    .having(
        sa.or_(
            sa.func.bool_and(Filter.id.is_(None)),
            sa.func.bool_and(Stream.id.is_(None)),  # group has no streams
        )
    )
)
GroupStream.create = (
    # only admins can add streams to groups
    accessible_by_group_admins
    & GroupStream.read
    & CustomUserAccessControl(
        # Can only add a stream to a group if all users in the group have
        # access to the stream.
        # Also, cannot add stream access to single user groups.
        lambda cls, user_or_token: DBSession()
        .query(cls)
        .join(Group, cls.group)
        .outerjoin(User, Group.users)
        .outerjoin(
            StreamUser,
            sa.and_(
                cls.stream_id == StreamUser.stream_id,
                User.id == StreamUser.user_id,
            ),
        )
        .filter(Group.single_user_group.is_(False))
        .group_by(cls.id)
        .having(
            sa.or_(
                sa.func.bool_and(StreamUser.stream_id.isnot(None)),
                sa.func.bool_and(User.id.is_(None)),
            )
        )
    )
)

GroupPublicRelease = join_model('group_public_releases', Group, PublicRelease)
GroupPublicRelease.__doc__ = "Join table mapping Groups to Public Releases."
GroupPublicRelease.update = GroupPublicRelease.delete = (
    accessible_by_group_admins & GroupPublicRelease.read
)
