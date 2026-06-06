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
import * as topSaversActions from "./ducks/topSavers";
import * as recentSourcesActions from "./ducks/recentSources";
import * as mmadetectorActions from "./ducks/mmadetector";
import * as instrumentsActions from "./ducks/instruments";
import * as sourceCountsActions from "./ducks/sourceCounts";
import * as observingRunsActions from "./ducks/observingRuns";
import * as telescopesActions from "./ducks/telescopes";
import * as taxonomyActions from "./ducks/taxonomies";
import * as favoritesActions from "./ducks/favorites";
import * as rejectedActions from "./ducks/rejected_candidates";
import * as sharingServicesActions from "./ducks/sharingServices";
import * as enumTypesActions from "./ducks/enum_types";
import * as usersActions from "./ducks/users";
import * as streamsActions from "./ducks/streams";
import * as analysisServicesActions from "./ducks/analysis_services";
import * as recentGcnEventsActions from "./ducks/recentGcnEvents";
import * as followupApisActions from "./ducks/followupApis";
import * as galaxiesActions from "./ducks/galaxies";
import * as objTagActions from "./ducks/objectTags";

// we also import actions that won't be hydrated, to make sure they are
// registered as reducers, to avoid conflicts with redux-state-sync
import * as sourceActions from "./ducks/source";
import * as sourcesActions from "./ducks/sources";
import * as gcnTagsActions from "./ducks/gcnTags";
import * as gcnEventActions from "./ducks/gcnEvent";
import * as gcnEventsActions from "./ducks/gcnEvents";
import * as weatherActions from "./ducks/weather";
import * as spatialCatalogsActions from "./ducks/spatialCatalogs";
import * as photometryActions from "./ducks/photometry";
import * as photometryMinimalActions from "./ducks/photometry_minimal";
import * as classificationsActions from "./ducks/classifications";
import * as sourcesInGcnActions from "./ducks/sourcesingcn";
import * as candidateActions from "./ducks/candidate/candidate";
import * as candidatesActions from "./ducks/candidate/candidates";
import * as observationsActions from "./ducks/observations";
import * as catalogQueriesActions from "./ducks/catalog_query";
import "./ducks/survey_efficiency_observations";
import * as surveyEfficiencyObservationPlansActions from "./ducks/survey_efficiency_observation_plans";
import * as localizationActions from "./ducks/localization";
import * as shiftsActions from "./ducks/shifts";
import * as remindersActions from "./ducks/reminders";
import "./ducks/group";
import * as instrumentActions from "./ducks/instrument";

// this is used to keep track of what has been hydrated yet or not
import * as hydrationActions from "./ducks/hydration";

