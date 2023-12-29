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
import * as topScannersActions from "./ducks/topScanners";
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

// this is used to keep track of what has been hydrated yet or not
import * as hydrationActions from "./ducks/hydration";

export default function hydrate(
  dashboardOnly = false,
  ducks_to_hydrate = hydrationActions.DUCKS_TO_HYDRATE
) {
  return (dispatch) => {
    if (!dashboardOnly) {
      // initial data
      if (ducks_to_hydrate.includes("sysInfo")) {
        dispatch(sysInfoActions.fetchSystemInfo()).then(() => {
          dispatch(hydrationActions.finishedHydrating("sysInfo"));
        });
      }
      if (ducks_to_hydrate.includes("dbInfo")) {
        dispatch(dbInfoActions.fetchDBInfo()).then(() => {
          dispatch(hydrationActions.finishedHydrating("dbInfo"));
        });
      }
      if (ducks_to_hydrate.includes("config")) {
        dispatch(configActions.fetchConfig()).then(() => {
          dispatch(hydrationActions.finishedHydrating("config"));
        });
      }
      if (ducks_to_hydrate.includes("profile")) {
        dispatch(profileActions.fetchUserProfile()).then(() => {
          dispatch(hydrationActions.finishedHydrating("profile"));
        });
      }
      if (ducks_to_hydrate.includes("groups")) {
        dispatch(groupsActions.fetchGroups(true)).then(() => {
          dispatch(hydrationActions.finishedHydrating("groups"));
        });
      }
      if (ducks_to_hydrate.includes("users")) {
        dispatch(usersActions.fetchUsers()).then(() => {
          dispatch(hydrationActions.finishedHydrating("users"));
        });
      }
    }
    // dashboard data, always refreshed
    dispatch(newsFeedActions.fetchNewsFeed());
    dispatch(topSourcesActions.fetchTopSources());
    dispatch(topScannersActions.fetchTopScanners());
    dispatch(recentSourcesActions.fetchRecentSources());
    dispatch(sourceCountsActions.fetchSourceCounts());
    dispatch(recentGcnEventsActions.fetchRecentGcnEvents());
    if (!dashboardOnly) {
      // other data
      if (ducks_to_hydrate.includes("streams")) {
        dispatch(streamsActions.fetchStreams()).then(() => {
          dispatch(hydrationActions.finishedHydrating("streams"));
        });
      }
      if (ducks_to_hydrate.includes("enumTypes")) {
        dispatch(enumTypesActions.fetchEnumTypes()).then(() => {
          dispatch(hydrationActions.finishedHydrating("enumTypes"));
        });
      }
      if (ducks_to_hydrate.includes("instruments")) {
        dispatch(instrumentsActions.fetchInstruments()).then(() => {
          dispatch(hydrationActions.finishedHydrating("instruments"));
        });
      }
      if (ducks_to_hydrate.includes("allocations")) {
        dispatch(allocationsActions.fetchAllocations()).then(() => {
          dispatch(hydrationActions.finishedHydrating("allocations"));
        });
      }
      if (ducks_to_hydrate.includes("telescopes")) {
        dispatch(telescopesActions.fetchTelescopes()).then(() => {
          dispatch(hydrationActions.finishedHydrating("telescopes"));
        });
      }
      if (ducks_to_hydrate.includes("taxonomy")) {
        dispatch(taxonomyActions.fetchTaxonomies()).then(() => {
          dispatch(hydrationActions.finishedHydrating("taxonomy"));
        });
      }
      if (ducks_to_hydrate.includes("instrumentForms")) {
        dispatch(instrumentsActions.fetchInstrumentForms()).then(() => {
          dispatch(hydrationActions.finishedHydrating("instrumentForms"));
        });
      }
      if (ducks_to_hydrate.includes("favorites")) {
        dispatch(favoritesActions.fetchFavorites()).then(() => {
          dispatch(hydrationActions.finishedHydrating("favorites"));
        });
      }
      if (ducks_to_hydrate.includes("tnsrobots")) {
        dispatch(tnsrobotsActions.fetchTNSRobots()).then(() => {
          dispatch(hydrationActions.finishedHydrating("tnsrobots"));
        });
      }
      if (ducks_to_hydrate.includes("rejected")) {
        dispatch(rejectedActions.fetchRejected()).then(() => {
          dispatch(hydrationActions.finishedHydrating("rejected"));
        });
      }
      if (ducks_to_hydrate.includes("observingRuns")) {
        dispatch(observingRunsActions.fetchObservingRuns()).then(() => {
          dispatch(hydrationActions.finishedHydrating("observingRuns"));
        });
      }
      if (ducks_to_hydrate.includes("allocationsApiClassname")) {
        dispatch(allocationsActions.fetchAllocationsApiClassname()).then(() => {
          dispatch(
            hydrationActions.finishedHydrating("allocationsApiClassname")
          );
        });
      }
      if (ducks_to_hydrate.includes("observationPlans")) {
        dispatch(observationPlansActions.fetchObservationPlanNames()).then(
          () => {
            dispatch(hydrationActions.finishedHydrating("observationPlans"));
          }
        );
      }
      if (ducks_to_hydrate.includes("analysisServices")) {
        dispatch(analysisServicesActions.fetchAnalysisServices()).then(() => {
          dispatch(hydrationActions.finishedHydrating("analysisServices"));
        });
      }
      if (ducks_to_hydrate.includes("defaultFollowupRequests")) {
        dispatch(
          defaultFollowupRequestsActions.fetchDefaultFollowupRequests()
        ).then(() => {
          dispatch(
            hydrationActions.finishedHydrating("defaultFollowupRequests")
          );
        });
      }
      if (ducks_to_hydrate.includes("defaultObservationPlans")) {
        dispatch(
          defaultObservationPlansActions.fetchDefaultObservationPlans()
        ).then(() => {
          dispatch(
            hydrationActions.finishedHydrating("defaultObservationPlans")
          );
        });
      }
      if (ducks_to_hydrate.includes("defaultSurveyEfficiencies")) {
        dispatch(
          defaultSurveyEfficienciesActions.fetchDefaultSurveyEfficiencies()
        ).then(() => {
          dispatch(
            hydrationActions.finishedHydrating("defaultSurveyEfficiencies")
          );
        });
      }
      if (ducks_to_hydrate.includes("earthquake")) {
        dispatch(earthquakeActions.fetchEarthquakes()).then(() => {
          dispatch(hydrationActions.finishedHydrating("earthquake"));
        });
      }
      if (ducks_to_hydrate.includes("mmadetector")) {
        dispatch(mmadetectorActions.fetchMMADetectors()).then(() => {
          dispatch(hydrationActions.finishedHydrating("mmadetector"));
        });
      }
    }
  };
}
