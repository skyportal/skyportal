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
import * as recentGcnEventsActions from "./ducks/recentGcnEvents";

// we also import actions that won't be hydrated, to make sure they are
// registered as reducers, to avoid conflicts with redux-state-sync
/* eslint-disable no-unused-vars */
import * as sourceActions from "./ducks/source";
import * as sourcesActions from "./ducks/sources";
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

// add an argument 'dashboardOnly' to fetch only the data needed for the
export default function hydrate(dashboardOnly = false) {
  return (dispatch) => {
    if (!dashboardOnly) {
      // initial data
      dispatch(sysInfoActions.fetchSystemInfo());
      dispatch(dbInfoActions.fetchDBInfo());
      dispatch(configActions.fetchConfig());
      dispatch(profileActions.fetchUserProfile());
      dispatch(groupsActions.fetchGroups(true));
      dispatch(usersActions.fetchUsers());
    }
    // dashboard data
    dispatch(newsFeedActions.fetchNewsFeed());
    dispatch(topSourcesActions.fetchTopSources());
    dispatch(recentSourcesActions.fetchRecentSources());
    dispatch(sourceCountsActions.fetchSourceCounts());
    dispatch(recentGcnEventsActions.fetchRecentGcnEvents());

    if (!dashboardOnly) {
      // other data
      dispatch(streamsActions.fetchStreams());
      dispatch(enumTypesActions.fetchEnumTypes());
      dispatch(instrumentsActions.fetchInstruments());
      dispatch(allocationsActions.fetchAllocations());
      dispatch(telescopesActions.fetchTelescopes());
      dispatch(taxonomyActions.fetchTaxonomies());
      dispatch(instrumentsActions.fetchInstrumentForms());
      dispatch(favoritesActions.fetchFavorites());
      dispatch(tnsrobotsActions.fetchTNSRobots());
      dispatch(rejectedActions.fetchRejected());
      dispatch(observingRunsActions.fetchObservingRuns());
      dispatch(allocationsActions.fetchAllocationsApiClassname());
      dispatch(observationPlansActions.fetchObservationPlanNames());
      dispatch(analysisServicesActions.fetchAnalysisServices());
      dispatch(defaultFollowupRequestsActions.fetchDefaultFollowupRequests());
      dispatch(defaultObservationPlansActions.fetchDefaultObservationPlans());
      dispatch(
        defaultSurveyEfficienciesActions.fetchDefaultSurveyEfficiencies()
      );
      dispatch(earthquakeActions.fetchEarthquakes());
      dispatch(mmadetectorActions.fetchMMADetectors());
    }
  };
}
