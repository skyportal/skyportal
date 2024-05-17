import store from "../store";

const FINISHED_HYDRATING = "skyportal/FINISHED_HYDRATING";
const VERIFY_HYDRATION = "skyportal/VERIFY_HYDRATION";

export const DUCKS_TO_HYDRATE = [
  "groups",
  "profile",
  "dbInfo",
  "sysInfo",
  "config",
  "users",
  "taxonomy",
  "enumTypes",
  "streams",
  "allocations",
  "tnsrobots",
  "instrumentForms",
  "observingRuns",
  "analysisServices",
  "instruments",
  "earthquake",
  "allocationsApiClassname",
  "defaultFollowupRequests",
  "defaultObservationPlans",
  "mmadetector",
  "defaultSurveyEfficiencies",
  "telescopes",
  "favorites",
  "rejected",
  "observationPlans",
  "galaxyCatalogs",
];

export const NUMBER_OF_DUCKS_TO_HYDRATE = DUCKS_TO_HYDRATE.length;

// eslint-disable-next-line import/prefer-default-export
export function finishedHydrating(ducks) {
  return {
    data: ducks,
    type: FINISHED_HYDRATING,
  };
}

export function verifyHydration() {
  return {
    type: VERIFY_HYDRATION,
  };
}

const reducer = (state = { hydratedList: [], hydrated: false }, action) => {
  switch (action.type) {
    case FINISHED_HYDRATING: {
      return {
        ...state,
        hydratedList: [...new Set([...state.hydratedList, action.data])],
        hydrated: state.hydratedList.length === NUMBER_OF_DUCKS_TO_HYDRATE,
      };
    }
    case VERIFY_HYDRATION: {
      return {
        ...state,
        hydrated: state?.hydratedList?.length === NUMBER_OF_DUCKS_TO_HYDRATE,
      };
    }
    default:
      return state;
  }
};

store.injectReducer("hydration", reducer);
