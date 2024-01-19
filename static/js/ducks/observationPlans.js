import messageHandler from "baselayer/MessageHandler";

import * as API from "../API";
import store from "../store";

const FETCH_OBSERVATION_PLAN_NAMES = "skyportal/FETCH_OBSERVATION_PLAN_NAMES";
const FETCH_OBSERVATION_PLAN_NAMES_OK =
  "skyportal/FETCH_OBSERVATION_PLAN_NAMES_OK";

// eslint-disable-next-line import/prefer-default-export
export const fetchObservationPlanNames = (filterParams = {}) =>
  API.GET(
    "/api/observation_plan/plan_names",
    FETCH_OBSERVATION_PLAN_NAMES,
    filterParams,
  );

// Websocket message handler
messageHandler.add((actionType, payload, dispatch) => {
  if (actionType === FETCH_OBSERVATION_PLAN_NAMES) {
    dispatch(fetchObservationPlanNames());
  }
});

const reducer = (state = null, action) => {
  switch (action.type) {
    case FETCH_OBSERVATION_PLAN_NAMES_OK: {
      return action.data;
    }
    default:
      return state;
  }
};

store.injectReducer("observationPlans", reducer);
