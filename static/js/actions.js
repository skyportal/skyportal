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
import "./ducks/source";
import * as gcnTagsActions from "./ducks/gcnTags";
import "./ducks/gcnEvent";
import "./ducks/gcnEvents";
import * as weatherActions from "./ducks/weather";
import * as spatialCatalogsActions from "./ducks/spatialCatalogs";
import * as photometryMinimalActions from "./ducks/photometry_minimal";
import * as classificationsActions from "./ducks/classifications";
import * as sourcesInGcnActions from "./ducks/sourcesingcn";
import "./ducks/candidate/candidate";
import * as candidatesActions from "./ducks/candidate/candidates";
import * as observationsActions from "./ducks/observations";
import * as catalogQueriesActions from "./ducks/catalog_query";
import "./ducks/survey_efficiency_observations";
import "./ducks/survey_efficiency_observation_plans";
import * as localizationActions from "./ducks/localization";
import * as shiftsActions from "./ducks/shifts";
import * as remindersActions from "./ducks/reminders";
import "./ducks/group";
import * as instrumentActions from "./ducks/instrument";

// this is used to keep track of what has been hydrated yet or not
import * as hydrationActions from "./ducks/hydration";

export default function hydrate() {
  return (dispatch) => {
    // Dashboard data, refreshed on navigation. Everything else is fetched
    // on-demand by each page's RTK Query hooks (no eager boot prefetch).
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
  };
}