export default function hydrate(
  dashboardOnly = false,
  ducks_to_hydrate = hydrationActions.DUCKS_TO_HYDRATE,
) {
  return (dispatch) => {
    if (!dashboardOnly) {
      // initial data
      if (ducks_to_hydrate.includes("sysInfo")) {
        // RTK Query: `initiate()` is a dispatchable thunk that resolves when the
        // request settles, so the hydration-count gating is preserved.
        dispatch(
          sysInfoActions.sysInfoApi.endpoints.getSysInfo.initiate(),
        ).then(() => {
          dispatch(hydrationActions.finishedHydrating("sysInfo"));
        });
      }
      if (ducks_to_hydrate.includes("dbInfo")) {
        dispatch(dbInfoActions.dbInfoApi.endpoints.getDbInfo.initiate()).then(
          () => {
            dispatch(hydrationActions.finishedHydrating("dbInfo"));
          },
        );
      }
      if (ducks_to_hydrate.includes("config")) {
        dispatch(configActions.configApi.endpoints.getConfig.initiate()).then(
          () => {
            dispatch(hydrationActions.finishedHydrating("config"));
          },
        );
      }
      if (ducks_to_hydrate.includes("profile")) {
        dispatch(
          profileActions.profileApi.endpoints.getProfile.initiate(),
        ).then(() => {
          dispatch(hydrationActions.finishedHydrating("profile"));
        });
      }
      if (ducks_to_hydrate.includes("groups")) {
        dispatch(groupsActions.groupsApi.endpoints.getGroups.initiate()).then(
          () => {
            dispatch(hydrationActions.finishedHydrating("groups"));
          },
        );
      }
      if (ducks_to_hydrate.includes("users")) {
        dispatch(usersActions.usersApi.endpoints.getUsers.initiate()).then(
          () => {
            dispatch(hydrationActions.finishedHydrating("users"));
          },
        );
      }
    }
    // dashboard data, always refreshed
    dispatch(newsFeedActions.newsFeedApi.endpoints.getNewsFeed.initiate());
    dispatch(
      topSourcesActions.topSourcesApi.endpoints.getTopSources.initiate(),
    );
    dispatch(topSaversActions.topSaversApi.endpoints.getTopSavers.initiate());
    dispatch(
      recentSourcesActions.recentSourcesApi.endpoints.getRecentSources.initiate(),
    );
    dispatch(
      sourceCountsActions.sourceCountsApi.endpoints.getSourceCounts.initiate(),
    );
    dispatch(
      recentGcnEventsActions.recentGcnEventsApi.endpoints.getRecentGcnEvents.initiate(),
    );
    if (!dashboardOnly) {
      // other data
      if (ducks_to_hydrate.includes("streams")) {
        dispatch(
          streamsActions.streamsApi.endpoints.getStreams.initiate(),
        ).then(() => {
          dispatch(hydrationActions.finishedHydrating("streams"));
        });
      }
      if (ducks_to_hydrate.includes("enumTypes")) {
        dispatch(
          enumTypesActions.enumTypesApi.endpoints.getEnumTypes.initiate(),
        ).then(() => {
          dispatch(hydrationActions.finishedHydrating("enumTypes"));
        });
      }
      if (ducks_to_hydrate.includes("instruments")) {
        dispatch(
          instrumentsActions.instrumentsApi.endpoints.getInstruments.initiate(),
        ).then(() => {
          dispatch(hydrationActions.finishedHydrating("instruments"));
        });
      }
      if (ducks_to_hydrate.includes("allocations")) {
        dispatch(
          allocationsActions.allocationsApi.endpoints.getAllocations.initiate(),
        ).then(() => {
          dispatch(hydrationActions.finishedHydrating("allocations"));
        });
      }
      if (ducks_to_hydrate.includes("telescopes")) {
        dispatch(
          telescopesActions.telescopesApi.endpoints.getTelescopes.initiate(),
        ).then(() => {
          dispatch(hydrationActions.finishedHydrating("telescopes"));
        });
      }
      if (ducks_to_hydrate.includes("taxonomy")) {
        dispatch(
          taxonomyActions.taxonomiesApi.endpoints.getTaxonomies.initiate(),
        ).then(() => {
          dispatch(hydrationActions.finishedHydrating("taxonomy"));
        });
      }
      if (ducks_to_hydrate.includes("instrumentForms")) {
        dispatch(
          instrumentsActions.instrumentsApi.endpoints.getInstrumentForms.initiate(),
        ).then(() => {
          dispatch(hydrationActions.finishedHydrating("instrumentForms"));
        });
      }
      if (ducks_to_hydrate.includes("favorites")) {
        dispatch(
          favoritesActions.favoritesApi.endpoints.getFavorites.initiate(),
        ).then(() => {
          dispatch(hydrationActions.finishedHydrating("favorites"));
        });
      }
      if (ducks_to_hydrate.includes("sharingServices")) {
        dispatch(
          sharingServicesActions.sharingServicesApi.endpoints.getSharingServices.initiate(),
        ).then(() => {
          dispatch(hydrationActions.finishedHydrating("sharingServices"));
        });
      }
      if (ducks_to_hydrate.includes("galaxyCatalogs")) {
        dispatch(
          galaxiesActions.galaxiesApi.endpoints.getGalaxyCatalogs.initiate(),
        ).then(() => {
          dispatch(hydrationActions.finishedHydrating("galaxyCatalogs"));
        });
      }
      if (ducks_to_hydrate.includes("rejected")) {
        dispatch(
          rejectedActions.rejectedCandidatesApi.endpoints.getRejectedCandidates.initiate(),
        ).then(() => {
          dispatch(hydrationActions.finishedHydrating("rejected"));
        });
      }
      if (ducks_to_hydrate.includes("observingRuns")) {
        dispatch(
          observingRunsActions.observingRunsApi.endpoints.getObservingRuns.initiate(),
        ).then(() => {
          dispatch(hydrationActions.finishedHydrating("observingRuns"));
        });
      }
      if (ducks_to_hydrate.includes("allocationsApiClassname")) {
        dispatch(
          allocationsActions.allocationsApi.endpoints.getAllocationsApiClassname.initiate(),
        ).then(() => {
          dispatch(
            hydrationActions.finishedHydrating("allocationsApiClassname"),
          );
        });
      }
      if (ducks_to_hydrate.includes("analysisServices")) {
        dispatch(
          analysisServicesActions.analysisServicesApi.endpoints.getAnalysisServices.initiate(),
        ).then(() => {
          dispatch(hydrationActions.finishedHydrating("analysisServices"));
        });
      }
      if (ducks_to_hydrate.includes("defaultFollowupRequests")) {
        dispatch(
          defaultFollowupRequestsActions.defaultFollowupRequestsApi.endpoints.getDefaultFollowupRequests.initiate(),
        ).then(() => {
          dispatch(
            hydrationActions.finishedHydrating("defaultFollowupRequests"),
          );
        });
      }
      if (ducks_to_hydrate.includes("defaultObservationPlans")) {
        dispatch(
          defaultObservationPlansActions.defaultObservationPlansApi.endpoints.getDefaultObservationPlans.initiate(),
        ).then(() => {
          dispatch(
            hydrationActions.finishedHydrating("defaultObservationPlans"),
          );
        });
      }
      if (ducks_to_hydrate.includes("defaultSurveyEfficiencies")) {
        dispatch(
          defaultSurveyEfficienciesActions.defaultSurveyEfficienciesApi.endpoints.getDefaultSurveyEfficiencies.initiate(),
        ).then(() => {
          dispatch(
            hydrationActions.finishedHydrating("defaultSurveyEfficiencies"),
          );
        });
      }
      if (ducks_to_hydrate.includes("earthquake")) {
        dispatch(
          earthquakeActions.earthquakeApi.endpoints.getEarthquakes.initiate(),
        ).then(() => {
          dispatch(hydrationActions.finishedHydrating("earthquake"));
        });
      }
      if (ducks_to_hydrate.includes("mmadetector")) {
        dispatch(
          mmadetectorActions.mmadetectorApi.endpoints.getMMADetectors.initiate(),
        ).then(() => {
          dispatch(hydrationActions.finishedHydrating("mmadetector"));
        });
      }
      if (ducks_to_hydrate.includes("followupApis")) {
        dispatch(
          followupApisActions.followupApisApi.endpoints.getFollowupApis.initiate(),
        ).then(() => {
          dispatch(hydrationActions.finishedHydrating("followupApis"));
        });
      }
      if (ducks_to_hydrate.includes("objectTags")) {
        dispatch(
          objTagActions.objectTagsApi.endpoints.getTagOptions.initiate(),
        ).then(() => {
          dispatch(hydrationActions.finishedHydrating("objectTags"));
        });
      }
    }
  };
}
