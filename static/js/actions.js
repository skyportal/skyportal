import * as allocationsActions from "./ducks/allocations";
import * as groupsActions from "./ducks/groups";
import * as profileActions from "./ducks/profile";
import * as sysInfoActions from "./ducks/sysInfo";
import * as dbInfoActions from "./ducks/dbInfo";
import * as earthquakeActions from "./ducks/earthquake";
import * as configActions from "./ducks/config";
import * as defaultFollowupRequestsActions from "./ducks/default_followup_requests";
import * as defaultObservationPlansActions from "./ducks/default_observation_plans";
import * as defaultSurveyEfficienciesActions from "./ducks/default_survey_efficiencies";
import * as newsFeedActions from "./ducks/newsFeed";
import * as topSourcesActions from "./ducks/topSources";
import * as recentSourcesActions from "./ducks/recentSources";
import * as mmadetectorActions from "./ducks/mmadetector";
import * as observationPlansActions from "./ducks/observationPlans";
import * as instrumentsActions from "./ducks/instruments";
import * as sourceCountsActions from "./ducks/sourceCounts";
import * as observingRunsActions from "./ducks/observingRuns";
import * as telescopesActions from "./ducks/telescopes";
import * as taxonomyActions from "./ducks/taxonomies";
import * as favoritesActions from "./ducks/favorites";
import * as rejectedActions from "./ducks/rejected_candidates";
import * as tnsrobotsActions from "./ducks/tnsrobots";
import * as enumTypesActions from "./ducks/enum_types";
import * as usersActions from "./ducks/users";
import * as streamsActions from "./ducks/streams";
import * as analysisServicesActions from "./ducks/analysis_services";

// we also import actions that won't be hydrated, to make sure they are
// registered as reducers, to avoid conflicts with redux-state-sync
/* eslint-disable no-unused-vars */
import * as sourceActions from "./ducks/source";
import * as sourcesActions from "./ducks/sources";
import * as recentGcnEventsActions from "./ducks/recentGcnEvents";
import * as gcnTagsActions from "./ducks/gcnTags";
import * as gcnEventActions from "./ducks/gcnEvent";
import * as gcnEventsActions from "./ducks/gcnEvents";
import * as weatherActions from "./ducks/weather";
import * as spatialCatalogsActions from "./ducks/spatialCatalogs";
import * as photometryActions from "./ducks/photometry";
import * as classificationsActions from "./ducks/classifications";
import * as sourcesInGcnActions from "./ducks/sourcesingcn";
import * as candidateActions from "./ducks/candidate";
import * as candidatesActions from "./ducks/candidates";
import * as galaxiesActions from "./ducks/galaxies";
import * as observationsActions from "./ducks/observations";
import * as catalogQueriesActions from "./ducks/catalog_query";
import * as surveyEfficiencyObservationsActions from "./ducks/survey_efficiency_observations";
import * as surveyEfficiencyObservationPlansActions from "./ducks/survey_efficiency_observation_plans";
import * as localizationActions from "./ducks/localization";
import * as shiftActions from "./ducks/shift";
import * as shiftsActions from "./ducks/shifts";
import * as remindersActions from "./ducks/reminders";
import * as groupActions from "./ducks/group";
import * as instrumentActions from "./ducks/instrument";
/* eslint-enable no-unused-vars */

export default function hydrate() {
  return (dispatch) => {
    dispatch(sysInfoActions.fetchSystemInfo());
    dispatch(dbInfoActions.fetchDBInfo());
    dispatch(configActions.fetchConfig());
    dispatch(earthquakeActions.fetchEarthquakes());
    dispatch(profileActions.fetchUserProfile());
    dispatch(groupsActions.fetchGroups(true));
    dispatch(mmadetectorActions.fetchMMADetectors());
    dispatch(newsFeedActions.fetchNewsFeed());
    dispatch(topSourcesActions.fetchTopSources());
    dispatch(instrumentsActions.fetchInstruments());
    dispatch(allocationsActions.fetchAllocations());
    dispatch(instrumentsActions.fetchInstrumentForms());
    dispatch(recentSourcesActions.fetchRecentSources());
    dispatch(sourceCountsActions.fetchSourceCounts());
    dispatch(observingRunsActions.fetchObservingRuns());
    dispatch(telescopesActions.fetchTelescopes());
    dispatch(taxonomyActions.fetchTaxonomies());
    dispatch(favoritesActions.fetchFavorites());
    dispatch(rejectedActions.fetchRejected());
    dispatch(tnsrobotsActions.fetchTNSRobots());
    dispatch(enumTypesActions.fetchEnumTypes());
    dispatch(allocationsActions.fetchAllocationsApiClassname());
    dispatch(observationPlansActions.fetchObservationPlanNames());
    dispatch(defaultFollowupRequestsActions.fetchDefaultFollowupRequests());
    dispatch(defaultObservationPlansActions.fetchDefaultObservationPlans());
    dispatch(defaultSurveyEfficienciesActions.fetchDefaultSurveyEfficiencies());
    dispatch(usersActions.fetchUsers());
    dispatch(streamsActions.fetchStreams());
    dispatch(analysisServicesActions.fetchAnalysisServices());
  };
}
